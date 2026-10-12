"""COLETIVA NO DIA DO JOGO (11/10/2026).

Antes a coletiva só nascia na reunião (depois do save + mercado + vestiário + IA: alguns minutos). Quem simula rápido
recebia a coletiva do jogo anterior. Agora o pulso (memória do jogo, a cada 4 s) vê o resultado assim que o jogo
acaba e a Central monta na hora a coletiva pós-jogo, com as mesmas perguntas/efeitos de midia._pergunta:
resultado (craque do jogo pela súmula da memória), destaque/artilheiro e o próximo adversário.
Arquivo: historico/coletiva_viva_<slot>.json. A reunião seguinte REAPROVEITA essa coletiva (mesmo id) em vez de
criar outra para o mesmo jogo (midia.edicao), e as respostas valem pelo diário como sempre (acoes.consumir).
"""
import json
import os
import random

HERE = os.path.dirname(os.path.abspath(__file__))
HIST = os.path.join(HERE, 'historico')


def arquivo(slot):
    return os.path.join(HIST, f'coletiva_viva_{slot}.json')


def ler(slot):
    try:
        with open(arquivo(slot), encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _gerar(dados, p):
    import midia
    from proximo_jogo import nome_comp
    g = (p.get('ultimos_jogos') or [])[-1]
    uj = p.get('ultimo_jogo') or {}
    J = [{'k': (j['reg'], j['pid']), 'nome': j['nome'], 'pos': j['pos'], 'status': j['status'], 'moral': j['moral']}
         for j in dados.get('jogadores') or []]
    porK = {j['k']: j for j in J}
    marc, melhor = [], None
    for x in uj.get('linhas') or []:
        j = porK.get((x['reg'], x['pid']))
        if j and x['gols']:
            marc.append((j, x['gols']))
        if j and x['nota'] and (melhor is None or x['nota'] + 0.6 * x['gols'] > melhor[1]):
            melhor = (j, x['nota'] + 0.6 * x['gols'])
    F = [{'tipo': 'resultado' if g['pro'] >= g['contra'] else 'derrota', 'peso': 9, 'jogo': g, 'marcadores': marc, 'melhor': melhor}]
    if marc:
        art = max(marc, key=lambda m: m[1])[0]
        if not melhor or art is not melhor[0]:
            F.append({'tipo': 'destaque', 'peso': 4, 'j': art})
    pr = p.get('proximo')
    if pr:
        adv = pr['fora'] if pr['casa'] == dados.get('time') else pr['casa']
        F.append({'tipo': 'proximo', 'peso': 3, 'pj': {'adversario': adv, 'competicao': nome_comp(pr['comp'])}})
    data = tuple(g['data'])
    rnd = random.Random(f'colv|{dados.get("carreira")}|{data}')
    col = None
    try:   # 55 cenários ligados ao jogo (clássico, placar, súmula da memória, tabela...)
        import coletiva_cenarios as cc
        ps = cc.gerar(cc.contexto_vivo(dados, p), n=3, seed='vivo')
        if len(ps) >= 2:
            col = midia.montar_coletiva(ps, data, rnd)
    except Exception as e:  # noqa: BLE001
        print('aviso: cenários da coletiva ao vivo:', e, flush=True)
    col = col or midia.coletiva(F, J, data, rnd, car=None)
    if not col:
        return None
    col['id'] = f'colv|{data[0]}-{data[1]:02d}-{data[2]:02d}'
    col['jogo'] = list(data)
    col['placar'] = f'{g["pro"]} x {g["contra"]}'
    col['adversario'] = g['adversario']
    col['ao_vivo'] = True
    return col


def atual(dados, p, slot):
    """Coletiva pós-jogo do último jogo que a MEMÓRIA mostra, criada uma vez por jogo. None se não houver."""
    if not p or not p.get('ultimos_jogos') or not slot:
        return None
    data = list(p['ultimos_jogos'][-1]['data'])
    viva = ler(slot)
    if viva and viva.get('jogo') == data:
        return viva
    reuniao = (dados.get('ultimos_jogos_reuniao') or [{}])[-1].get('data')
    if reuniao and tuple(reuniao) >= tuple(data) and dados.get('coletiva'):
        return None   # a reunião já cobriu este jogo com a coletiva dela
    try:
        col = _gerar(dados, p)
    except Exception as e:  # noqa: BLE001 - nunca derruba a Central
        print('aviso: coletiva ao vivo não gerada:', e, flush=True)
        return None
    if col:
        tmp = arquivo(slot) + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(col, f, ensure_ascii=False)
        os.replace(tmp, arquivo(slot))
    return col


def escolher(dados, viva):
    """Qual coletiva a Central mostra: a do jogo mais recente; empate de jogo = a ao vivo (já pode ter respostas)."""
    if not viva:
        return dados.get('coletiva')
    reuniao = (dados.get('ultimos_jogos_reuniao') or [{}])[-1].get('data')
    if not reuniao or tuple(viva['jogo']) >= tuple(reuniao) or not dados.get('coletiva'):
        return viva
    return dados.get('coletiva')
