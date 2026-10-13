# Mercado IA — autor: William (https://github.com/WilliamProgramadorBR)
"""ONDE COMEÇAM AS SELEÇÕES na tabela de times do save (13/10/2026), sem depender do idioma do patch.

Antes: find_team('ALBÂNIA') — o nome em português do banco do GOGOSZ. Num patch em inglês ("ALBANIA") o nome não
existia: alguns módulos caíam num número fixo (625) e o mercado perdia a proteção das seleções (uma seleção poderia
comprar jogadores).
Agora: os jogadores de uma seleção também estão registrados nos seus clubes, que vêm antes na tabela; um clube nunca
repete jogador de outro clube. O começo do bloco é o 1º time com 50%+ de jogadores já vistos em times anteriores,
desde que o bloco em volta também repita (5 dos 10 seguintes). Conferido em dois saves do GOGOSZ: 625, a Albânia.
Se a regra não achar, procura pelo nome em vários idiomas.
"""
_CACHE = {}
NOMES = ('ALBÂNIA', 'ALBANIA', 'ALBANIEN', 'ALBANIE', 'ALBANIJA')


def _repetidos(sq, vistos):
    return sum(1 for k in sq if k in vistos) / len(sq) if len(sq) >= 11 else 0.0


def primeira(s, padrao=None):
    """Índice do primeiro time que é seleção (s = SaveML). `padrao` se não achar."""
    import zlib
    chave = (len(s.d), s.base, zlib.crc32(bytes(s.d[s.base:s.base + 3_000_000])))   # mesma tabela de times = mesmo resultado
    if chave in _CACHE:
        return _CACHE[chave]
    elencos, i = [], 0
    while i < 900:
        try:
            nome = s.name(i)
        except Exception:  # noqa: BLE001
            break
        if not nome:
            break
        elencos.append([tuple(k) for k in s.squad(i)])
        i += 1
    vistos, achou = set(), None
    rep = []
    for sq in elencos:
        rep.append(_repetidos(sq, vistos))
        vistos.update(sq)
    # clube não repete jogador de outro clube (0%); seleção pequena (Andorra) repete pouco, mas o bloco todo repete:
    # o 1º time com 50%+ e, entre os 10 seguintes, pelo menos 5 com repetidos (conferido: clubes 0,0; seleções 0,17-1,0)
    for j in range(50, len(elencos)):
        janela = rep[j:j + 10]
        if rep[j] >= 0.5 and sum(1 for x in janela if x >= 0.15) >= min(5, len(janela)):
            achou = j
            break
    if achou is None:   # reserva: pelo nome, em vários idiomas
        achou = next((x for x in (s.find_team(n) for n in NOMES) if x is not None), None)
    _CACHE[chave] = achou if achou is not None else padrao
    return _CACHE[chave]
