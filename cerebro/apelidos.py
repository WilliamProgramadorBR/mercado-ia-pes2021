"""Apelidos dados pela torcida (Vestiário IA) — usa o sistema NATIVO de apelidos do PES.

Formato (confirmado no jogo em 09/10/2026: Justin Omoregie virou "El Diablo" na ficha e na mensagem):
  registro do jogador (156 bytes) +80 = u32 (0x1D << 16) | código; 0 = sem apelido;
  mensagem nativa tipo 89 "Apelido do X" (assistente técnico) com o mesmo u32 em +64 e o jogador em +40.
Textos: historico/apelidos_catalogo.json — 114 códigos confirmados (trechos da lista do jogo ancorados em
apelidos reais vistos na tela). Só usamos códigos desse catálogo.

Regra: no máximo 1 apelido por mês do jogo; candidato = jogador do usuário SEM apelido e com status alto
(Lenda/Ídolo/Superastro) ou torcida >= 80; apelido combinando com a posição e que nenhum jogador do mundo use.
"""
import json
import os
import random
import struct

HERE = os.path.dirname(os.path.abspath(__file__))
CATALOGO = os.path.join(HERE, 'historico', 'apelidos_catalogo.json')
GRUPO = 0x1D

POR_FUNCAO = {
    'GK': [377, 428, 744, 724],
    'DEF': [374, 414, 429, 408, 674, 743, 424, 673, 436],
    'MEI': [381, 402, 433, 401, 386, 439, 740, 745, 406],
    'ALA': [727, 747, 737, 741, 422, 397, 729, 363],
    'ATA': [730, 379, 421, 398, 409, 732, 731, 748, 368, 734, 733],
    'JOVEM': [410, 667, 668, 422],
}
GRUPO_POS = {'GK': 'GK', 'CB': 'DEF', 'LB': 'DEF', 'RB': 'DEF', 'DMF': 'MEI', 'CMF': 'MEI', 'AMF': 'MEI',
             'LMF': 'ALA', 'RMF': 'ALA', 'LWF': 'ALA', 'RWF': 'ALA', 'SS': 'ATA', 'CF': 'ATA'}


def catalogo():
    try:
        with open(CATALOGO, encoding='utf-8') as f:
            return {int(k): v for k, v in json.load(f)['apelidos'].items()}
    except (OSError, ValueError, KeyError):
        return {}


def codigo_de(reg_bytes):
    v = struct.unpack_from('<I', reg_bytes, 80)[0]
    return v & 0xFFFF if v else 0


def com_apelido(reg_bytes, codigo):
    r = bytearray(reg_bytes)
    struct.pack_into('<I', r, 80, (GRUPO << 16) | codigo)
    return bytes(r)


def escolher(car, J, regs, hoje):
    """Devolve {'k','nome','codigo','texto'} ou None. Não grava nada."""
    if car.get('apelido_mes') == [hoje[0], hoje[1]]:
        return None
    cat = catalogo()
    if not cat:
        return None
    usados = {codigo_de(r) for r in regs.values()}
    cands = [j for j in J if j['k'] in regs and not codigo_de(regs[j['k']]) and
             (j['status'] in ('Lenda', 'Ídolo', 'Superastro') or j['torcida'] >= 80)]
    if not cands:
        return None
    j = max(cands, key=lambda j: (j['torcida'], j['ovr']))
    grupo = 'JOVEM' if j['idade'] <= 20 and j['status'] == 'Promessa' else GRUPO_POS.get(j['pos'], 'MEI')
    opcoes = [c for c in POR_FUNCAO[grupo] if c in cat and c not in usados] or \
             [c for g in POR_FUNCAO.values() for c in g if c in cat and c not in usados]
    if not opcoes:
        return None
    rnd = random.Random(f'{j["k"]}|{hoje}')
    c = rnd.choice(opcoes)
    return {'k': list(j['k']), 'nome': j['nome'], 'codigo': c, 'texto': cat[c]}
