"""Pré-treino das redes do duelo com o histórico de súmulas do save (12/10/2026).

python pretreinar_rede.py            -> treina com 80% dos jogos (em ordem de data), testa nos 20% finais contra a
                                        estatística (mesmo bolão do duelo) e depois treina com tudo e grava.
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


def teste(amostras, rede_, est):
    pe = pr = 0
    for x, y, _ in amostras:
        real = [int(y[0]), int(y[1])]
        pe += R.pontos(R.palpite(*est(x)), real)
        pr += R.pontos(R.palpite(*rede_.prever(x)), real)
    return pe, pr


def main():
    dec = max(glob.glob(os.path.join(HERE, '..', 'save_work', 'vestiario_*', 'dec', 'data.dat')), key=os.path.getmtime)
    # a temporada passada (o jogo apaga as súmulas na virada): cópia de fim de temporada guardada pela reunião
    antigos = [a for a in sys.argv[1:] if os.path.exists(a)] or [
        os.path.join(HERE, '..', 'save_work', 'vestiario_20261011_074657', 'dec', 'data.dat')]
    d = open(dec, 'rb').read()
    P = dados.load_players(V.SNAP)
    t0 = time.time()
    sim, usr, gols, vistos = [], [], [], set()
    for caminho in [dec] + [a for a in antigos if os.path.exists(a)]:
        dx = open(caminho, 'rb').read()
        rx = V.analisar(dx, V.SNAP)
        sx = SaveML.__new__(SaveML)
        sx.path, sx.d, sx.base = None, bytearray(dx), dx.index(b'ARSENAL\x00')
        a_sim, a_usr, b_ = D.amostras_historicas(rx, P, sx, d)   # planos originais pelo save atual
        for lst, dst in ((a_sim, sim), (a_usr, usr)):
            for am in lst:
                k = (am[2], tuple(round(v, 3) for v in am[0][:3]))
                if k not in vistos:
                    vistos.add(k)
                    dst.append(am)
        gols.append(b_)
    base = sum(gols) / len(gols)
    print(f'amostras: {len(sim)} jogos simulados, {len(usr)} jogos do usuário; média de gols por time {base:.2f} ({time.time() - t0:.0f} s)')
    e = D.estado()
    e['base_gols'] = round(base, 3)
    if usr:
        e['total_usuario'] = round(sum(y[0] + y[1] for _, y, _ in usr[-40:]) / len(usr[-40:]), 2)
    out = {}
    for arena, ams, est in (('simulados', sim, lambda x: [max(0.15, base + D.COEF * x[2] * 5), max(0.15, base - D.COEF * x[2] * 5)]),
                            ('usuario', usr, lambda x: [e['total_usuario'] / 2 + D.COEF * x[2] * 5, max(0.2, e['total_usuario'] / 2 - D.COEF * x[2] * 5)])):
        if len(ams) < 30:
            print(f'{arena}: poucos jogos ({len(ams)}), pulando')
            continue
        ams.sort(key=lambda a: a[2])
        corte = int(len(ams) * 0.8)
        treino, prova = ams[:corte], ams[corte:]
        t0 = time.time()
        rd = R.Rede(D.N_IN[arena], 10, 2, semente=7)
        ep = 12 if arena == 'simulados' else 60
        for k in range(ep):
            perda = rd.treinar([(x, y) for x, y, _ in treino], epocas=1, lr=0.01 if k < ep // 2 else 0.004, semente=k)
        pe, pr = teste(prova, rd, est)
        print(f'{arena}: teste em {len(prova)} jogos — estatística {pe} pts x rede {pr} pts (perda {perda:.3f}, {time.time() - t0:.0f} s)')
        out[arena] = {'teste_jogos': len(prova), 'estatistica': pe, 'rede': pr}
        rd = R.Rede(D.N_IN[arena], 10, 2, semente=7)   # agora com tudo
        for k in range(ep):
            rd.treinar([(x, y) for x, y, _ in ams], epocas=1, lr=0.01 if k < ep // 2 else 0.004, semente=k)
        rd.salvar(D.ARQ_REDE[arena], extra={'pretreino': out[arena], 'jogos': len(ams)})
        with open(D.ARQ_BUF[arena], 'w', encoding='utf-8') as f:
            json.dump([[x, y] for x, y, _ in ams[-4000:]], f)
    e['pretreino'] = out
    D.gravar(e)
    print('ok')


if __name__ == '__main__':
    main()
