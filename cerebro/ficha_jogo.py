# Mercado IA — autor: William (https://github.com/WilliamProgramadorBR)
"""FICHA DO JOGO (13/10/2026): o estado físico e de elenco dos dois times antes de uma partida contra o usuário.

Pedido do usuário: "vamos dar mais dados" às IAs — cansaço, espírito de equipe, condição física, desfalques — porque
"tenho jogadores que estão no limite e não tenho quem substituir". A análise dos jogos de 2035/36 mostrou que o
cansaço é o sinal mais forte: com 4+ titulares carregando 250+ minutos em 14 dias o United sofreu 2,0 gols por jogo;
com o elenco descansado, 0,83.

Para cada lado:
  xi           nota média dos 11 que devem entrar (usuário: a escalação dele, bloco 730; clube da IA: a que o técnico
               da IA escreveu para a data, senão a gravada no save, senão o melhor XI pelas notas)
  cond         condição física média desse XI (registro de 156 B do save, +120 bits 0-6) e `baixos` (quantos < 75)
  carga        minutos médios desse XI nos 14 dias anteriores (súmulas) e `pesados` (quantos com 250+ minutos)
  descanso     dias desde o último jogo do time; `j7` = jogos nos 7 dias anteriores
  desfalques   quantos dos 14 melhores do elenco estão lesionados (+116 do registro)
Do usuário, também o espírito de equipe (save 0xB629BC, ver dificuldade.py) e a moral média do vestiário.

A condição de cada jogo NÃO fica guardada no save (só a do momento): por isso a ficha é gravada junto com o palpite
(duelo.py) e com o registro da IA adversária — o histórico que faltava para as IAs aprenderem. Para os jogos antigos
(pré-treino) dá para refazer da súmula só a carga, o descanso e o XI (`lado_sumula`). Só leitura.
"""
import datetime as dt
import json
import os
import zlib

PESADO = 250        # minutos em 14 dias que deixam um titular "no limite"
BAIXA = 75          # condição física abaixo disso conta como jogador cansado
HERE = os.path.dirname(os.path.abspath(__file__))
_MEMO = {}


# ---------------------------------------------------------------- leitura do save
def _registros(d):
    """{(registro, id): (condição, lesão)} de todos os jogadores da carreira (memo pelo conteúdo do save)."""
    chave = (len(d), zlib.crc32(d[-4_000_000:]))
    if _MEMO.get('regs_chave') != chave:
        import jogadores_save as JS
        out = {}
        for k, r in JS.registros(JS.blob(d)).items():
            c = JS.campos(r)
            out[k] = (c['condicao'], c['lesao'])
        _MEMO.update(regs_chave=chave, regs=out)
    return _MEMO['regs']


def _nota(P, k):
    import encaixe
    f = P.get(tuple(k)) if P else None
    return encaixe.rating(f, f.pos) if f else None


def xi_usuario(d, s, ti):
    """Chaves (registro, id) dos 11 da escalação do usuário (bloco 730: a ordem exata da formação dele)."""
    import tatica_save as T
    sq = s.squad(ti)
    o = T.BASE + 730 * T.TAM
    return [tuple(sq[i]) for i in d[o:o + 11] if i != 0xFF and i < len(sq)]


def xi_clube(d, s, ti, data, P):
    """Os 11 do clube da IA: a escalação que o técnico da IA escreveu para esta data, senão a gravada no save, senão
    o melhor XI pelas notas."""
    import tatica_save as T
    sq = [tuple(k) for k in s.squad(ti)]
    try:
        with open(os.path.join(HERE, 'historico', 'escalacao_ia.json'), encoding='utf-8') as f:
            hist = (json.load(f).get('titulares') or {}).get(str(ti)) or []
        reg = next((h for h in reversed(hist) if h['data'] == str(dt.date(*data[:3]))), None)
        if reg:
            por_pid = {k[1]: k for k in sq}
            xs = [por_pid[p] for p in reg['pids'] if p in por_pid]
            if len(xs) >= 9:
                return xs
    except (OSError, ValueError, KeyError, TypeError):
        pass
    xs = [sq[i] for i in T.titulares(d, ti) if i < len(sq)]
    if len(xs) >= 9:
        return xs
    return sorted(sq, key=lambda k: -(_nota(P, k) or 0))[:11]


# ---------------------------------------------------------------- carga pelas súmulas
class Cargas:
    """Minutos por jogador e datas de jogo de cada time, a partir das súmulas (ordem cronológica)."""
    def __init__(self, todas):
        self.por_time = {}
        for p in sorted(todas, key=lambda p: tuple(p['data'])):
            for t, ln in ((p['time1'], p['linhas1']), (p['time2'], p['linhas2'])):
                mins = {(x['reg'], x['pid']): x['minutos'] for x in ln if x['minutos'] > 0}
                self.por_time.setdefault(t, []).append((dt.date(*p['data'][:3]), mins))

    def lado(self, ti, data, xi):
        """carga (minutos médios do XI em 14 dias), pesados, descanso (dias), j7."""
        dia = dt.date(*data[:3])
        antes = [(dd, m) for dd, m in self.por_time.get(ti, []) if dd < dia]
        j14 = [m for dd, m in antes if (dia - dd).days <= 14]
        mins = [sum(m.get(tuple(k), 0) for m in j14) for k in xi]
        return {'carga': round(sum(mins) / max(1, len(mins))), 'pesados': sum(1 for x in mins if x >= PESADO),
                'descanso': (dia - antes[-1][0]).days if antes else None,
                'j7': sum(1 for dd, _ in antes if (dia - dd).days <= 7)}


