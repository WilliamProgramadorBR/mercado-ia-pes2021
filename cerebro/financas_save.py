# Mercado IA — autor: William (https://github.com/WilliamProgramadorBR)
"""Finanças do clube do usuário no save da Master League (data.dat descriptografado).

Descoberto em 09/10/2026 comparando 4 saves com os prints do jogo (valores x 430 = R$ na tela):
  bloco do clube do usuário (estava em 0xc7dd00 em todos os saves, mas sempre localizamos pela ÂNCORA):
    -44 u32 108   -40 u32 0xFFFF                        (iguais em todos os saves)
    -24 u32 3 em jan/2034, 1 em abr/2034 (fase/janela?) — NÃO serve de âncora
    +0  u32 ORÇAMENTO DE TRANSFERÊNCIAS atual           CONFIRMADO (357.498.560 / 352.836.500 / 347.803.350)
    +16 u32 igual ao +0 depois da janela de janeiro (orçamento da janela?)
    +20 u32 cresce com o tempo (receita acumulada?)
    +28 u32 perto do orçamento de salários, mas não igual (18/04/2034: 292.306.690 x 293.007.160 na tela) — suspeita
    +64 u32 13 até jun/2034 e 0 depois da virada de temporada — NÃO é âncora (era coincidência)
GRAVAÇÃO do orçamento: ainda em teste (teste_orcamento.py). O bloco fica FORA da parte comprimida.
"""
import struct

X = 430


def achar_bloco(d, time_idx=None, perto=0xC7DD00, referencia=None):
    """Posição (+0) do orçamento de transferências do usuário.
    A posição 0xC7DD00 foi a mesma em 7 saves (dez/2033 -> virada para 2034/35). Conferências:
      -44 == 108 e -40 == 0xFFFF (únicos valores fixos em volta, comparando os 7 saves);
      valor plausível (0 < R$ < 5 bi);
      se `referencia` (último orçamento conhecido, em R$) for dado: o valor atual tem que estar entre 50% e 150% dele.
    ATENÇÃO (09/10/2026): o antigo teste "+64 == índice do time" era coincidência — na virada de temporada vale 0.
    `time_idx` fica só por compatibilidade."""
    o = perto
    ok = (o - 44 >= 0 and o + 4 <= len(d) and
          struct.unpack_from('<I', d, o - 44)[0] == 108 and
          struct.unpack_from('<I', d, o - 40)[0] == 0xFFFF)
    v = struct.unpack_from('<I', d, o)[0] * X if ok else 0
    if not ok or not (0 < v < 5e9):
        raise RuntimeError('bloco de finanças não encontrado com segurança (marcadores ou valor fora do esperado)')
    if referencia and not (0.5 * referencia <= v <= 1.5 * referencia):
        raise RuntimeError(f'orçamento no save (R$ {v:,.0f}) muito diferente do último conhecido (R$ {referencia:,.0f})')
    return o


def ler(d, time_idx=None, referencia=None):
    o = achar_bloco(d, time_idx, referencia=referencia)
    u = lambda k: struct.unpack_from('<I', d, o + k)[0]
    return {'pos': o, 'orcamento_transf': u(0) * X, 'orcamento_janela?': u(16) * X, 'u20': u(20) * X,
            'orcamento_salarios?': u(28) * X}


def com_orcamento(d, time_idx, novo_reais):
    """Cópia do data.dat com o orçamento de transferências trocado (arredonda para múltiplo de 430)."""
    o = achar_bloco(d, time_idx)
    v = max(0, int(round(novo_reais / X)))
    d = bytearray(d)
    struct.pack_into('<I', d, o, v)
    return bytes(d)
