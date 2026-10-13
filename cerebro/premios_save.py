# Mercado IA — autor: William (https://github.com/WilliamProgramadorBR)
"""PRÊMIOS INDIVIDUAIS do PES (Base de dados > Títulos individuais), lidos do save (11/10/2026, SOMENTE LEITURA).

Achado pelos votos da tela "Prêmio de melhor jogador do mundo 2034" (William 945, KAIO 588, Benzema 388):
  5 categorias seguidas, uma a cada 0x17D8 bytes (no save de 2034: 0xBEE290..):
    u32 categoria (0 mundo, 1 Europa, 2 América do Sul, 3 Ásia, 4 vazia) | u32 ANO (edição mais recente)
    3 registros de 16 B: u32 registro, u32 id, u32 código do clube (& 0x3FFF = índice do time), u32 VOTOS
    (a lista aparece duas vezes seguidas). Na categoria 0, 20 bytes antes do ano: u32 id do técnico premiado (+4 = 1).
  O save guarda só a edição mais recente de cada prêmio -> o histórico é acumulado no banco da imprensa.
Também: PRÊMIOS POR COMPETIÇÃO (blocos de 6268 B): cabeçalho ..., u32 código da competição, 1, u32 reg, u32 id
  (destaque); depois registros de 20 B: código do clube, (valor << 16) | ano, tipo, reg, id.
  tipo 1/2 = artilharia (valor = gols), 12 = assistências (valor), 13 = maior nota média (valor = nota x 10),
  0 e 3..11 e 14 = time ideal da competição (valor = nota x 10).
"""
import struct

PASSO = 0x17D8
CATEGORIAS = {0: 'mundo', 1: 'europa', 2: 'america_sul', 3: 'asia'}
NOMES = {'mundo': 'Melhor jogador do mundo', 'europa': 'Melhor jogador da Europa',
         'america_sul': 'Melhor jogador da América do Sul', 'asia': 'Melhor jogador da Ásia'}


def _registro(d, o):
    reg, pid, clube, votos = struct.unpack_from('<IIII', d, o)
    if reg in (0, 0xFFFF, 0xFFFFFFFF) or (clube & 0x3FFF) >= 730 or not 0 < votos < 100000:
        return None
    return {'reg': reg, 'pid': pid, 'clube': clube & 0x3FFF, 'votos': votos}


def _lista(d, o):
    out = []
    for k in range(3):
        r = _registro(d, o + 4 + 16 * k)
        if not r:
            break
        out.append(r)
    ok = len(out) >= 1 and all(out[i]['votos'] >= out[i + 1]['votos'] for i in range(len(out) - 1))
    return out if ok else None


def achar(d, ini=0xA00000, fim=0xE00000):
    """Posição do ANO da categoria 0 (mundo). Confere a sequência de categorias 0..3."""
    for o in range(ini, min(fim, len(d) - 5 * PASSO), 4):
        if struct.unpack_from('<I', d, o - 4)[0] != 0:
            continue
        ano = struct.unpack_from('<I', d, o)[0]
        if not 2015 <= ano <= 2060 or not _lista(d, o):
            continue
        if all(struct.unpack_from('<I', d, o + k * PASSO - 4)[0] == k for k in (1, 2, 3)):
            return o
    return None


def ler(d):
    """{'mundo': {'ano', 'top': [{reg, pid, clube, votos}], 'tecnico': id}, 'europa': ..., ...} (categorias com dados)."""
    o = achar(d)
    if o is None:
        return {}
    out = {}
    for k, nome in CATEGORIAS.items():
        p = o + k * PASSO
        ano = struct.unpack_from('<I', d, p)[0]
        top = _lista(d, p) if 2015 <= ano <= 2060 else None
        if top:
            out[nome] = {'ano': ano, 'top': top}
    if 'mundo' in out:
        tec = struct.unpack_from('<I', d, o - 16)[0]
        out['mundo']['tecnico'] = tec if tec not in (0, 0xFFFFFFFF) else None
    return out


# ---------------------------------------------------------------- Jogadores favoritos (diário de carreira)
# Escritório do técnico > Carreira do técnico > Jogadores favoritos (até 3 jogadores). Achado em 11/10/2026 pelas datas
# da tela do William (28/07/2029 empréstimo, 15/09/2029 registro, 02/12/2031 prêmio de melhor jogador do mundo):
#   cabeçalho: u32 reg, u32 id, u32 código do clube, 8 bytes ?, data do registro, data de chegada (u16 ano, u8 mês, u8 dia)
#   eventos de 0x38 bytes: +0 u32 tipo (1 competição, 2 prêmio, 3/4 outros), +4 0xFFFF, +8 u32 parâmetro,
#     +12 u32 temporada (índice), +20 data, +24 u16 competição (0xFFFF = nenhuma), +26 título, +27 melhor jogador,
#     +28 artilheiro (+32 u32 gols), +29 líder de assistências (+32 u32 assistências), +30 time do torneio.
#   tipo 2 com parâmetro 1 em 2/dez = PRÊMIO DE MELHOR JOGADOR DO MUNDO (William: 2031, 2032, 2033, 2034).
COMPS_FAVORITOS = {0x11: 'Premier League', 0x17: 'FA Cup', 0x01: 'FIFA Intercontinental Cup'}
EV = 0x38


