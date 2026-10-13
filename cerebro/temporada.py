# Mercado IA — autor: William (https://github.com/WilliamProgramadorBR)
"""CALENDÁRIO E LIGA DE QUALQUER CARREIRA (12/10/2026).

Antes, várias partes supunham a temporada europeia (julho a junho) e descobriam "a liga" pela competição mais jogada
do clube. Simulando 5 carreiras (Man Utd, Atlético de Madrid, Wolverhampton, Mirassol, Flamengo) isso falhava:
  - Brasileirão (janeiro a dezembro) virava "2026/27" contado de julho;
  - na pré-temporada, sem súmula de liga, a "liga" virava a Community Shield.
Agora, para qualquer carreira:
  liga()      a competição de pontos corridos do clube: a que tem mais times (>= 10) e mais jogos no mundo, contando os
              jogos já disputados e os marcados (agenda)
  inicio()    o começo da temporada = o mês da 1ª rodada mais recente dessa liga (até 330 dias atrás); sem isso, janeiro
              para ligas de calendário anual e julho para as outras
  rotulo()    '2027' (calendário anual) ou '2026/27' (europeu); chave() = '2027' ou '2026-27'
definir(r) guarda o resultado da reunião atual; destaques/historia/rodada_mes/midia_liga/Bola na Mesa usam o mesmo.
"""
import collections
import datetime as dt

NAO_LIGA = set(range(100, 111)) | set(range(34, 47)) | {56}   # amistosos/pré-temporada e torneios de seleções
ANUAIS = {0x1D, 0xA3, 0x1F, 8, 9, 0x0A, 30, 52, 55, 59, 67, 68}   # Brasil, Libertadores, Argentina, Japão, Chile

ATUAL = {'liga': None, 'ini': None, 'hoje': None}


def _d(a, b):
    return (dt.date(*a) - dt.date(*b)).days


def liga(todas, ti, agenda=()):
    """Código da liga do clube, ou None."""
    jogos = list(todas or []) + list(agenda or [])
    meus = {p['comp'] for p in jogos if ti in (p['time1'], p['time2']) and p['comp'] not in NAO_LIGA}
    if not meus:
        return None
    times, n = collections.defaultdict(set), collections.Counter()
    for p in jogos:
        if p['comp'] in meus:
            times[p['comp']].update((p['time1'], p['time2']))
            n[p['comp']] += 1
    cands = [c for c in meus if len(times[c]) >= 10]
    if not cands:
        return None
    return max(cands, key=lambda c: (n[c], len(times[c])))


def inicio(todas, comp, hoje):
    """Começo da temporada da liga `comp` em `hoje`."""
    if comp is not None:
        r1 = [tuple(p['data']) for p in todas or [] if p['comp'] == comp and p.get('rodada') == 1 and tuple(p['data']) <= tuple(hoje)]
        if r1:
            ult = max(r1)
            if _d(hoje, ult) <= 330:
                return (ult[0], 1, 1) if ult[1] <= 4 else (ult[0], ult[1], 1)
    if comp in ANUAIS:
        return (hoje[0], 1, 1)
    return (hoje[0] if hoje[1] >= 7 else hoje[0] - 1, 7, 1)


def anual(ini):
    return ini[1] <= 4   # temporadas que começam entre janeiro e abril levam o nome de um ano só


def rotulo(ini):
    return str(ini[0]) if anual(ini) else f'{ini[0]}/{str(ini[0] + 1)[2:]}'


def chave(ini):
    return str(ini[0]) if anual(ini) else f'{ini[0]}-{str(ini[0] + 1)[2:]}'


def anterior(ini):
    return (ini[0] - 1, ini[1], 1)


def definir(r):
    """Calcula e guarda a liga e o começo da temporada da reunião (r = vestiario.analisar)."""
    hoje = tuple(r['hoje'])
    c = liga(r.get('todas_partidas') or [], r['ti'], r.get('agenda') or [])
    ATUAL.update(liga=c, ini=inicio(r.get('todas_partidas') or [], c, hoje), hoje=hoje)
    return ATUAL


def ini_de(hoje):
    """O começo da temporada já definido para esta data, ou a regra europeia como reserva."""
    if ATUAL['ini'] and ATUAL['hoje'] and abs(_d(tuple(hoje), ATUAL['hoje'])) <= 45:
        return ATUAL['ini']
    return (hoje[0] if hoje[1] >= 7 else hoje[0] - 1, 7, 1)
