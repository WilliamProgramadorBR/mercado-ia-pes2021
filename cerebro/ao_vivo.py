# Mercado IA — autor: William (https://github.com/WilliamProgramadorBR)
"""Escrita AO VIVO na memória do jogo (fase 1: mensagens) — para não precisar recarregar a carreira.

Ideia: o jogo trabalha com os dados na memória e grava o save a partir deles. Se colocarmos a mudança NA MEMÓRIA
(com o jogo parado no menu), o próprio jogo passa a mostrá-la e a grava no próximo save.

Segurança:
  - a caixa de mensagens é localizada com as MESMAS conferências do save (129 registros de 80 bytes com data
    válida + contador = posição da mais nova + 1);
  - antes de escrever, relê os bytes do alvo e confere que são exatamente os que foram analisados;
  - escreve só o registro da mensagem (80 bytes) e o contador (1 byte), em páginas graváveis;
  - lê de volta e confere.
Uso (teste): python ao_vivo.py mensagem <tipo> <reg:id> [--escrever]
             python ao_vivo.py seta <data.dat> <reg:id> <0-4> [--escrever]
  sem --escrever: só localiza, monta e mostra o que faria (nada é escrito).
"""
import ctypes
import ctypes.wintypes as wt
import os
import struct
import sys

import memoria as M
import mensagens_save as MS

PROCESS_VM_WRITE = 0x0020
PROCESS_VM_OPERATION = 0x0008
GRAVAVEL = {0x04, 0x08, 0x40, 0x80}   # READWRITE, WRITECOPY, EXECUTE_READWRITE, EXECUTE_WRITECOPY

M.k32.WriteProcessMemory.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t,
                                     ctypes.POINTER(ctypes.c_size_t)]


def abrir(escrita=False):
    pid = M.pid_do_jogo()
    if not pid:
        raise RuntimeError('o jogo não está aberto')
    acesso = M.PROCESS_QUERY_INFORMATION | M.PROCESS_VM_READ
    if escrita:
        acesso |= PROCESS_VM_WRITE | PROCESS_VM_OPERATION
    h = M.k32.OpenProcess(acesso, False, pid)
    if not h:
        raise RuntimeError(f'não consegui abrir o processo do jogo (erro {ctypes.get_last_error()})')
    return h


def gravavel(h, addr, n):
    mbi = M.MBI()
    a = addr
    while a < addr + n:
        if not M.k32.VirtualQueryEx(h, ctypes.c_void_p(a), ctypes.byref(mbi), ctypes.sizeof(mbi)):
            return False
        if mbi.State != M.MEM_COMMIT or (mbi.Protect & 0xFF) not in GRAVAVEL or (mbi.Protect & 0x100):
            return False
        a = (mbi.BaseAddress or 0) + mbi.RegionSize
    return True


def escrever(h, addr, dados, esperado):
    """Confere que a memória ainda tem `esperado`, escreve `dados` e lê de volta.
    Usa a trava 'memoria': Central e vigia nunca escrevem ao mesmo tempo."""
    from trava import trava
    with trava('memoria'):
        _escrever(h, addr, dados, esperado)


def _escrever(h, addr, dados, esperado):
    atual = M.ler(h, addr, len(esperado))
    if atual != esperado:
        raise RuntimeError(f'memória mudou em {addr:#x} desde a análise; nada escrito')
    if not gravavel(h, addr, len(dados)):
        raise RuntimeError(f'região {addr:#x} não é gravável; nada escrito')
    n = ctypes.c_size_t(0)
    buf = ctypes.create_string_buffer(dados, len(dados))
    if not M.k32.WriteProcessMemory(h, ctypes.c_void_p(addr), buf, len(dados), ctypes.byref(n)) or n.value != len(dados):
        raise RuntimeError(f'falha ao escrever em {addr:#x} (erro {ctypes.get_last_error()})')
    if M.ler(h, addr, len(dados)) != dados:
        raise RuntimeError(f'conferência após escrever falhou em {addr:#x}')


CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'historico', 'caixa_memoria_cache.txt')


def achar_caixa_memoria(h):
    """[(endereço da caixa, buffer da região, base da região, início no buffer)] — normalmente exatamente 1.
    Tenta primeiro a região onde a caixa estava da última vez (rápido); senão varre o processo (~2 min)."""
    try:
        ultimo = int(open(CACHE).read().strip(), 16)
    except (OSError, ValueError):
        ultimo = None
    if ultimo:
        for base, size in M.regioes(h):
            if base <= ultimo < base + size:
                x = M.ler(h, base, size)
                try:
                    ini = MS.achar_caixa(x, perto=ultimo - base) if x else None
                except RuntimeError:
                    ini = None
                if ini == ultimo - base:
                    return [(ultimo, x, base, ini)]
    achadas = _varrer(h)
    if len(achadas) == 1:
        os.makedirs(os.path.dirname(CACHE), exist_ok=True)
        with open(CACHE, 'w') as f:
            f.write(hex(achadas[0][0]))
    return achadas


def _varrer(h):
    achadas = []
    for base, size in M.regioes(h):
        if size > 96 * 1024 * 1024:
            continue
        x = M.ler(h, base, size)
        if not x or x.count(b'\xff\xff\xff\x00') < 50:
            continue
        try:
            ini = MS.achar_caixa(x, perto=-1)
        except RuntimeError:
            continue
        achadas.append((base + ini, x, base, ini))
    return achadas


def mensagem(tipo, jogadores=(), extra=None, escrever_de_verdade=False, log=print):
    h = abrir(escrita=escrever_de_verdade)
    try:
        achadas = achar_caixa_memoria(h)
        if len(achadas) != 1:
            raise RuntimeError(f'caixa de mensagens na memória: {len(achadas)} candidatas (precisa ser 1); nada escrito')
        addr, x, base, ini = achadas[0]
        nova_pos = MS.mais_nova(x, ini)
        hoje = struct.unpack_from('<HBB', x, ini + nova_pos * MS.REC + 8)
        x2, slot = MS.inserir(x, tipo, hoje, jogadores=list(jogadores), extra=extra)
        a = ini + slot * MS.REC
        idx = ini + MS.INDICE_REL
        assert x[:a] == x2[:a] and x[a + MS.REC:idx] == x2[a + MS.REC:idx] and x[idx + 1:] == x2[idx + 1:]
        log(f'caixa na memória em {addr:#x}; mensagem tipo {tipo} ({MS.TIPOS.get(tipo, "?")}) com data '
            f'{hoje[2]:02d}/{hoje[1]:02d}/{hoje[0]} na posição {slot}; contador {x[idx]} -> {x2[idx]}')
        if not escrever_de_verdade:
            log('ENSAIO: nada foi escrito na memória.')
            return slot
        escrever(h, base + a, x2[a:a + MS.REC], x[a:a + MS.REC])
        escrever(h, base + idx, x2[idx:idx + 1], x[idx:idx + 1])
        log('ESCRITO NA MEMÓRIA do jogo (mensagem + contador), conferido.')
        return slot
    finally:
        M.k32.CloseHandle(h)


def achar_apelido_memoria(h, k, rec_save):
    """Endereço do campo de apelido do jogador `k` no bloco de carreira dele na região das fichas.
    Descoberto em 09/10/2026: nesse bloco o apelido fica 300 bytes depois do par (registro, id) da ficha, entre a
    função/personalidade (8 bytes antes, iguais ao save +72..+79) e o salário (4 bytes depois, igual ao save +84).
    Só aceita a posição se essas duas vizinhanças baterem com o registro do save."""
    alvo = struct.pack('<II', *k)
    achados = []
    for base, size in M.regioes(h):
        if size > 96 * 1024 * 1024:
            continue
        x = M.ler(h, base, size)
        if not x:
            continue
        i = x.find(alvo)
        while i >= 0:
            p = i + 300
            if p + 8 <= len(x) and x[p - 8:p] == rec_save[72:80] and x[p + 4:p + 8] == rec_save[84:88]:
                achados.append((base + p, x[p:p + 4]))
            i = x.find(alvo, i + 1)
    return achados


