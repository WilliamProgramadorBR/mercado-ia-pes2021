# Mercado IA — autor: William (https://github.com/WilliamProgramadorBR)
"""Qual é o time do usuário numa carreira da ML (data.dat descriptografado). SOMENTE LEITURA.

Descoberto em 10/10/2026 comparando 4 carreiras (Man Utd 13, Flamengo 122, Atlético de Madrid 41, Wolverhampton 19):
o índice do time do usuário (na tabela de times do save) fica, entre outros lugares, nestes u16 fixos.
Exige que pelo menos 2 dos 3 concordem; senão devolve None (quem chama usa o padrão configurado).
"""
import struct

POSICOES = (0xAFA22C, 0xB628C8, 0xCAC26C)


def indice_do_usuario(d):
    # bits altos são marcadores: depois de trocar de clube (demissão -> Mirassol, 10/10/2026) o valor virou 0x407E
    # (126 | 0x4000). Mesmo esquema do código de time nas súmulas/tabela (índice = valor & 0x3FFF).
    vals = [struct.unpack_from('<H', d, o)[0] & 0x3FFF for o in POSICOES if o + 2 <= len(d)]
    for v in vals:
        if v < 1000 and vals.count(v) >= 2:
            return v
    return None


# Bloco próprio do time do usuário (escalação, cobradores +40..45, capitão +49, nome do técnico +0x40): logo depois
# das 730 listas de escalação, que começam em 0x133C50 (posição igual nas 4 carreiras conferidas em 10/10/2026).
BLOCO_USUARIO = 0x133C50 + 730 * 600


def bloco_usuario(d):
    """(posição do bloco, nome do técnico) ou (None, None) se o nome não parecer válido."""
    nome = bytes(d[BLOCO_USUARIO + 0x40:BLOCO_USUARIO + 0x80]).split(b'\x00')[0]
    try:
        txt = nome.decode('utf-8')
    except UnicodeDecodeError:
        return None, None
    if not txt or not txt.isprintable():
        return None, None
    return BLOCO_USUARIO, txt


def time_do_usuario(d, padrao=None):
    """(índice, nome) do time do usuário."""
    from save_ml import SaveML
    s = SaveML.__new__(SaveML)
    s.path, s.d, s.base = None, bytearray(d), d.index(b'ARSENAL\x00')
    i = indice_do_usuario(d)
    if i is None:
        if not padrao:
            raise RuntimeError('time do usuário não encontrado no save')
        i = s.find_team(padrao)
    return i, s.name(i).strip()
