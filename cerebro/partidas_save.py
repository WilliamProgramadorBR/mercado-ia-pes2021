# Mercado IA — autor: William (https://github.com/WilliamProgramadorBR)
"""Leitura das SÚMULAS de partidas guardadas no save da Master League (data.dat descriptografado).

Descoberto em 09/10/2026 comparando o save antes/depois de Burnley 1 x 1 Man Utd (03/01/2034,
gols de Victor Muñoz e Wallace). Formato (registro de 596 bytes, fora dos blocos comprimidos):
  cabeçalho (36 bytes):
    +0  u32 número da partida (sequencial)
    +4  u8 competição (0x11 = Premier League do Man Utd), +5 u8 ?, +6 u8 RODADA (Burnley = 19), +7 u8 0x60
    +8  data (u16 ano, u8 mês, u8 dia)            +12 u32 0
    +16 u32 11..16 (varia por jogo da mesma liga: horário do jogo?)
    +20 u32 time 1 (mandante) — índice na tabela de times = valor & 0x3FFF (bits altos = marcadores)
    +24 u32 time 2 (visitante)
    +28 u8 gols do time 1, +31 u8 gols do time 2  (PROVÁVEL; conferido pela soma das linhas)
  depois: 17 linhas de 16 bytes do time 1 e 17 do time 2 (0xFFFF no registro = vaga vazia) e 16 bytes finais.
  linha: u32 registro, u32 id, u8 gols, u8 assistências (PROVÁVEL: Mejbri = 1 no gol do Burnley), u8, u8,
         u32 compactado: bits 0-6 minutos jogados, bits 7-13 nota x10 (Wallace 77 = 7,7), bits 14-17 função
         (0 goleiro .. 9 centroavante), bit 21 titular, bit 22 relacionado.
"""
import struct

REC = 596
AGENDADO = (0x20, 0x10, 0x00)   # +7 de jogo ainda não disputado (liga/grupos, volta e ida do mata-mata)
FAIXA = (0x300000, 0x980000)   # onde ficam as súmulas (10/10/2026: as do Brasileirão começam ~0x32a000)
SLOTS = 17


def _linha(d, o):
    reg, pid, st, pk = struct.unpack_from('<IIII', d, o)
    if reg == 0xFFFF:
        return None
    return {'reg': reg, 'pid': pid, 'gols': st & 0xFF, 'assist': (st >> 8) & 0xFF,
            'minutos': pk & 0x7F, 'nota': ((pk >> 7) & 0x7F) / 10, 'funcao': (pk >> 14) & 0xF,
            'titular': bool(pk & (1 << 21))}


def _cabecalho_ok(d, o):
    if o + REC > len(d):
        return False
    y, m, dd = struct.unpack_from('<HBB', d, o + 8)
    # +16: pequeno na maioria das ligas, alto na Champions (0x3712) e com u16 alto na FA Cup (0x2A0013): 11/10/2026 não
    # é mais conferido (a exigência < 0x10000 descartava TODAS as súmulas e jogos da FA Cup; validação = linhas/placar).
    return 2015 <= y <= 2080 and 1 <= m <= 12 and 1 <= dd <= 31 and \
        struct.unpack_from('<I', d, o + 12)[0] <= 3   # 0 ou 1 (10/10/2026: 1 = maioria, inclusive o Brasileirão)


def partida(d, o):
    num, = struct.unpack_from('<I', d, o)
    y, m, dd = struct.unpack_from('<HBB', d, o + 8)
    t1, t2 = struct.unpack_from('<II', d, o + 20)
    times = []
    for k in range(2):
        base = o + 36 + k * SLOTS * 16
        times.append([x for x in (_linha(d, base + i * 16) for i in range(SLOTS)) if x])
    return {'pos': o, 'num': num, 'data': (y, m, dd), 'comp': d[o + 4], 'rodada': d[o + 6], 'flag': d[o + 7],
            'time1': t1 & 0x3FFF, 'time2': t2 & 0x3FFF, 'gols1': d[o + 28], 'gols2': d[o + 31],
            'linhas1': times[0], 'linhas2': times[1]}


_MEMO = {}