def _cargas(todas):
    chave = (id(todas), len(todas))
    if _MEMO.get('cargas_chave') != chave:
        _MEMO.update(cargas_chave=chave, cargas=Cargas(todas))
    return _MEMO['cargas']


# ---------------------------------------------------------------- a ficha
def _lado(d, s, ti, xi, data, P, cargas):
    regs = _registros(d)
    notas = [n for n in (_nota(P, k) for k in xi) if n is not None]
    conds = [regs[tuple(k)][0] for k in xi if tuple(k) in regs]
    top14 = sorted((tuple(k) for k in s.squad(ti)), key=lambda k: -(_nota(P, k) or 0))[:14]
    lado = {'xi': round(sum(notas) / len(notas), 1) if notas else None, 'n_xi': len(xi),
            'cond': round(sum(conds) / len(conds), 1) if conds else None,
            'baixos': sum(1 for c in conds if c < BAIXA) if conds else None,
            'desfalques': sum(1 for k in top14 if regs.get(k, (100, 0))[1] > 0)}
    lado.update(cargas.lado(ti, data, xi))
    return lado


def montar(d, s, user_ti, adv_ti, data, P, dados=None, todas=None):
    """Ficha do jogo do usuário contra `adv_ti` na data `data` (save da última reunião `d`)."""
    import partidas_save as ps
    todas = todas if todas is not None else ps.todas(d, *ps.FAIXA)
    cargas = _cargas(todas)
    ficha = {'data': list(data[:3]),
             'nos': _lado(d, s, user_ti, xi_usuario(d, s, user_ti), data, P, cargas),
             'adv': _lado(d, s, adv_ti, xi_clube(d, s, adv_ti, data, P), data, P, cargas)}
    try:
        import dificuldade
        esp = d[dificuldade.ESPIRITO]
        ficha['espirito'] = esp if esp <= 100 else None
    except Exception:  # noqa: BLE001
        ficha['espirito'] = None
    js = (dados or {}).get('jogadores') or []
    mor = [j['moral'] for j in js if j.get('moral') is not None]
    ficha['moral'] = round(sum(mor) / len(mor)) if mor else None
    return ficha


def lado_sumula(cargas, ti, linhas, data, P):
    """O que dá para refazer de um jogo antigo: XI (os 11 com mais minutos), carga e descanso. Sem condição/lesão."""
    xi = [(x['reg'], x['pid']) for x in sorted((x for x in linhas if x['minutos'] > 0), key=lambda x: -x['minutos'])[:11]]
    notas = [n for n in (_nota(P, k) for k in xi) if n is not None]
    lado = {'xi': round(sum(notas) / len(notas), 1) if notas else None, 'n_xi': len(xi),
            'cond': None, 'baixos': None, 'desfalques': None}
    lado.update(cargas.lado(ti, data, xi))
    return lado


# ---------------------------------------------------------------- leitura humana
def fisico(ficha):
    """Quem chega no limite: {'nos': motivo ou None, 'adv': motivo ou None}."""
    out = {}
    for lado in ('nos', 'adv'):
        f = (ficha or {}).get(lado) or {}
        mot = []
        if (f.get('pesados') or 0) >= 4:
            mot.append(f'{f["pesados"]} titulares com {PESADO}+ minutos em 14 dias')
        lim = 82 if lado == 'nos' else 85
        if f.get('cond') is not None and f['cond'] < lim:
            mot.append(f'condição média do XI {f["cond"]:.0f}')
        if (f.get('baixos') or 0) >= 3:
            mot.append(f'{f["baixos"]} titulares abaixo de {BAIXA}')
        out[lado] = ', '.join(mot) or None
    return out


def texto(ficha, nome_nos='seu time', nome_adv='adversário'):
    """Uma linha por lado, para o Painel e os registros."""
    def lin(nome, f):
        if not f:
            return f'{nome}: sem dados'
        partes = [f'XI {f["xi"]}' if f.get('xi') else None,
                  f'condição {f["cond"]:.0f}' + (f' ({f["baixos"]} abaixo de {BAIXA})' if f.get('baixos') else '') if f.get('cond') is not None else None,
                  f'carga 14 dias {f["carga"]} min' + (f' ({f["pesados"]} no limite)' if f.get('pesados') else ''),
                  f'descanso {f["descanso"]} dias' if f.get('descanso') is not None else None,
                  f'{f["desfalques"]} desfalque(s)' if f.get('desfalques') else None]
        return f'{nome}: ' + ' · '.join(p for p in partes if p)
    out = [lin(nome_nos, (ficha or {}).get('nos')), lin(nome_adv, (ficha or {}).get('adv'))]
    extra = [f'espírito de equipe {ficha["espirito"]}' if (ficha or {}).get('espirito') is not None else None,
             f'moral média {ficha["moral"]}' if (ficha or {}).get('moral') is not None else None]
    if any(extra):
        out[0] += ' · ' + ' · '.join(x for x in extra if x)
    return out
