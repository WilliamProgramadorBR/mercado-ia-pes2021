# Mercado IA — autor: William (https://github.com/WilliamProgramadorBR)
"""Foto da memória do PES 2021 tirada DE FORA do jogo (Windows ReadProcessMemory), sem risco de derrubar o jogo.

Por quê: o overlay lia blocos FIXOS de memória (0x7FF4D7E00000...) com memory.read; em 09/10/2026 esse endereço
não existia na sessão e o jogo fechou ao apertar 9. Aqui só lemos regiões que o Windows diz estarem
comprometidas e legíveis (VirtualQueryEx), e procuramos a tabela de fichas de jogador (380 bytes) onde ela estiver.

Saída: um arquivo no mesmo formato que dados.load_players() entende (a região com as fichas, inteira) e,
no fim, um trecho com o marcador de data da carreira (07 6d 01 00 00) usado por aplicar.career_year().
"""
import ctypes
import ctypes.wintypes as wt
import re
import struct
import subprocess

PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010
MEM_COMMIT = 0x1000
MEM_PRIVATE = 0x20000
READABLE = {0x02, 0x04, 0x08, 0x20, 0x40, 0x80}   # READONLY, READWRITE, WRITECOPY, EXECUTE_READ(+WRITE/COPY)
GUARD_NOACCESS = 0x100 | 0x01
SIG = b'\xff\xff\xff\xff\x00\x00\x00\x00'
MARCA_DATA = b'\x07\x6d\x01\x00\x00'


class MBI(ctypes.Structure):
    _fields_ = [('BaseAddress', ctypes.c_void_p), ('AllocationBase', ctypes.c_void_p),
                ('AllocationProtect', wt.DWORD), ('PartitionId', wt.WORD), ('RegionSize', ctypes.c_size_t),
                ('State', wt.DWORD), ('Protect', wt.DWORD), ('Type', wt.DWORD)]


k32 = ctypes.WinDLL('kernel32', use_last_error=True)
k32.OpenProcess.restype = wt.HANDLE
k32.VirtualQueryEx.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.POINTER(MBI), ctypes.c_size_t]
k32.VirtualQueryEx.restype = ctypes.c_size_t
k32.ReadProcessMemory.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t,
                                  ctypes.POINTER(ctypes.c_size_t)]
k32.CloseHandle.argtypes = [wt.HANDLE]


def pid_do_jogo(nome='PES2021.exe'):
    r = subprocess.run(['tasklist', '/FI', f'IMAGENAME eq {nome}', '/FO', 'CSV', '/NH'],
                       capture_output=True, text=True)
    for linha in r.stdout.splitlines():
        partes = [p.strip('"') for p in linha.split('","')]
        if partes and partes[0].lower() == nome.lower():
            return int(partes[1])
    return None


def regioes(h):
    """Regiões privadas, comprometidas e legíveis do processo."""
    addr, mbi = 0, MBI()
    while k32.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbi), ctypes.sizeof(mbi)):
        base, size = mbi.BaseAddress or 0, mbi.RegionSize
        if (mbi.State == MEM_COMMIT and mbi.Type == MEM_PRIVATE and (mbi.Protect & 0xFF) in READABLE
                and not (mbi.Protect & GUARD_NOACCESS)):
            yield base, size
        addr = base + size
        if addr >= 0x7FFFFFFFFFFF:
            break


def ler(h, base, size, pedaco=16 * 1024 * 1024):
    """Lê a região em pedaços de 16 MB. Em 09/10/2026 ler uma região grande de uma vez dava MemoryError (sem
    mensagem) — era o 'ERRO ao ler a memória ()' do 1º teste da tecla 9. Falha de leitura -> None (pula a região)."""
    partes = []
    try:
        for off in range(0, size, pedaco):
            n_ler = min(pedaco, size - off)
            buf = ctypes.create_string_buffer(n_ler)
            n = ctypes.c_size_t(0)
            if not k32.ReadProcessMemory(h, ctypes.c_void_p(base + off), buf, n_ler, ctypes.byref(n)):
                return b''.join(partes) or None
            partes.append(buf.raw[:n.value])
        return b''.join(partes)
    except MemoryError:
        return None