def _memo(nome, d, ini, fim, calc):
    """12/10/2026: a reunião varria o save inteiro várias vezes (agenda ~3 s, súmulas ~5 s, até 6 vezes cada).
    Guarda o último resultado de cada varredura para o MESMO objeto de save (referência guardada: o id não é
    reaproveitado por outro arquivo). Devolve cópias rasas, para ninguém alterar o resultado guardado."""
    k = (nome, ini, fim)
    m = _MEMO.get(k)
    if m is None or m[0] is not d:
        m = (d, calc())
        _MEMO[k] = m
    return [dict(p) for p in m[1]]


def todas(d, ini=0, fim=None):
    if isinstance(d, bytes):
        return _memo('todas', d, ini, fim, lambda: _todas(d, ini, fim))
    return _todas(d, ini, fim)


def _todas(d, ini=0, fim=None):
    """Varre o save atrás de todas as súmulas válidas (placar do cabeçalho = soma dos gols das linhas).
    Em 09/10/2026 achou 1436 súmulas entre 0x4d83ec e 0x8b82c0 (temporada 2033/34 e fim de 2032/33).
    Súmulas com gol contra provavelmente ficam de fora (o placar não bate com a soma)."""
    fim = fim or len(d) - REC
    out = []
    for o in range(ini, fim, 4):
        if d[o + 13:o + 16] != bytes(3) or d[o + 12] > 3 or not _cabecalho_ok(d, o):
            continue
        p = partida(d, o)
        if not p['linhas1'] or not p['linhas2'] or p['time1'] >= 730 or p['time2'] >= 730:
            continue
        if (sum(x['gols'] for x in p['linhas1']), sum(x['gols'] for x in p['linhas2'])) != (p['gols1'], p['gols2']):
            continue
        out.append(p)
    return out


def partidas(d, ancora=None):
    """Todas as súmulas encadeadas a partir de uma âncora (posição de um cabeçalho conhecido).
    Sem âncora, procura o primeiro cabeçalho válido cujas linhas citam jogadores (registro/id plausíveis)."""
    if ancora is None:
        raise ValueError('passe a posição de um cabeçalho conhecido')
    out = []
    o = ancora
    while o >= REC and _cabecalho_ok(d, o - REC):
        o -= REC
    while _cabecalho_ok(d, o):
        out.append(partida(d, o))
        o += REC
    return out


def agenda(d, ini=None, fim=None):
    if isinstance(d, bytes):
        return _memo('agenda', d, ini, fim, lambda: _agenda(d, ini, fim))
    return _agenda(d, ini, fim)


def _agenda(d, ini=None, fim=None):
    """JOGOS AGENDADOS (calendário de todas as competições). Mesmo registro de 596 B das súmulas, ainda sem placar:
    o byte +7 é 0x20 (agendado) em vez de 0x60 (jogado). Descoberto em 10/10/2026 (Mirassol x Remo, 08/08/2026,
    Brasileirão rodada 17, aparecia em "Próximas partidas"). Devolve [{'data', 'comp', 'rodada', 'time1', 'time2'}]."""
    ini, fim = ini or FAIXA[0], fim or FAIXA[1]
    out = []
    for o in range(ini, min(fim, len(d) - REC), 4):
        # +7 (11/10/2026): 0x20 agendado (liga/grupos); no MATA-MATA 0x00 = ida agendada, 0x10 = volta agendada
        # (jogados: 0x60 liga/grupos, 0x40 ida, 0x50 volta -> bit 0x40)
        if d[o + 7] not in AGENDADO or d[o + 13:o + 16] != bytes(3) or d[o + 12] > 3 or not _cabecalho_ok(d, o):
            continue
        if d[o + 7] != 0x20 and (d[o + 28] or d[o + 31]):
            continue
        t1, t2 = struct.unpack_from('<II', d, o + 20)
        t1, t2 = t1 & 0x3FFF, t2 & 0x3FFF
        if t1 >= 730 or t2 >= 730 or t1 == t2:
            continue
        y, m, dd = struct.unpack_from('<HBB', d, o + 8)
        out.append({'pos': o, 'data': (y, m, dd), 'comp': d[o + 4], 'rodada': d[o + 6], 'time1': t1, 'time2': t2,
                    'flag': d[o + 7], 'gols1': 0, 'gols2': 0})
    return sorted(out, key=lambda p: p['data'])