SETA_REL = 283   # byte da seta no bloco de carreira (a partir do par registro/id); +282 = condição (0-100)


def achar_carreiras_memoria(h, recs):
    """{k: [endereço do par (registro, id) do bloco de carreira]} para vários jogadores numa varredura só.
    Mesma âncora do apelido: função/personalidade (+292, = save +72..+79) e salário (+304, = save +84)."""
    alvos = {struct.pack('<II', *k): (k, r) for k, r in recs.items()}
    achados = {k: [] for k in recs}
    for base, size in M.regioes(h):
        if size > 96 * 1024 * 1024:
            continue
        x = M.ler(h, base, size)
        if not x:
            continue
        for alvo, (k, r) in alvos.items():
            i = x.find(alvo)
            while i >= 0:
                p = i + 300
                if p + 8 <= len(x) and x[p - 8:p] == r[72:80] and x[p + 4:p + 8] == r[84:88]:
                    achados[k].append(base + i)
                i = x.find(alvo, i + 1)
    return achados


def setas(mudancas, recs, escrever_de_verdade=False, log=print, esperado=None):
    """Troca a SETA DE CONDIÇÃO de vários jogadores NA MEMÓRIA. mudancas = {k: seta 0-4}; recs = {k: registro do save}.
    esperado = {k: seta que o save tem}: se a memória já estiver diferente (o jogo recalculou depois de salvar), pula.
    Descoberto em 09/10/2026 (fase 3): no bloco de carreira, +282 = condição e +283 = 0x50 | seta (bits 0-2) —
    bateu com a tela nos 21 jogadores do elenco. Só mexe nos 3 bits da seta; o resto do byte fica como está.
    Devolve {k: (seta antiga, seta nova)} dos que foram trocados."""
    h = abrir(escrita=escrever_de_verdade)
    feito = {}
    try:
        achados = achar_carreiras_memoria(h, {k: recs[k] for k in mudancas})
        for k, nova in mudancas.items():
            assert 0 <= nova <= 4
            # 1 cópia no menu; 2 na tela pré-jogo (o jogo monta uma lista do elenco com passo 392 bytes) -> escreve nas duas
            addrs = [a + SETA_REL - 1 for a in achados[k]]
            lidos = [M.ler(h, a, 2) for a in addrs]
            if not 1 <= len(addrs) <= 2 or len(set(lidos)) != 1:
                log(f'{k}: bloco de carreira na memória com {len(addrs)} candidato(s) diferentes; pulado')
                continue
            cond_seta = lidos[0]
            # condição = 7 bits (o bit 7 é um marcador do jogo: 228 = 100 + 0x80)
            if not cond_seta or cond_seta[0] & 0x7F > 100 or cond_seta[1] & 7 > 4:
                log(f'{k}: bytes inesperados em {addrs[0]:#x} ({cond_seta.hex() if cond_seta else "?"}); pulado')
                continue
            velho = cond_seta[1]
            aceitos = esperado.get(k) if esperado else None
            if aceitos is not None and not isinstance(aceitos, (set, list, tuple)):
                aceitos = {aceitos}
            if aceitos is not None and velho & 7 not in aceitos:
                log(f'{k}: seta na memória ({velho & 7}) não é a esperada ({sorted(aceitos)}); pulado')
                continue
            novo = (velho & ~7) | nova
            log(f'{k}: seta {velho & 7} -> {nova} (condição {cond_seta[0] & 0x7F}; {len(addrs)} cópia(s))')
            if escrever_de_verdade and novo != velho:
                for a in addrs:
                    escrever(h, a + 1, bytes([novo]), bytes([velho]))
            feito[k] = (velho & 7, nova)
        log('SETAS ESCRITAS NA MEMÓRIA, conferidas.' if escrever_de_verdade else 'ENSAIO: nada foi escrito na memória.')
        return feito
    finally:
        M.k32.CloseHandle(h)