def _evento(d, o, estrito=True):
    t, ff, par, temp = struct.unpack_from('<IIII', d, o)
    y, m, dd = struct.unpack_from('<HBB', d, o + 20)
    # +4 é 0xFFFF nos eventos comuns; no tipo 6 (11/10/2026: título da William em 30/05/2030) vem outro valor
    if (estrito and ff != 0xFFFF) or t > 10 or not (2015 <= y <= 2060 and 1 <= m <= 12 and 1 <= dd <= 31):
        return None
    comp = struct.unpack_from('<H', d, o + 24)[0]
    fl = d[o + 26:o + 31]
    val = struct.unpack_from('<I', d, o + 32)[0]
    e = {'tipo': t, 'param': par, 'data': (y, m, dd), 'comp': None if comp == 0xFFFF else comp}
    if t == 2 and e['comp'] is None:
        e['premio'] = 'melhor_do_mundo' if par == 1 else 'premio_continental'
    else:
        e.update({'titulo': fl[0] == 1, 'melhor': fl[1] == 1, 'artilheiro': val if fl[2] == 1 else None,
                  'assistencias': val if fl[3] == 1 else None, 'time_torneio': fl[4] == 1})
    return e


def favoritos(d, chaves, ini=0xF00000, fim=0x1200000):
    """[{'reg', 'pid', 'clube', 'eventos': [...]}] dos jogadores favoritos (diário de carreira)."""
    out, o = [], ini
    while o < min(fim, len(d) - EV):
        if not _evento(d, o):
            o += 4
            continue
        evs, p, falhas = [], o, 0
        while p < len(d) - EV and falhas < 2:   # passo fixo; um registro estranho no meio não encerra o diário
            e = _evento(d, p, estrito=False)
            if e:
                evs.append(e)
                falhas = 0
            else:
                falhas += 1
            p += EV
        if len(evs) >= 3:
            dono = None
            for b in range(o - 4, o - 0x80, -4):   # cabeçalho logo antes dos eventos
                k = struct.unpack_from('<II', d, b)
                if k in chaves:
                    dono = (k, struct.unpack_from('<I', d, b + 8)[0] & 0x3FFF)
                    break
            if dono:
                out.append({'reg': dono[0][0], 'pid': dono[0][1], 'clube': dono[1], 'eventos': evs})
        o = p + 4
    return out


def _reg20(d, o, chaves):
    """Registro de 20 B dos prêmios por competição e do Time do mês: u32 registro, u32 id, u32 código do clube,
    u32 (valor << 16) | ano, u32 tipo. 12/10/2026: a 1ª leitura começava 12 bytes antes (clube do jogador anterior)."""
    reg, pid, clube, va, tp = struct.unpack_from('<IIIII', d, o)
    if (reg, pid) not in chaves or not 2015 <= (va & 0xFFFF) <= 2060 or tp > 20 or (clube & 0x3FFF) >= 730:
        return None
    return {'tipo': tp, 'valor': va >> 16, 'ano': va & 0xFFFF, 'reg': reg, 'pid': pid, 'clube': clube & 0x3FFF}


def competicoes(d, chaves, ini=0xC80000, fim=0xF80000):
    """Prêmios de fim de temporada por competição: [{'comp', 'ano', 'itens': [{tipo, valor, reg, pid, clube}]}]
    (tipo 1/2 artilharia, 12 assistências, 13 maior nota média, os outros = time ideal). Cabeçalho: ..., u32 comp, u32 1."""
    out = []
    o = ini
    while o < min(fim, len(d) - 20):
        if not _reg20(d, o, chaves):
            o += 4
            continue
        ini_bloco, itens = o, []
        while o < len(d) - 20:
            x = _reg20(d, o, chaves)
            if not x:
                break
            itens.append(x)
            o += 20
        if len(itens) >= 5:
            comp, um = struct.unpack_from('<II', d, ini_bloco - 8)
            out.append({'pos': ini_bloco, 'comp': comp if um == 1 else None, 'ano': itens[0]['ano'], 'itens': itens})
        else:
            o = ini_bloco + 4
    return out


def time_do_mes(d, chaves, ini=0xBF0000, fim=0xC40000):
    """TIME DO MÊS do jogo (Base de dados > Títulos individuais > Time do mês), achado em 12/10/2026 pelo print do
    usuário (Premier League, maio de 2035): 11 registros de 20 B logo depois de u32 competição + u32 0x0C; no save do
    Man Utd fica em 0xC00190. valor = nota média do mês x 10. O jogo troca o time quando o mês fecha e NÃO grava qual
    é o mês (time_do_mes.py descobre comparando as notas com as súmulas)."""
    o = ini
    while o < min(fim, len(d) - 220):
        comp, doze = struct.unpack_from('<II', d, o - 8)
        if doze == 0x0C and comp < 0x400 and _reg20(d, o, chaves):
            js = [_reg20(d, o + 20 * k, chaves) for k in range(11)]
            if all(js):
                return {'pos': o, 'comp': comp, 'ano': js[0]['ano'], 'jogadores': js}
        o += 4
    return None
