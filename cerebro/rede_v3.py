# Mercado IA — autor: William (https://github.com/WilliamProgramadorBR)
"""REDE v3 DOS JOGOS DO USUÁRIO (19/10/2026): comitê de redes residuais sobre a estatística, mexendo só no SALDO.

Por que (estudo de 19/10, 90 jogos, teste andando no tempo nos últimos 45 — ver memória rede-v3-estudo): com ~90
jogos a rede comum (MLP de 28 entradas) DECORA — confiante demais, NLL 3,81 contra 3,23 da estatística — e mais
variáveis pioram. O que ganhou da estatística (bolão 57 x 49, vencedor 34 x 32, RPS 0,167 x 0,171):
  residual  a rede parte da previsão da estatística (λ_base) e aprende só a CORREÇÃO: λ_nós = b_nós·e^δ e
            λ_eles = b_eles·e^−δ — empurra o saldo, o total de gols continua o da estatística. Sem dado, δ = 0
            (a rede começa igual à estatística e só se afasta quando os jogos mostram motivo);
  pequena   4 neurônios tanh, δ = tanh limitado a ±1 (no máximo ~2,7x num lado), L2 forte (0,1), 60 épocas;
  comitê    5 redes com sementes diferentes; a previsão é a média — corta o "decorar";
  entradas  as 28 da v2 (ficha, força, mando, forma, plano do rival...) + 23 de jogador por jogador (velocidade e jogo
            aéreo x zagueiros, quem está quente, dependência do artilheiro, gols recentes, confronto direto...),
            padronizadas (média 0, desvio 1) com os dados de treino.
Treino: do zero, com todos os jogos guardados, a cada jogo pontuado. Roda num PROCESSO SEPARADO
(python rede_v3.py treinar) para não disputar o Python da Central com os cliques do usuário.
Python puro, sem numpy (o pacote da comunidade não leva).
"""
import json
import math
import os
import random
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ARQ = os.path.join(HERE, 'historico', 'rede_usuario_v3.json')
ARQ_BUF = os.path.join(HERE, 'historico', 'rede_usuario_v3_dados.json')
TRAVA_TREINO = os.path.join(HERE, 'historico', 'rede_usuario_v3.treinando')
SEMENTES = (1, 2, 3, 4, 5)
OCULTOS, L2, EPOCAS, LR, LIMITE = 4, 0.1, 60, 0.004, 1.0
MAX_AMOSTRAS = 800


class Residual:
    def __init__(self, n_in, semente=0):
        rnd = random.Random(semente)
        e1 = 1 / math.sqrt(n_in)
        self.W1 = [[rnd.uniform(-e1, e1) for _ in range(n_in)] for _ in range(OCULTOS)]
        self.b1 = [0.0] * OCULTOS
        self.w2 = [0.0] * OCULTOS
        self.b2 = 0.0

    def delta(self, z):
        h = [math.tanh(sum(w * v for w, v in zip(row, z)) + b) for row, b in zip(self.W1, self.b1)]
        return h, LIMITE * math.tanh(sum(w * hi for w, hi in zip(self.w2, h)) + self.b2)

    def treinar(self, ams, semente):
        """ams = [(z, base, y)]; perda de Poisson com λ = base·e^(±δ); devolve a perda média da última época."""
        rnd = random.Random(semente)
        perda = 0.0
        for _ in range(EPOCAS):
            ordem = list(ams)
            rnd.shuffle(ordem)
            perda = 0.0
            for z, base, y in ordem:
                h, dl = self.delta(z)
                lu, la = base[0] * math.exp(dl), base[1] * math.exp(-dl)
                perda += lu - y[0] * math.log(max(lu, 1e-6)) + la - y[1] * math.log(max(la, 1e-6))
                g = ((lu - y[0]) - (la - y[1])) * (1 - (dl / LIMITE) ** 2)
                for j in range(OCULTOS):
                    dh = g * self.w2[j] * (1 - h[j] * h[j])
                    self.w2[j] -= LR * (g * h[j] + L2 * self.w2[j])
                    row = self.W1[j]
                    for i in range(len(row)):
                        row[i] -= LR * (dh * z[i] + L2 * row[i])
                    self.b1[j] -= LR * dh
                self.b2 -= LR * g
        return perda / max(1, len(ams))

    def para_dict(self):
        return {'W1': self.W1, 'b1': self.b1, 'w2': self.w2, 'b2': self.b2}

    @classmethod
    def de_dict(cls, d):
        r = cls.__new__(cls)
        r.W1, r.b1, r.w2, r.b2 = d['W1'], d['b1'], d['w2'], d['b2']
        return r


