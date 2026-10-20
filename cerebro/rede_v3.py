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
Treino: do zero, com todos os jogos guardados, a cada jogo pontuado.
20/10/2026 — para durar mil jogos: (1) PESO POR RECÊNCIA: cada jogo pesa recencia^idade (normalizado para média 1),
porque o elenco e o próprio usuário mudam com as temporadas; (2) REAJUSTE AUTOMÁTICO: a cada 100 jogos novos, um
teste andando no tempo escolhe o tamanho (neurônios), a regularização (L2) e a recência numa grade — e só troca se a
nova configuração ganhar da atual com margem (NLL) sem piorar o RPS. A configuração fica em rede_usuario_v3_config.json. Roda num PROCESSO SEPARADO
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
ARQ_CFG = os.path.join(HERE, 'historico', 'rede_usuario_v3_config.json')
SEMENTES = (1, 2, 3, 4, 5)
EPOCAS, LR, LIMITE = 60, 0.004, 1.0
CFG_PADRAO = {'ocultos': 4, 'l2': 0.1, 'recencia': 1.0}   # o campeão do estudo de 19/10 (sem recência)
GRADE = [{'ocultos': o, 'l2': l, 'recencia': r} for o in (4, 8) for l in (0.1, 0.05) for r in (1.0, 0.995, 0.98)]
AJUSTE_A_CADA, AJUSTE_MIN_JOGOS = 100, 60
MARGEM_NLL = 0.01
MAX_AMOSTRAS = 800
# 20/10/2026: entrada que só ganhou dado real nos últimos jogos (moral, espírito, condição: os jogos antigos não têm)
# tem desvio quase zero e virava z de 4 a 7 — o "vestiário" empurrou o Nottingham para 4 x 0. Ela só conta com
# MIN_INFO jogos fora do valor mais comum; e nenhuma entrada passa de ±Z_MAX desvios.
MIN_INFO, Z_MAX = 15, 3.0


class Residual:
    def __init__(self, n_in, semente=0, ocultos=4):
        rnd = random.Random(semente)
        e1 = 1 / math.sqrt(n_in)
        self.W1 = [[rnd.uniform(-e1, e1) for _ in range(n_in)] for _ in range(ocultos)]
        self.b1 = [0.0] * ocultos
        self.w2 = [0.0] * ocultos
        self.b2 = 0.0

    def delta(self, z):
        h = [math.tanh(sum(w * v for w, v in zip(row, z)) + b) for row, b in zip(self.W1, self.b1)]
        return h, LIMITE * math.tanh(sum(w * hi for w, hi in zip(self.w2, h)) + self.b2)

    def treinar(self, ams, semente, l2=0.1):
        """ams = [(z, base, y, peso)]; perda de Poisson com λ = base·e^(±δ), cada jogo com o seu peso (recência);
        devolve a perda média da última época."""
        rnd = random.Random(semente)
        perda = 0.0
        for _ in range(EPOCAS):
            ordem = list(ams)
            rnd.shuffle(ordem)
            perda = 0.0
            for z, base, y, w in ordem:
                h, dl = self.delta(z)
                lu, la = base[0] * math.exp(dl), base[1] * math.exp(-dl)
                perda += w * (lu - y[0] * math.log(max(lu, 1e-6)) + la - y[1] * math.log(max(la, 1e-6)))
                g = w * ((lu - y[0]) - (la - y[1])) * (1 - (dl / LIMITE) ** 2)
                for j in range(len(self.w2)):
                    dh = g * self.w2[j] * (1 - h[j] * h[j])
                    self.w2[j] -= LR * (g * h[j] + l2 * self.w2[j])
                    row = self.W1[j]
                    for i in range(len(row)):
                        row[i] -= LR * (dh * z[i] + l2 * row[i])
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


def _informativos(col):
    """Quantos jogos têm a coluna FORA do valor mais comum (o padrão dos jogos sem esse dado)."""
    from collections import Counter
    vals = [round(v, 6) for v in col]
    return len(vals) - Counter(vals).most_common(1)[0][1]


