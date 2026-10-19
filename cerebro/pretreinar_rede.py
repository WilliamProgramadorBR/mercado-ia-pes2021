# Mercado IA — autor: William (https://github.com/WilliamProgramadorBR)
"""Pré-treino das redes do duelo com o histórico de súmulas do save (12/10/2026).

python pretreinar_rede.py            -> treina com 80% dos jogos (em ordem de data), testa nos 20% finais contra a
                                        estatística (mesmo bolão do duelo) e depois treina com tudo e grava.
python pretreinar_rede.py --so-usuario  só a arena do usuário (13/10/2026: v2 com a ficha do jogo; a estatística
                                        v2 também é ajustada aqui — regressão com os jogos do usuário).
O placar oficial do duelo começa do zero: isto só dá à rede o "estudo" do que já aconteceu.
"""
import glob
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import dados  # noqa: E402
import duelo as D  # noqa: E402
import rede as R  # noqa: E402
import vestiario as V  # noqa: E402
from save_ml import SaveML  # noqa: E402


def bases_andando(usr):
    """19/10/2026 (rede v3): λ da estatística de cada jogo usando só os jogos anteriores — o mesmo que acontece ao
    vivo (a rede aprende a corrigir a previsão que a estatística fez NA HORA)."""
    out = []
    for i, (_, y, _, xe) in enumerate(usr):
        ant = usr[:i] or usr[:1]
        co = D.ajustar_est([{'xe': a[3], 'saldo': a[1][0] - a[1][1]} for a in ant])
        tot = ant[0][1][0] + ant[0][1][1]
        for a in ant[1:]:
            tot = (1 - D.ALFA_TOTAL) * tot + D.ALFA_TOTAL * (a[1][0] + a[1][1])
        out.append(D.est_usr({'coef_usr': co, 'total_usuario': tot}, xe))
    return out


def treinar_usuario_v3(usr, out):
    """Comitê v3: teste nos 20% finais (bolão e RPS contra a estatística) e depois treino com tudo."""
    import rede_v3
    bases = bases_andando(usr)
    ams = [{'c': list(x), 'base': [round(b[0], 3), round(b[1], 3)], 'y': [float(y[0]), float(y[1])]}
           for (x, y, _, _), b in zip(usr, bases)]
    corte = int(len(ams) * 0.8)
    t0 = time.time()
    c = rede_v3.Comite(D.N_IN['usuario'])
    c.treinar(ams[:corte])
    pe = pr = 0
    re_ = rr = 0.0
    for a in ams[corte:]:
        real = [int(a['y'][0]), int(a['y'][1])]
        lr_ = c.prever(a['c'], a['base'])
        pe += R.pontos(R.palpite(*a['base']), real)
        pr += R.pontos(R.palpite(*lr_), real)
        re_ += D.calibracao([{'lam_est': a['base'], 'real': real}])['estatistica']['rps']
        rr += D.calibracao([{'lam_est': lr_, 'real': real}])['estatistica']['rps']
    n = len(ams) - corte
    print(f'usuario (rede v3): teste em {n} jogos — estatística {pe} pts (RPS {re_ / n:.4f}) x rede {pr} pts (RPS {rr / n:.4f}) '
          f'({time.time() - t0:.0f} s)')
    out['usuario'] = {'teste_jogos': n, 'estatistica': pe, 'rede': pr, 'versao': 3}
    rede_v3.gravar_buffer(ams)
    final = rede_v3.Comite(D.N_IN['usuario'])
    final.extra = {'pretreino': out['usuario']}
    final.treinar(ams)
    final.salvar()
    D._REDES.pop('usuario', None)


def teste(amostras, rede_, est):
    """est recebe a amostra inteira (x, y, data[, xe])."""
    pe = pr = 0
    for am in amostras:
        x, y = am[0], am[1]
        real = [int(y[0]), int(y[1])]
        pe += R.pontos(R.palpite(*est(am)), real)
        pr += R.pontos(R.palpite(*rede_.prever(x)), real)
    return pe, pr


