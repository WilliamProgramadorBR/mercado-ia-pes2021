# Mercado IA — autor: William (https://github.com/WilliamProgramadorBR)
"""Caixa de MENSAGENS da Master League (data.dat descriptografado): leitura e inserção de mensagens nativas.

Descoberto em 09/10/2026:
  - fila circular de 129 registros de 80 bytes (estava em 0xbe8b80 em todos os saves; localizada e conferida);
  - a PRÓXIMA POSIÇÃO livre é 1 byte em caixa + 0x5704 (conferido em 3 saves: 49, 55, 96 = mais nova + 1);
    o jogo escreve a mensagem nessa posição e soma 1 (volta a 0 depois de 128).
  - registro: +0 3 bytes, +4 u32 TIPO (modelo de texto), +8 data (u16 ano, u8 mês, u8 dia),
    +12/+16 parâmetros, +20 u32 1 = NÃO LIDA (bolinha azul), +28 código de clube, +40/+48/+56 jogadores (reg, id),
    +64 "mais N", +72 código extra (ex.: função no tipo 90), +76 outra data.
  - TESTE NO JOGO OK (09/10/2026): tipo 340 inserido apareceu com os nomes pedidos (Mainoo, Bruno).
  - NÃO há texto livre: o jogo monta o texto pelo tipo. Catálogo de tipos: ver memória do projeto / TIPOS abaixo.
"""
import os
import struct

REC = 80
N = 129
INDICE_REL = 0x5704
TIPOS = {26: 'Resultados da observação', 27: 'Negociações com X', 33: 'Saída de jogador', 35: 'Aviso de chegada',
         81: 'Evolução de X (assistente: muito promissor, use nas partidas)', 89: 'Apelido do X (torcida)',
         99: 'Transferência confirmada (saída de graça, contrato não renovado)', 22: 'Convocações de seleções',
         24: 'Hora de fazer suas escolhas (seleção)', 11: 'Cansaço depois de partidas pela seleção',
         13: 'Desafio da Seleção do Mundo', 282: 'Resultados da observação (N jogadores)',
         36: 'Contratos (dir. esportivo)', 83: 'Relatório mensal', 85: 'Jogador do torneio', 90: 'Troca na função',
         91: 'Relatório mensal de treino', 92: 'Programação do mês', 93: 'Receita do mês', 277: 'Suspensão',
         299: 'Contratos (dir. esportivo)', 340: '11 melhores do mês', 596: '11 melhores do mês'}


def _data_ok(d, o):
    y, m, dd = struct.unpack_from('<HBB', d, o + 8)
    return 2015 <= y <= 2080 and 1 <= m <= 12 and 1 <= dd <= 31


def achar_caixa(d, perto=0xBE8B80):
    """Início da fila. Confere: 129 registros com data válida e o byte de índice = mais nova + 1."""
    def ok(ini):
        if ini < 0 or ini + N * REC > len(d) or not all(_data_ok(d, ini + i * REC) for i in range(N)):
            return False
        if _data_ok(d, ini - REC) or _data_ok(d, ini + N * REC):
            return False
        # a posição anterior ao contador tem que ter a data mais recente da fila (pode haver empate de datas:
        # na virada de temporada chegam muitas mensagens no mesmo dia — 1º teste ingênuo falhou em 01/07/2034)
        idx = d[ini + INDICE_REL]
        if idx >= N:
            return False
        datas = [struct.unpack_from('<HBB', d, ini + i * REC + 8) for i in range(N)]
        return datas[(idx - 1) % N] == max(datas)
    if ok(perto):
        return perto
    for o in range(0, len(d) - N * REC, 4):
        if _data_ok(d, o) and ok(o):
            return o
    raise RuntimeError('caixa de mensagens não encontrada com segurança')


def mais_nova(d, ini):
    """Posição da mensagem mais nova = a anterior ao contador (o jogo escreve em sequência)."""
    return (d[ini + INDICE_REL] - 1) % N


def listar(d):
    ini = achar_caixa(d)
    out = []
    for i in range(N):
        o = ini + i * REC
        out.append({'slot': i, 'tipo': struct.unpack_from('<I', d, o + 4)[0],
                    'data': struct.unpack_from('<HBB', d, o + 8), 'jogador': struct.unpack_from('<II', d, o + 40),
                    'clube': struct.unpack_from('<I', d, o + 28)[0]})
    return out


MODELOS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'historico', 'modelos_mensagem')


def modelo(d, tipo):
    """Registro real mais recente desse tipo (para copiar o formato exato). Guarda uma cópia em
    historico/modelos_mensagem/<tipo>.bin; se o tipo já saiu da caixa (a fila dá a volta), usa a cópia."""
    ini = achar_caixa(d)
    cands = [(struct.unpack_from('<HBB', d, ini + i * REC + 8), i) for i in range(N)
             if struct.unpack_from('<I', d, ini + i * REC + 4)[0] == tipo]
    arq = os.path.join(MODELOS, f'{tipo}.bin')
    if cands:
        i = max(cands)[1]
        r = bytes(d[ini + i * REC:ini + (i + 1) * REC])
        os.makedirs(MODELOS, exist_ok=True)
        with open(arq, 'wb') as f:
            f.write(r)
        return r
    if os.path.exists(arq):
        r = open(arq, 'rb').read()
        if len(r) == REC and struct.unpack_from('<I', r, 4)[0] == tipo:
            return r
    raise RuntimeError(f'não há mensagem do tipo {tipo} na caixa (nem cópia guardada) para servir de modelo')


def guardar_modelos(d):
    """Guarda uma cópia de cada tipo presente na caixa (chamado a cada reunião)."""
    ini = achar_caixa(d)
    for t in {struct.unpack_from('<I', d, ini + i * REC + 4)[0] for i in range(N)}:
        modelo(d, t)


def inserir(d, tipo, data, jogadores=(), clube=None, extra=None):
    """Cópia do data.dat com UMA mensagem nova (tipo `tipo`, data (a, m, d)), escrita na próxima posição livre.
    jogadores: até 3 pares (reg, id); clube: código u32; extra: dict {deslocamento: (fmt, valor)}."""
    d = bytearray(d)
    ini = achar_caixa(bytes(d))
    pos = d[ini + INDICE_REL]
    r = bytearray(modelo(bytes(d), tipo))
    r[0:3] = b'\xff\xff\xff'
    struct.pack_into('<HBB', r, 8, *data)
    struct.pack_into('<I', r, 20, 1)          # NÃO LIDA (bolinha azul) — as mensagens novas do jogo têm 1 aqui
    if jogadores:
        # preenche as vagas pedidas e LIMPA as outras (o modelo pode trazer jogadores da mensagem original:
        # no 1º teste veio o Omoregie na 3ª vaga)
        for n in range(3):
            k = jogadores[n] if n < len(jogadores) else (0xFFFF, 0)
            struct.pack_into('<II', r, 40 + 8 * n, *k)
    if clube is not None:
        struct.pack_into('<I', r, 28, clube)
    for off, (fmt, val) in (extra or {}).items():
        struct.pack_into(fmt, r, off, val)
    o = ini + pos * REC
    d[o:o + REC] = r
    d[ini + INDICE_REL] = (pos + 1) % N
    return bytes(d), pos
