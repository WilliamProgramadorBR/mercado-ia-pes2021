"""REDE NEURAL PEQUENA EM PYTHON PURO (12/10/2026).

Pedido do usuário: uma rede neural que dispute com a estatística quem prevê melhor os jogos (sem tirar a estatística).
Escolhas para ficar LEVE (o usuário se preocupa com desempenho) e sem instalar nada (o pacote da comunidade não leva
numpy): uma camada escondida (tanh), duas saídas = gols esperados de cada lado (softplus), perda de Poisson (a
distribuição natural de gols), treino por descida de gradiente com Adam, pesos em JSON. ~200 parâmetros: treinar 10 mil
jogos leva segundos; prever um jogo leva microssegundos.
"""
import json
import math
import os
import random


def _softplus(x):
    return math.log1p(math.exp(-abs(x))) + max(x, 0.0)


def _sig(x):
    return 1.0 / (1.0 + math.exp(-x)) if x >= 0 else math.exp(x) / (1.0 + math.exp(x))


class Rede:
    def __init__(self, n_in, n_hid=10, n_out=2, semente=0):
        rnd = random.Random(semente)
        e1, e2 = 1 / math.sqrt(n_in), 1 / math.sqrt(n_hid)
        self.n_in, self.n_hid, self.n_out = n_in, n_hid, n_out
        self.W1 = [[rnd.uniform(-e1, e1) for _ in range(n_in)] for _ in range(n_hid)]
        self.b1 = [0.0] * n_hid
        self.W2 = [[rnd.uniform(-e2, e2) for _ in range(n_hid)] for _ in range(n_out)]
        self.b2 = [0.3] * n_out                 # softplus(0.3) ~ 0.85 gol: começo razoável
        self.t = 0
        self._m = self._zeros()
        self._v = self._zeros()
        self.vistos = 0                          # quantos jogos a rede já estudou

    # ---------------------------------------------------------------- utilidades
    def _zeros(self):
        return {'W1': [[0.0] * self.n_in for _ in range(self.n_hid)], 'b1': [0.0] * self.n_hid,
                'W2': [[0.0] * self.n_hid for _ in range(self.n_out)], 'b2': [0.0] * self.n_out}

    def prever(self, x):
        """Gols esperados [lado A, lado B]."""
        h = [math.tanh(sum(w * xi for w, xi in zip(row, x)) + b) for row, b in zip(self.W1, self.b1)]
        return [max(0.05, _softplus(sum(w * hi for w, hi in zip(row, h)) + b)) for row, b in zip(self.W2, self.b2)]

    def _grad(self, x, y):
        h = [math.tanh(sum(w * xi for w, xi in zip(row, x)) + b) for row, b in zip(self.W1, self.b1)]
        z = [sum(w * hi for w, hi in zip(row, h)) + b for row, b in zip(self.W2, self.b2)]
        lam = [max(1e-3, _softplus(zi)) for zi in z]
        # perda de Poisson: lam - y*log(lam); d/dz = (1 - y/lam) * sigmoid(z)
        dz = [(1 - yi / li) * _sig(zi) for yi, li, zi in zip(y, lam, z)]
        g = self._zeros()
        dh = [0.0] * self.n_hid
        for o in range(self.n_out):
            g['b2'][o] = dz[o]
            for j in range(self.n_hid):
                g['W2'][o][j] = dz[o] * h[j]
                dh[j] += dz[o] * self.W2[o][j]
        for j in range(self.n_hid):
            da = dh[j] * (1 - h[j] * h[j])
            g['b1'][j] = da
            for i in range(self.n_in):
                g['W1'][j][i] = da * x[i]
        perda = sum(li - yi * math.log(li) for yi, li in zip(y, lam))
        return g, perda

    def treinar(self, amostras, epocas=1, lr=0.01, lote=16, semente=0):
        """amostras = [(x, [gols_A, gols_B])]. Devolve a perda média da última época."""
        rnd = random.Random(semente)
        b1_, b2_, eps = 0.9, 0.999, 1e-8
        perda_media = 0.0
        for _ in range(epocas):
            ordem = list(amostras)
            rnd.shuffle(ordem)
            tot = 0.0
            for k in range(0, len(ordem), lote):
                bloco = ordem[k:k + lote]
                acc = self._zeros()
                for x, y in bloco:
                    g, perda = self._grad(x, y)
                    tot += perda
                    for nome in ('b1', 'b2'):
                        for i, v in enumerate(g[nome]):
                            acc[nome][i] += v / len(bloco)
                    for nome in ('W1', 'W2'):
                        for i, row in enumerate(g[nome]):
                            ar = acc[nome][i]
                            for j, v in enumerate(row):
                                ar[j] += v / len(bloco)
                self.t += 1
                c1, c2 = 1 - b1_ ** self.t, 1 - b2_ ** self.t
                for nome, P in (('W1', self.W1), ('W2', self.W2)):
                    for i, row in enumerate(P):
                        mr, vr, gr = self._m[nome][i], self._v[nome][i], acc[nome][i]
                        for j in range(len(row)):
                            mr[j] = b1_ * mr[j] + (1 - b1_) * gr[j]
                            vr[j] = b2_ * vr[j] + (1 - b2_) * gr[j] * gr[j]
                            row[j] -= lr * (mr[j] / c1) / (math.sqrt(vr[j] / c2) + eps)
                for nome, P in (('b1', self.b1), ('b2', self.b2)):
                    mr, vr, gr = self._m[nome], self._v[nome], acc[nome]
                    for j in range(len(P)):
                        mr[j] = b1_ * mr[j] + (1 - b1_) * gr[j]
                        vr[j] = b2_ * vr[j] + (1 - b2_) * gr[j] * gr[j]
                        P[j] -= lr * (mr[j] / c1) / (math.sqrt(vr[j] / c2) + eps)
            perda_media = tot / max(1, len(ordem))
        self.vistos += len(amostras)
        return perda_media

    # ---------------------------------------------------------------- arquivo
    def salvar(self, arq, extra=None):
        dados = {'n_in': self.n_in, 'n_hid': self.n_hid, 'n_out': self.n_out, 'W1': self.W1, 'b1': self.b1,
                 'W2': self.W2, 'b2': self.b2, 't': self.t, 'm': self._m, 'v': self._v, 'vistos': self.vistos,
                 'extra': extra or {}}
        tmp = arq + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(dados, f)
        os.replace(tmp, arq)

    @classmethod
    def carregar(cls, arq):
        try:
            with open(arq, encoding='utf-8') as f:
                d = json.load(f)
        except (OSError, ValueError):
            return None
        r = cls(d['n_in'], d['n_hid'], d['n_out'])
        r.W1, r.b1, r.W2, r.b2, r.t = d['W1'], d['b1'], d['W2'], d['b2'], d['t']
        r._m, r._v, r.vistos = d['m'], d['v'], d.get('vistos', 0)
        r.extra = d.get('extra') or {}
        return r