def main():
    dec = max(glob.glob(os.path.join(HERE, '..', 'save_work', 'vestiario_*', 'dec', 'data.dat')), key=os.path.getmtime)
    # a temporada passada (o jogo apaga as súmulas na virada): cópia de fim de temporada guardada pela reunião
    antigos = [a for a in sys.argv[1:] if not a.startswith('--') and os.path.exists(a)] or [
        os.path.join(HERE, '..', 'save_work', 'vestiario_20261011_074657', 'dec', 'data.dat')]
    d = open(dec, 'rb').read()
    P = dados.load_players(V.SNAP)
    t0 = time.time()
    so_usuario = '--so-usuario' in sys.argv
    sim, usr, gols, vistos = [], [], [], set()
    for caminho in [dec] + [a for a in antigos if os.path.exists(a)]:
        dx = open(caminho, 'rb').read()
        rx = V.analisar(dx, V.SNAP)
        sx = SaveML.__new__(SaveML)
        sx.path, sx.d, sx.base = None, bytearray(dx), dx.index(b'ARSENAL\x00')
        a_sim, a_usr, b_ = D.amostras_historicas(rx, P, sx, d)   # planos originais pelo save atual
        for am in a_sim:
            k = (am[2], tuple(round(v, 3) for v in am[0][:3]))
            if k not in vistos:
                vistos.add(k)
                sim.append(am)
        for am in a_usr:   # v2: dicionários "crus" (ficha refeita da súmula)
            k = ('u', am['data'], tuple(am['y']))
            if k not in vistos:
                vistos.add(k)
                usr.append(am)
        gols.append(b_)
    base = sum(gols) / len(gols)
    print(f'amostras: {len(sim)} jogos simulados, {len(usr)} jogos do usuário; média de gols por time {base:.2f} ({time.time() - t0:.0f} s)')
    e = D.estado()
    if not so_usuario:
        e['base_gols'] = round(base, 3)
    usr, fim = D.encadear_usr(usr)
    out = dict(e.get('pretreino') or {})
    corte_u = int(len(usr) * 0.8)
    # estatística v2 do usuário: a do teste só conhece os 80% iniciais (como a rede)
    est_teste = dict(e, coef_usr=D.ajustar_est([{'xe': xe, 'saldo': y[0] - y[1]} for _, y, _, xe in usr[:corte_u]]),
                     total_usuario=sum(y[0] + y[1] for _, y, _, _ in usr[max(0, corte_u - 15):corte_u]) / max(1, min(15, corte_u)))
    arenas = []   # 19/10/2026: a arena do usuário usa o comitê v3 (treinar_usuario_v3), abaixo
    if len(usr) >= 30:
        treinar_usuario_v3(usr, out)
    if not so_usuario:
        arenas.insert(0, ('simulados', sim, lambda am: [max(0.15, base + D.COEF * am[0][2] * 5), max(0.15, base - D.COEF * am[0][2] * 5)]))
    for arena, ams, est in arenas:
        if len(ams) < 30:
            print(f'{arena}: poucos jogos ({len(ams)}), pulando')
            continue
        ams.sort(key=lambda a: a[2])
        corte = int(len(ams) * 0.8)
        treino, prova = ams[:corte], ams[corte:]
        t0 = time.time()
        rd = D.rede_nova(arena)
        ep = 12 if arena == 'simulados' else 60
        for k in range(ep):
            perda = rd.treinar([(am[0], am[1]) for am in treino], epocas=1, lr=0.01 if k < ep // 2 else 0.004, semente=k)
        pe, pr = teste(prova, rd, est)
        print(f'{arena}: teste em {len(prova)} jogos — estatística {pe} pts x rede {pr} pts (perda {perda:.3f}, {time.time() - t0:.0f} s)')
        out[arena] = {'teste_jogos': len(prova), 'estatistica': pe, 'rede': pr}
        rd = D.rede_nova(arena)   # agora com tudo
        for k in range(ep):
            rd.treinar([(am[0], am[1]) for am in ams], epocas=1, lr=0.01 if k < ep // 2 else 0.004, semente=k)
        rd.salvar(D.ARQ_REDE[arena], extra={'pretreino': out[arena], 'jogos': len(ams)})
        with open(D.ARQ_BUF[arena], 'w', encoding='utf-8') as f:
            json.dump([[am[0], am[1]] for am in ams[-4000:]], f)
        D._REDES.pop(arena, None)
    if usr:   # a estatística v2 com todos os jogos do usuário, a média de gols recente e o momento
        e['amostras_est'] = [{'xe': {k: round(v, 4) for k, v in xe.items()}, 'saldo': y[0] - y[1], 'extra': 0.0, 'data': list(dt_)}
                             for _, y, dt_, xe in usr][-400:]
        e['coef_usr'] = D.ajustar_est(e['amostras_est'])
        e.update(fim)
        print('estatística v2 (gols de saldo por unidade):', e['coef_usr'])
        print('média de gols por jogo:', e['total_usuario'], '| momento:', D.momento(e))
    e['pretreino'] = out
    D.gravar(e)
    print('ok')


if __name__ == '__main__':
    main()