class Comite:
    """Interface do duelo: prever(x, base), vistos, extra (perdas por treino, para o gráfico do Painel)."""
    def __init__(self, n_in):
        self.n_in = n_in
        self.mu, self.sd = [0.0] * n_in, [1.0] * n_in
        self.redes = []            # sem treino: δ = 0 (igual à estatística)
        self.vistos = 0
        self.extra = {}

    def z(self, x):
        # coluna sem variação nos jogos de treino (ex.: espírito/moral/condição, que os jogos antigos não têm) fica
        # NEUTRA: padronizar com desvio ~0 transformaria um valor real ao vivo num número gigante (rede saturada)
        return [0.0 if s < 1e-4 else (v - m) / s for v, m, s in zip(x, self.mu, self.sd)]

    def _prever_z(self, zz, base):
        if not self.redes:
            return list(base)
        ls = []
        for r in self.redes:
            _, dl = r.delta(zz)
            ls.append((base[0] * math.exp(dl), base[1] * math.exp(-dl)))
        return [sum(l[0] for l in ls) / len(ls), sum(l[1] for l in ls) / len(ls)]

    def prever(self, x, base):
        return self._prever_z(self.z(x), base)

    def saldo_sem(self, x, base, indices):
        """Saldo previsto com um grupo de entradas neutro (no valor médio): para o "por quê"."""
        zz = self.z(x)
        for i in indices:
            zz[i] = 0.0
        a, b = self._prever_z(zz, base)
        return a - b

    def treinar(self, amostras):
        """amostras = [{'c': entradas, 'base': [λ nós, λ eles] da estatística na hora do palpite, 'y': [gols nós, eles]}]"""
        ams = [a for a in amostras if len(a['c']) == self.n_in]
        if len(ams) < 12:
            return None
        n = len(ams)
        self.mu = [sum(a['c'][i] for a in ams) / n for i in range(self.n_in)]
        self.sd = [math.sqrt(sum((a["c"][i] - self.mu[i]) ** 2 for a in ams) / n) for i in range(self.n_in)]
        dados = [(self.z(a['c']), a['base'], a['y']) for a in ams]
        self.redes, perdas = [], []
        for sm in SEMENTES:
            r = Residual(self.n_in, sm)
            perdas.append(r.treinar(dados, sm))
            self.redes.append(r)
        self.vistos = n
        perda = sum(perdas) / len(perdas)
        self.extra['perdas'] = (self.extra.get('perdas') or [])[-299:] + [[n, round(perda, 4)]]
        return perda

    def salvar(self, arq=ARQ):
        os.makedirs(os.path.dirname(arq), exist_ok=True)
        tmp = arq + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump({'versao': 3, 'n_in': self.n_in, 'mu': self.mu, 'sd': self.sd, 'vistos': self.vistos,
                       'redes': [r.para_dict() for r in self.redes], 'extra': self.extra}, f)
        for _ in range(40):
            try:
                os.replace(tmp, arq)
                return
            except PermissionError:
                time.sleep(0.05)

    @classmethod
    def carregar(cls, arq=ARQ):
        try:
            with open(arq, encoding='utf-8') as f:
                d = json.load(f)
        except (OSError, ValueError):
            return None
        if d.get('versao') != 3:
            return None
        c = cls(d['n_in'])
        c.mu, c.sd, c.vistos, c.extra = d['mu'], d['sd'], d.get('vistos', 0), d.get('extra') or {}
        c.redes = [Residual.de_dict(r) for r in d['redes']]
        return c


# ---------------------------------------------------------------- buffer e treino em processo separado
def ler_buffer():
    try:
        with open(ARQ_BUF, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return []


def gravar_buffer(buf):
    os.makedirs(os.path.dirname(ARQ_BUF), exist_ok=True)
    tmp = ARQ_BUF + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(buf[-MAX_AMOSTRAS:], f)
    os.replace(tmp, ARQ_BUF)


def treinar_arquivo(n_in, log=print):
    """Treina do zero com o buffer e grava o modelo (mantém o histórico de perdas do modelo anterior)."""
    antigo = Comite.carregar()
    c = Comite(n_in)
    if antigo is not None:
        c.extra = antigo.extra
    t0 = time.time()
    perda = c.treinar(ler_buffer())
    if perda is None:
        log('rede v3: poucos jogos para treinar (mínimo 12)')
        return None
    c.salvar()
    log(f'rede v3: {c.vistos} jogos, perda {perda:.3f} ({time.time() - t0:.1f} s)')
    return perda


def treinar_em_fundo(n_in):
    """Dispara o treino num processo separado (uma vez por vez; a trava expira em 10 min)."""
    import subprocess
    try:
        if os.path.exists(TRAVA_TREINO) and time.time() - os.path.getmtime(TRAVA_TREINO) < 600:
            open(TRAVA_TREINO + '.de_novo', 'w').close()     # pede outra rodada quando a atual acabar
            return
    except OSError:
        pass
    subprocess.Popen([sys.executable, '-s', os.path.abspath(__file__), 'treinar', str(n_in)], cwd=HERE,
                     creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0) | getattr(subprocess, 'BELOW_NORMAL_PRIORITY_CLASS', 0),
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


if __name__ == '__main__' and len(sys.argv) >= 3 and sys.argv[1] == 'treinar':
    n_in = int(sys.argv[2])
    try:
        while True:
            open(TRAVA_TREINO, 'w').close()
            treinar_arquivo(n_in)
            if not os.path.exists(TRAVA_TREINO + '.de_novo'):
                break
            os.remove(TRAVA_TREINO + '.de_novo')
    finally:
        for f in (TRAVA_TREINO, TRAVA_TREINO + '.de_novo'):
            try:
                os.remove(f)
            except OSError:
                pass