def ajustar_carreira(mudancas, recs, escrever_de_verdade=False, log=print):
    """Condição física (+282, 7 bits; bit 7 é marcador do jogo) e/ou seta (+283, bits 0-2) de vários jogadores.
    mudancas = {k: {'cond_delta': int, 'seta': 0-4}} (qualquer um dos dois). A condição é ajustada sobre o valor que
    ESTÁ na memória (o jogo recupera/gasta condição sozinho), limitada a 40..100.
    Etapa 2 (10/10/2026): plano de treino e pedidos de descanso. Devolve {k: {'cond': (a, b), 'seta': (a, b)}}."""
    h = abrir(escrita=escrever_de_verdade)
    feito = {}
    try:
        achados = achar_carreiras_memoria(h, {k: recs[k] for k in mudancas})
        for k, m in mudancas.items():
            addrs = [a + SETA_REL - 1 for a in achados[k]]
            lidos = [M.ler(h, a, 2) for a in addrs]
            if not 1 <= len(addrs) <= 2 or len(set(lidos)) != 1 or not lidos[0]:
                log(f'{k}: bloco de carreira na memória com {len(addrs)} candidato(s) diferentes; pulado')
                continue
            c0, s0 = lidos[0]
            if c0 & 0x7F > 100 or s0 & 7 > 4:
                log(f'{k}: bytes inesperados ({lidos[0].hex()}); pulado')
                continue
            cond = c0 & 0x7F
            if 'cond_delta' in m:
                cond = max(40, min(100, cond + m['cond_delta']))
            seta = m.get('seta', s0 & 7)
            assert 0 <= seta <= 4
            novo = bytes([(c0 & 0x80) | cond, (s0 & ~7 & 0xFF) | seta])
            r = {}
            if novo[0] != c0:
                r['cond'] = (c0 & 0x7F, cond)
            if novo[1] != s0:
                r['seta'] = (s0 & 7, seta)
            if not r:
                continue
            log(f'{k}: ' + ', '.join(f'{n} {a} -> {b}' for n, (a, b) in r.items()) + f' ({len(addrs)} cópia(s))')
            if escrever_de_verdade:
                for a in addrs:
                    escrever(h, a, novo, lidos[0])
            feito[k] = r
        log('ESCRITO NA MEMÓRIA, conferido.' if escrever_de_verdade else 'ENSAIO: nada foi escrito na memória.')
        return feito
    finally:
        M.k32.CloseHandle(h)


def apelido(k, codigo, rec_save, escrever_de_verdade=False, log=print):
    """Dá o apelido `codigo` ao jogador `k` NA MEMÓRIA (bloco de carreira) + mensagem nativa 'Apelido do X'."""
    u = (0x1D << 16) | codigo
    h = abrir(escrita=escrever_de_verdade)
    try:
        achados = achar_apelido_memoria(h, k, rec_save)
        if len(achados) != 1:
            raise RuntimeError(f'campo de apelido na memória: {len(achados)} candidatos (precisa ser 1); nada escrito')
        addr, atual = achados[0]
        log(f'campo de apelido em {addr:#x}: atual {struct.unpack("<I", atual)[0]:#x} -> novo {u:#x}')
        if escrever_de_verdade:
            escrever(h, addr, struct.pack('<I', u), atual)
            log('APELIDO ESCRITO NA MEMÓRIA, conferido.')
    finally:
        M.k32.CloseHandle(h)
    return mensagem(89, [k], extra={64: ('<I', u)}, escrever_de_verdade=escrever_de_verdade, log=log)