def _fichas_validas(d, base_tambem=False):
    """Quantas fichas de carreira (assinatura + data válida + registro != cópia base) existem no buffer.
    base_tambem=True conta também as fichas da BASE (registro 0x40A90000): numa carreira recém-criada (conferido em
    10/10/2026, Flamengo de teste) a tabela de carreira ainda não existe e as fichas atuais são as da base."""
    n = 0
    for m in re.finditer(re.escape(SIG), d):
        o = m.start() - 4
        if o < 0 or o + 380 > len(d):
            continue
        y, mo, dd = struct.unpack_from('<HBB', d, o + 12)
        if 2015 <= y <= 2080 and 1 <= mo <= 12 and 1 <= dd <= 31 and \
                (base_tambem or struct.unpack_from('<I', d, o + 124)[0] != 0x40A90000):
            n += 1
    return n


CACHE = __import__('os').path.join(__import__('os').path.dirname(__import__('os').path.abspath(__file__)),
                                   'historico', 'memoria_cache.txt')


def _parece_tabela(d):
    """Filtro rápido: muitas assinaturas e quase todas no mesmo 'passo' de 380 bytes."""
    if d.count(SIG) < 1000:
        return False
    pos, i = [], d.find(SIG)
    while i >= 0 and len(pos) < 3000:
        pos.append((i - 4) % 380)
        i = d.find(SIG, i + 1)
    from collections import Counter
    return Counter(pos).most_common(1)[0][1] >= 0.5 * len(pos)


def foto(destino, log=print):
    """Grava a foto em `destino`. Devolve (n_fichas, endereço da região) ou levanta erro.
    Tenta primeiro a região onde a tabela estava da última vez (rápido); senão varre o processo."""
    import os
    pid = pid_do_jogo()
    if not pid:
        raise RuntimeError('o jogo não está aberto')
    h = k32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
    if not h:
        raise RuntimeError(f'não consegui abrir o processo do jogo (erro {ctypes.get_last_error()})')
    try:
        regs = [(b, s) for b, s in regioes(h) if s <= 256 * 1024 * 1024]
        try:
            ultimo = int(open(CACHE).read().strip(), 16)
        except (OSError, ValueError):
            ultimo = None
        # perto de onde estava da última vez primeiro (o heap costuma ficar na mesma vizinhança)
        ref = ultimo if ultimo is not None else 0x7FF4D9540000
        ordem = sorted(regs, key=lambda r: abs(r[0] - ref))
        melhor = None
        for base, size in ordem:
            d = ler(h, base, size)
            if not d or not _parece_tabela(d):
                continue
            n = _fichas_validas(d)
            if n and (melhor is None or n > melhor[0]):
                melhor = (n, base, d)
            if n >= 15000:
                break           # tabela completa: não precisa olhar o resto
        if not melhor or melhor[0] < 1000:
            # carreira recém-criada: ainda não há tabela de carreira; usa a tabela base (fichas atuais)
            for base, size in regs:
                d = ler(h, base, size)
                if not d or not _parece_tabela(d):
                    continue
                n = _fichas_validas(d, base_tambem=True)
                if n >= 1000 and (melhor is None or n > melhor[0]):
                    melhor = (n, base, d)
        if not melhor:
            raise RuntimeError('não achei a tabela de jogadores na memória (a carreira está carregada?)')
        n, base, d = melhor
        marca = b''
        if d.find(MARCA_DATA) < 0:   # marcador da data costuma estar na mesma região; senão procura
            for b2, s2 in regs:
                x = ler(h, b2, s2)
                i = x.find(MARCA_DATA) if x else -1
                if i > 0:
                    marca = bytes(400) + x[max(0, i - 64):i + 64]
                    break
        with open(destino + '.tmp', 'wb') as f:
            f.write(d)
            f.write(marca)
        import time
        for i in range(40):   # 11/10/2026: outro processo lendo a foto naquele instante (WinError 32): tenta de novo
            try:
                os.replace(destino + '.tmp', destino)
                break
            except PermissionError:
                if i == 39:
                    raise
                time.sleep(0.25)
        os.makedirs(os.path.dirname(CACHE), exist_ok=True)
        with open(CACHE, 'w') as f:
            f.write(hex(base))
        log(f'foto da memória: {n} fichas na região {base:#x} ({len(d) // 1024 // 1024} MB)')
        return n, base
    finally:
        k32.CloseHandle(h)


if __name__ == '__main__':
    import sys
    foto(sys.argv[1] if len(sys.argv) > 1 else 'mercado_snap.bin')