# ---------------------------------------------------------------- de gols esperados para um palpite de placar
def _poisson(lam, k):
    return math.exp(-lam) * lam ** k / math.factorial(k)


def palpite(la, lb, maximo=6):
    """Placar do bolão a partir dos gols esperados: o resultado (V/E/D) mais provável e, dentro dele, o placar mais
    provável. Mesma regra para a estatística e para a rede: a diferença está só nos gols esperados."""
    pa = [_poisson(la, k) for k in range(maximo + 1)]
    pb = [_poisson(lb, k) for k in range(maximo + 1)]
    grupos = {'A': [], 'E': [], 'B': []}
    for i in range(maximo + 1):
        for j in range(maximo + 1):
            grupos['A' if i > j else 'B' if j > i else 'E'].append((pa[i] * pb[j], i, j))
    res = max(grupos, key=lambda g: sum(p for p, _, _ in grupos[g]))
    _, i, j = max(grupos[res])
    return [i, j]


def pontos(prev, real):
    """Bolão: placar exato 3, saldo certo 2, vencedor/empate certo 1, errou 0."""
    if list(prev) == list(real):
        return 3
    sp, sr = prev[0] - prev[1], real[0] - real[1]
    if sp == sr:
        return 2
    if (sp > 0) == (sr > 0) and (sp < 0) == (sr < 0):
        return 1
    return 0
