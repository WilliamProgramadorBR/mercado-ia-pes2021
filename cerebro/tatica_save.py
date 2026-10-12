"""PLANO DE JOGO dos clubes no save da ML (12/10/2026, mapeado com o usuário: um ajuste por save + prints).

Blocos de 600 B a partir de 0x133C50 (731 blocos). O u16 em +56 do bloco é o ÍNDICE DO TIME (o bloco costuma ser
idx-1; o técnico do usuário usa os blocos 729/730 e as edições dele caem no 729). +64 = nome do técnico.
Cada bloco tem 3 planos de jogo (+120, +280, +440); em cada plano, depois da formação (3 x 33 B):
  +99  estilo ofensivo     0 contra-ataque | 1 posse de bola            (confirmado)
  +100 saída de bola       0 passe longo   | 1 passe curto              (confirmado)
  +101 área de ataque      0 ampla         | 1 centro                   (bate com o print)
  +102 posicionamento      0 manter        | 1 flexível                 (bate com o print)
  +103 estilo defensivo    0 pressão na frente | 1 defesa total         (bate com o print)
  +104 área de contenção   0 centro        | 1 ampla                    (bate com o print)
  +105 pressão             0 agressiva     | 1 tradicional              (confirmado)
  +140 amplitude de apoio (provável), +142 LINHA DEFENSIVA 1-10, +143 COMPACTAÇÃO 1-10 (confirmados)
INSTRUÇÕES AVANÇADAS (mapeadas uma por save em 12/10/2026), no plano A: 4 vagas de 8 B em +228/+236 (ataque) e
+244/+252 (defesa) = u32 código + u32 alvo (0 = nenhum). Alvo = posição no elenco (SaveML.squad) do PRÓPRIO time,
exceto na marcação (14), em que é a posição no elenco do ADVERSÁRIO.
"""
INSTRUCOES = {1: 'Preso às laterais', 2: 'Falso 9', 3: 'Falso lateral', 4: 'Lateral ofensivo', 5: 'Rotação de alas',
              6: 'Tiki-taka', 7: 'Alvo de cruzamento', 8: 'Defensivo', 9: 'Falso ala', 10: 'Ancoragem',
              11: 'Invadir área', 12: 'Defesa recuada', 13: 'Pressão ofensiva', 14: 'Marcação', 15: 'Pivô de contra-ataque',
              16: 'Lateral avançado'}
OFENSIVAS, DEFENSIVAS = set(range(1, 11)), set(range(11, 17))
COM_ALVO = {8, 10, 14, 15}            # 14: alvo no elenco do adversário
VAGAS = (228, 236, 244, 252)          # +0 a partir do bloco (plano A)


def instrucoes(d, ti, o=None):
    """[(código, nome, alvo)] das vagas ocupadas do time (ou do bloco `o`)."""
    o = bloco(d, ti) if o is None else o
    if o is None:
        return []
    out = []
    for v in VAGAS:
        cod, alvo = struct.unpack_from('<II', d, o + v)
        if cod:
            out.append((cod, INSTRUCOES.get(cod, f'? {cod}'), alvo))
    return out


def bloco_usuario(d):
    """Bloco do plano de jogo do USUÁRIO: 729 (as edições dele caem nesse; o 730 tem o mesmo técnico)."""
    o = BASE + 729 * TAM
    return o if d[o + 64:o + 96] == d[o + TAM + 64:o + TAM + 96] else None


def ler_em(d, o, plano=0):
    p = o + PLANOS[plano]
    return {k: d[p + off] for k, off in CAMPOS.items()}


def escalacao(d, ti):
    """Posição (no save) da ESCALAÇÃO do time: 40 bytes = posição no elenco de cada vaga (11 primeiros = titulares).
    12/10/2026 (x64dbg): o registro de verdade de cada clube começa em +56 deste bloco (u16 índice do time) e tem 600 B;
    a escalação fica no FIM dele (+544 do registro) = +0 do bloco SEGUINTE; cobradores em +40..+45 e capitão em +49
    desse mesmo trecho. Na memória o técnico da IA lê/escreve objeto+0x220 = esse endereço."""
    o = bloco(d, ti)
    return o + TAM if o is not None else None


def titulares(d, ti):
    """Posições no elenco (SaveML.squad) dos 11 primeiros da escalação gravada do time."""
    o = escalacao(d, ti)
    return [x for x in d[o:o + 11] if x != 0xFF] if o is not None else []
import struct

BASE = 0x133C50
TAM = 600
N = 731
PLANOS = (120, 280, 440)
CAMPOS = {'estilo_ofensivo': 99, 'saida_de_bola': 100, 'area_ataque': 101, 'posicionamento': 102,
          'estilo_defensivo': 103, 'contencao': 104, 'pressao': 105,
          'apoio': 140, 'linha_defensiva': 142, 'compactacao': 143}
LIMITES = {'apoio': (1, 10), 'linha_defensiva': (1, 10), 'compactacao': (1, 10)}


def bloco(d, ti):
    """Posição do bloco do time `ti` (pelo índice gravado em +56), ou None."""
    for b in (ti - 1, ti) + tuple(range(N)):
        if 0 <= b < N and struct.unpack_from('<H', d, BASE + b * TAM + 56)[0] == ti:
            return BASE + b * TAM
    return None


def tecnico(d, ti):
    o = bloco(d, ti)
    return d[o + 64:o + 96].split(b'\0')[0].decode('utf-8', 'replace') if o is not None else None


def ler(d, ti, plano=0):
    o = bloco(d, ti)
    if o is None:
        return None
    p = o + PLANOS[plano]
    return {k: d[p + off] for k, off in CAMPOS.items()}


def com_tatica(d, ti, **valores):
    """Cópia de `d` com os valores trocados nos 3 planos do time. Só mexe nos bytes dos campos pedidos."""
    o = bloco(d, ti)
    if o is None:
        raise ValueError(f'bloco do time {ti} não encontrado')
    novo = bytearray(d)
    for k, v in valores.items():
        lo, hi = LIMITES.get(k, (0, 1))
        if not lo <= int(v) <= hi:
            raise ValueError(f'{k}={v} fora de {lo}..{hi}')
        for p in PLANOS:
            novo[o + p + CAMPOS[k]] = int(v)
    return bytes(novo)
