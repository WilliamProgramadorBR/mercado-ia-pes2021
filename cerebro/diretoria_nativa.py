"""Estado da DIRETORIA DO PRÓPRIO PES lido do save (somente leitura). Descoberto em 10/10/2026 no laboratório
(Flamengo 2026 e Mirassol 2027, duas demissões completas).

Regra nativa: com OBJETIVO DA TEMPORADA definido (cena "Objetivos da temporada" no início do ano), o jogo avalia os
resultados REAIS de liga na VIRADA DE CADA MÊS. Mês ruim -> pressão da diretoria; outro mês ruim -> ultimato
("se não vencer a próxima, arrume as malas"); derrota no jogo seguinte -> demissão (a cadeia é zerada e chegam
propostas de outros clubes). Escrever esses registros na memória NÃO funciona: o jogo recalcula e desfaz.

Tabela de capítulos de história (0xBE2264, 98 registros de 44 B): +0 id, +4 marcadores, +12 liberado,
+16 situação (0 nada, 1 em andamento, 3 encerrado/falhou), +20 data início, +24 data fim, +28 código da competição.
"""
import struct

TABELA, N, REC = 0xBE2264, 98, 44
CLUBE_USUARIO, INICIO_PERIODO = 0xCAC26C, 0xCAC270

OBJETIVO = (0x28204D8, 0x14A)        # "Objetivos da temporada" (código muda com o tipo de objetivo)
PRESSAO = (0x7800054,)               # cobrança da diretoria ("a imprensa vai especular sobre a sua saída")
NIVEL_PRESSAO = (0x5000058,)         # marcadores sobem quando a pressão começa (02 -> C2)
ULTIMATO = (0x280005C,)              # "se não vencer a próxima partida, pode arrumar as malas"
DEMISSAO = (0x840448,)               # "a diretoria acabou de rasgar o seu contrato"


def _data(r, o):
    y, m, d = struct.unpack_from('<HBB', r, o)
    return [y, m, d] if 2000 <= y <= 2100 else None


def capitulos(d):
    out = {}
    for i in range(N):
        o = TABELA + i * REC
        r = d[o:o + REC]
        out[struct.unpack_from('<I', r, 0)[0]] = {
            'marcas': struct.unpack_from('<I', r, 4)[0], 'liberado': struct.unpack_from('<I', r, 12)[0],
            'situacao': struct.unpack_from('<I', r, 16)[0], 'inicio': _data(r, 20), 'fim': _data(r, 24),
            'competicao': struct.unpack_from('<I', r, 28)[0]}
    return out


def ler(d, hoje=None):
    """{'estado': 'sem_objetivo'|'tranquilo'|'pressao'|'ultimato'|'demitido', 'objetivo_desde', 'pressao_desde',
        'ultimato_desde', 'periodo', 'texto'}"""
    c = capitulos(d)

    def ativo(ids):
        for i in ids:
            x = c.get(i)
            if x and x['situacao'] == 1:
                return x
        return None

    def recente(ids):
        for i in ids:
            x = c.get(i)
            if x and x['situacao'] == 3 and x['fim'] and hoje and \
                    (hoje[0] * 12 + hoje[1]) - (x['fim'][0] * 12 + x['fim'][1]) <= 1:
                return x
        return None

    obj = ativo(OBJETIVO)
    pres = ativo(PRESSAO) or recente(PRESSAO)
    nivel = any(c.get(i) and c[i]['marcas'] & 0xC0 for i in NIVEL_PRESSAO + PRESSAO)
    ult = ativo(ULTIMATO)
    dem = recente(DEMISSAO)
    periodo = _data(d, INICIO_PERIODO)
    if dem:
        estado, texto = 'demitido', 'A diretoria rasgou o contrato do técnico.'
    elif ult:
        estado, texto = 'ultimato', 'ULTIMATO: se não vencer a próxima partida, o técnico cai.'
    elif pres or nivel:
        estado, texto = 'pressao', 'A diretoria do clube cobra resultados; a imprensa já especula a saída do técnico.'
    elif obj:
        estado, texto = 'tranquilo', 'Objetivo da temporada definido; a diretoria avalia os resultados de liga a cada virada de mês.'
    else:
        estado, texto = 'sem_objetivo', 'Sem objetivo da temporada definido: a diretoria do jogo não tem o que cobrar.'
    return {'estado': estado, 'texto': texto, 'periodo': periodo,
            'objetivo_desde': obj['inicio'] if obj else None,
            'pressao_desde': pres['inicio'] if pres else None,
            'ultimato_desde': ult['inicio'] if ult else None}


if __name__ == '__main__':
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    for p in sys.argv[1:]:
        print(p, ler(open(p, 'rb').read(), hoje=None))