def achar_orcamento_memoria(h, referencia_reais):
    """Endereço do ORÇAMENTO DE TRANSFERÊNCIAS do usuário na memória: o mesmo bloco de finanças do save
    (09/10/2026: bloco idêntico byte a byte ao do save, em 0x7ff4dac2cc04 nessa sessão).
    Exige os marcadores do save (-44 == 108, -40 == 0xFFFF) e valor coerente com `referencia_reais`
    (último orçamento conhecido, ±10%)."""
    achados = []
    lo, hi = referencia_reais * 0.9 / 430, referencia_reais * 1.1 / 430
    for base, size in M.regioes(h):
        if size > 96 * 1024 * 1024:
            continue
        x = M.ler(h, base, size)
        if not x:
            continue
        i = x.find(b'\x6c\x00\x00\x00\xff\xff\x00\x00')
        while i >= 0:
            p = i + 44
            if p + 4 <= len(x):
                v = struct.unpack_from('<I', x, p)[0]
                if lo <= v <= hi:
                    achados.append((base + p, v))
            i = x.find(b'\x6c\x00\x00\x00\xff\xff\x00\x00', i + 1)
    return achados


def orcamento(novo_reais, referencia_reais, escrever_de_verdade=False, log=print, delta_reais=None):
    """Troca o orçamento de transferências NA MEMÓRIA (o jogo grava no próximo save).
    Com delta_reais, soma o ajuste ao valor que ESTÁ na memória (respeita receitas/gastos que o jogo já lançou)."""
    h = abrir(escrita=escrever_de_verdade)
    try:
        achados = achar_orcamento_memoria(h, referencia_reais)
        if len(achados) != 1:
            raise RuntimeError(f'orçamento na memória: {len(achados)} candidatos (precisa ser 1); nada escrito')
        addr, v = achados[0]
        if delta_reais is not None:
            novo_reais = v * 430 + delta_reais
        novo = int(round(novo_reais / 430))
        assert novo > 0, 'orçamento ficaria negativo'
        log(f'orçamento na memória em {addr:#x}: R$ {v * 430:,} -> R$ {novo * 430:,}'.replace(',', '.'))
        if escrever_de_verdade:
            escrever(h, addr, struct.pack('<I', novo), struct.pack('<I', v))
            log('ORÇAMENTO ESCRITO NA MEMÓRIA, conferido.')
        return v * 430, novo * 430
    finally:
        M.k32.CloseHandle(h)


VERBA_REL = 20   # verba ANUAL de salários: bloco de finanças +20 (x430). O "Orçam. de salário" da tela é
                 # verba − salários do elenco (descoberto em 10/10/2026 no laboratório; o jogo mantém o valor escrito)


def verba_salarios(delta_reais, referencia_orcamento, escrever_de_verdade=False, log=print):
    """Soma `delta_reais` à verba anual de salários NA MEMÓRIA (patrocínio, sanções). Devolve (antes, depois) em R$."""
    h = abrir(escrita=escrever_de_verdade)
    try:
        achados = achar_orcamento_memoria(h, referencia_orcamento)
        if len(achados) != 1:
            raise RuntimeError(f'bloco de finanças na memória: {len(achados)} candidatos (precisa ser 1); nada escrito')
        addr = achados[0][0] + VERBA_REL
        atual = M.ler(h, addr, 4)
        v = struct.unpack('<i', atual)[0]
        novo = v + int(round(delta_reais / 430))
        assert 0 < novo < 2_000_000_000 // 430, 'verba fora do esperado'
        log(f'verba de salários em {addr:#x}: R$ {v * 430:,} -> R$ {novo * 430:,}'.replace(',', '.'))
        if escrever_de_verdade:
            escrever(h, addr, struct.pack('<i', novo), atual)
        return v * 430, novo * 430
    finally:
        M.k32.CloseHandle(h)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if args and args[0] == 'mensagem':
        jogs = [tuple(int(v) for v in a.split(':')) for a in args[2:]]
        mensagem(int(args[1]), jogs, escrever_de_verdade='--escrever' in sys.argv)
    elif args and args[0] == 'seta':
        # python ao_vivo.py seta <data.dat descriptografado> <reg:id> <0-4> [--escrever]
        import jogadores_save as js
        recs = js.registros(js.blob(open(args[1], 'rb').read()))
        k = tuple(int(v) for v in args[2].split(':'))
        setas({k: int(args[3])}, recs, escrever_de_verdade='--escrever' in sys.argv)
    else:
        print(__doc__)
