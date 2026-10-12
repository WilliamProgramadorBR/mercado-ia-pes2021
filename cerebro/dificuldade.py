"""Dificuldade dinâmica do vestiário (11/10/2026).

Técnico NOVO no clube + espírito de equipe BAIXO (valor do próprio jogo, save 0xB629BC) = vestiário instável: mais
casos de disciplina, mais pedidos, mais crises, imprensa mais dura. Técnico antigo com espírito alto = vestiário calmo.

  multiplicador m: ~0,5 (clube estável, espírito 95+) até ~2,3 (recém-chegado, espírito < 40)
Os geradores (disciplina, exigencias, humor, crises) multiplicam as chances por m. Fica em car['dificuldade'].
"""
from vestiario import dias

ESPIRITO = 0xB629BC
M = {'m': 1.0}   # valor da rodada atual (lido pelos geradores)


def calcular(car, d, hoje):
    esp = d[ESPIRITO] if d[ESPIRITO] <= 100 else 60
    if 'tecnico_desde' not in car:
        # carreira que já existia: a data mais antiga registrada no histórico dela (senão, hoje = recém-chegado)
        datas = [tuple(h['data']) for h in (car.get('historias') or {}).values() if h.get('data') and h['data'][0] > 2000]
        datas += [tuple(n['data']) for n in car.get('noticias', []) if n.get('data') and n['data'][0] > 2000]
        datas += [tuple(a['data']) for a in (car.get('diretoria') or {}).get('avaliacoes', []) if a.get('data')]
        car['tecnico_desde'] = list(min(datas)) if datas else list(hoje)
    desde = car['tecnico_desde']
    dias_clube = max(0, dias(tuple(hoje), tuple(desde)))
    novo = max(0.0, (240 - dias_clube) / 240)                 # 1 na chegada -> 0 depois de ~8 meses
    falta_espirito = max(0.0, (85 - esp) / 45)                # 0 com espírito 85+ ; ~1 com 40
    m = 0.5 + 0.9 * falta_espirito + 0.7 * novo + 0.4 * falta_espirito * novo
    m = round(max(0.45, min(2.3, m)), 2)
    if m >= 1.6:
        nivel, texto = 'explosivo', 'Vestiário instável: o grupo ainda não comprou a ideia do técnico. Espere cobranças, crises e testes de autoridade.'
    elif m >= 1.15:
        nivel, texto = 'tenso', 'Vestiário desconfiado: há resistência a algumas decisões. Cada resposta pesa.'
    elif m >= 0.8:
        nivel, texto = 'normal', 'Vestiário dentro do normal: problemas pontuais, nada fora do controle.'
    else:
        nivel, texto = 'blindado', 'Vestiário blindado: técnico respeitado e espírito de equipe alto. Crises são raras.'
    car['dificuldade'] = {'m': m, 'nivel': nivel, 'texto': texto, 'espirito': esp, 'dias_clube': dias_clube}
    M['m'] = m
    return car['dificuldade']


def chance(base, teto=0.9):
    return min(teto, base * M['m'])