class Comite:
    """Interface do duelo: prever(x, base), vistos, extra (perdas por treino, para o gráfico do Painel)."""
    def __init__(self, n_in, cfg=None):
        self.n_in = n_in
        self.cfg = dict(CFG_PADRAO, **(cfg or {}))
        self.mu, self.sd = [0.0] * n_in, [1.0] * n_in
        self.redes = []            # sem treino: δ = 0 (igual à estatística)
        self.vistos = 0
        self.extra = {}

    def z(self, x):
        # coluna sem variação nos jogos de treino (ex.: espírito/moral/condição, que os jogos antigos não têm) fica
        # NEUTRA: padronizar com desvio ~0 transformaria um valor real ao vivo num número gigante (rede saturada)
        return [0.0 if s < 1e-4 else max(-Z_MAX, min(Z_MAX, (v - m) / s)) for v, m, s in zip(x, self.mu, self.sd)]

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
        for i in range(self.n_in):   # pouco dado real na coluna: fica neutra (sd 0) até juntar MIN_INFO jogos
            if self.sd[i] >= 1e-4 and _informativos([a['c'][i] for a in ams]) < MIN_INFO:
                self.sd[i] = 0.0
        rec = self.cfg['recencia']   # o buffer está em ordem cronológica: o último é o jogo mais novo
        pesos = [rec ** (n - 1 - i) for i in range(n)]
        mp = sum(pesos) / n
        dados = [(self.z(a['c']), a['base'], a['y'], w / mp) for a, w in zip(ams, pesos)]
        self.redes, perdas = [], []
        for sm in SEMENTES:
            r = Residual(self.n_in, sm, self.cfg['ocultos'])
            perdas.append(r.treinar(dados, sm, self.cfg['l2']))
            self.redes.append(r)
        self.vistos = n
        perda = sum(perdas) / len(perdas)
        self.extra['perdas'] = (self.extra.get('perdas') or [])[-299:] + [[n, round(perda, 4)]]
        return perda

    def salvar(self, arq=ARQ):
        os.makedirs(os.path.dirname(arq), exist_ok=True)
        tmp = arq + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump({'versao': 3, 'n_in': self.n_in, 'cfg': self.cfg, 'mu': self.mu, 'sd': self.sd, 'vistos': self.vistos,
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
        c = cls(d['n_in'], d.get('cfg'))
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


def ler_cfg():
    try:
        with open(ARQ_CFG, encoding='utf-8') as f:
            return dict(CFG_PADRAO, **(json.load(f).get('cfg') or {}))
    except (OSError, ValueError):
        return dict(CFG_PADRAO)


def _rps(lam, y, m=10):
    pa = [math.exp(-lam[0]) * lam[0] ** k / math.factorial(k) for k in range(m + 1)]
    pb = [math.exp(-lam[1]) * lam[1] ** k / math.factorial(k) for k in range(m + 1)]
    v = sum(pa[i] * pb[j] for i in range(m + 1) for j in range(m + 1) if i > j)
    e = sum(pa[i] * pb[i] for i in range(m + 1))
    o = [1.0 if y[0] > y[1] else 0.0, 1.0 if y[0] == y[1] else 0.0]
    c1, c2 = v - o[0], v + e - o[0] - o[1]
    return (c1 * c1 + c2 * c2) / 2


def testar(buf, n_in, cfg, n_teste, passo=1):
    """Teste andando no tempo: para cada jogo dos n_teste finais, treina só com os ANTERIORES e prevê.
    (passo > 1: re-treina a cada `passo` jogos — para buffers grandes.) Devolve {'nll', 'rps', 'jogos'}."""
    n = len(buf)
    nll = rps = 0.0
    k = 0
    for i in range(n - n_teste, n, passo):
        c = Comite(n_in, cfg)
        if c.treinar(buf[:i]) is None:
            continue
        for a in buf[i:min(n, i + passo)]:
            lam = [max(0.05, v) for v in c.prever(a['c'], a['base'])]
            y = [int(a['y'][0]), int(a['y'][1])]
            nll += sum(l - yi * math.log(l) + math.lgamma(yi + 1) for l, yi in zip(lam, y))
            rps += _rps(lam, y)
            k += 1
    return {'nll': round(nll / k, 4), 'rps': round(rps / k, 4), 'jogos': k} if k else None


def ajustar(n_in, log=print, forcar=False):
    """Reajuste automático: testa a GRADE andando no tempo e troca a configuração só se a melhor ganhar da atual por
    MARGEM_NLL sem piorar o RPS. Grava o resultado (com a tabela) em ARQ_CFG. Devolve a configuração em uso."""
    buf = [a for a in ler_buffer() if len(a['c']) == n_in]
    try:
        with open(ARQ_CFG, encoding='utf-8') as f:
            reg = json.load(f)
    except (OSError, ValueError):
        reg = {}
    atual = dict(CFG_PADRAO, **(reg.get('cfg') or {}))
    n = len(buf)
    if n < AJUSTE_MIN_JOGOS or (not forcar and n - reg.get('vistos_ajuste', 0) < AJUSTE_A_CADA and 'vistos_ajuste' in reg):
        return atual
    n_teste = min(60, max(20, n // 4))
    passo = 1 if n <= 200 else 5
    t0 = time.time()
    tabela = []
    for cfg in GRADE + ([] if atual in GRADE else [atual]):
        r = testar(buf, n_in, cfg, n_teste, passo)
        if r:
            tabela.append({'cfg': cfg, **r})
            log(f'rede v3 ajuste: {cfg} -> NLL {r["nll"]:.4f} RPS {r["rps"]:.4f}')
    base = next((t for t in tabela if t['cfg'] == atual), None)
    cands = [t for t in tabela if base is None or (t['rps'] <= base['rps'] and t['nll'] <= base['nll'] - MARGEM_NLL)]
    melhor = min(cands, key=lambda t: t['nll']) if cands else None
    novo = melhor['cfg'] if melhor else atual
    reg = {'cfg': novo, 'vistos_ajuste': n, 'quando': time.strftime('%Y-%m-%d %H:%M'), 'teste_jogos': n_teste,
           'atual_antes': base, 'escolhida': melhor or base, 'trocou': novo != atual, 'tabela': tabela,
           'segundos': round(time.time() - t0)}
    os.makedirs(os.path.dirname(ARQ_CFG), exist_ok=True)
    with open(ARQ_CFG + '.tmp', 'w', encoding='utf-8') as f:
        json.dump(reg, f, ensure_ascii=False, indent=1)
    os.replace(ARQ_CFG + '.tmp', ARQ_CFG)
    log(f'rede v3 ajuste ({n} jogos, teste nos {n_teste} finais, {reg["segundos"]} s): '
        + (f'TROCOU {atual} -> {novo}' if novo != atual else f'mantém {atual}'))
    return novo


def treinar_arquivo(n_in, log=print):
    """Treina do zero com o buffer e grava o modelo (mantém o histórico de perdas do modelo anterior)."""
    antigo = Comite.carregar()
    c = Comite(n_in, ler_cfg())
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


if __name__ == '__main__' and len(sys.argv) >= 3 and sys.argv[1] == 'ajustar':   # manual: python rede_v3.py ajustar 51
    if ajustar(int(sys.argv[2]), forcar=True) is not None:
        treinar_arquivo(int(sys.argv[2]))

if __name__ == '__main__' and len(sys.argv) >= 3 and sys.argv[1] == 'treinar':
    n_in = int(sys.argv[2])
    try:
        while True:
            open(TRAVA_TREINO, 'w').close()
            treinar_arquivo(n_in)
            try:   # a cada AJUSTE_A_CADA jogos novos: reajuste automático (e re-treino se a configuração mudou)
                antes = ler_cfg()
                if ajustar(n_in) != antes:
                    treinar_arquivo(n_in)
            except Exception as e:  # noqa: BLE001
                print('rede v3: ajuste falhou:', e)
            if not os.path.exists(TRAVA_TREINO + '.de_novo'):
                break
            os.remove(TRAVA_TREINO + '.de_novo')
    finally:
        for f in (TRAVA_TREINO, TRAVA_TREINO + '.de_novo'):
            try:
                os.remove(f)
            except OSError:
                pass
