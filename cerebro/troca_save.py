"""Troca segura do save da Master League (usada pelo mercado e pelo vestiário, inclusive no modo automático).

  1. confere que o save no disco ainda é EXATAMENTE o que foi lido no começo (byte a byte): se o jogo salvou
     de novo enquanto processávamos, NÃO grava nada (senão apagaríamos o progresso novo do jogador);
  2. escreve o arquivo novo ao lado (mesma pasta) e troca de uma vez (os.replace, atômico): o jogo nunca lê um
     save pela metade;
  3. tenta de novo por alguns segundos se o arquivo estiver preso (OneDrive/antivírus).
"""
import ctypes
import ctypes.wintypes as wt
import msvcrt
import os
import shutil
import time

_k32 = ctypes.WinDLL('kernel32', use_last_error=True)
_k32.CreateFileW.restype = wt.HANDLE
_k32.CreateFileW.argtypes = [wt.LPCWSTR, wt.DWORD, wt.DWORD, ctypes.c_void_p, wt.DWORD, wt.DWORD, wt.HANDLE]
GENERIC_READ, OPEN_EXISTING = 0x80000000, 3
SHARE_TUDO = 0x1 | 0x2 | 0x4          # FILE_SHARE_READ | WRITE | DELETE
INVALIDO = wt.HANDLE(-1).value


class SaveMudou(RuntimeError):
    pass


def ler_compartilhado(path):
    """Lê o arquivo SEM impedir que o jogo o substitua ao mesmo tempo.
    O open() do Python não libera FILE_SHARE_DELETE; se o jogo tenta trocar o save (salvar) enquanto lemos, o
    salvamento dele falha ("não foi possível salvar" — visto em 09/10/2026 com o modo automático)."""
    for _ in range(10):
        h = _k32.CreateFileW(path, GENERIC_READ, SHARE_TUDO, None, OPEN_EXISTING, 0, None)
        if h != INVALIDO:
            fd = msvcrt.open_osfhandle(h, os.O_RDONLY | os.O_BINARY)
            with os.fdopen(fd, 'rb') as f:
                return f.read()
        time.sleep(0.5)
    raise OSError(f'não consegui ler {path} (erro {ctypes.get_last_error()})')


def copiar_compartilhado(src, dst):
    """Cópia do save (mantém a data) sem bloquear o jogo."""
    dados = ler_compartilhado(src)
    with open(dst, 'wb') as f:
        f.write(dados)
    st = os.stat(src)
    os.utime(dst, (st.st_atime, st.st_mtime))


def substituir(ml_path, novo_path, original_copia):
    with open(original_copia, 'rb') as f:
        original = f.read()
    atual = ler_compartilhado(ml_path)
    if atual != original:
        raise SaveMudou('o save mudou durante o processamento (o jogo salvou de novo); save NÃO foi alterado')
    tmp = ml_path + '.mia_tmp'
    shutil.copy2(novo_path, tmp)
    for _ in range(15):
        try:
            os.replace(tmp, ml_path)
            return
        except PermissionError:
            time.sleep(1)
    try:
        os.remove(tmp)
    except OSError:
        pass
    raise RuntimeError('não foi possível substituir o save (arquivo preso); save NÃO foi alterado')
