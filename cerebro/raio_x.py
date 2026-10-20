# Mercado IA — autor: William (https://github.com/WilliamProgramadorBR)
"""RAIO-X DO TIME na imprensa (20/10/2026): os números da tela "Desempenho do clube" (desempenho_save.py) viram
matéria a cada 8 jogos jogados na temporada — por onde o time ataca, quando marca e quando sofre, como saem os gols,
quem carrega o time e o que mudou nos últimos jogos. Só fatos do próprio jogo; nada é inventado.
Gancho: aplicar_vestiario (depois da análise do jogo). Frente "temporada" da Central.
"""
import random

import desempenho_save as DS
import imprensa_db as db

A_CADA = 8


def _pct(x):
    return f'{round(100 * x)}%'


def frases(r, rec=None, time='o time'):
    """[(peso, frase)] dos números mais marcantes (os pesos escolhem manchete e ordem)."""
    out = []
    Time = time[:1].upper() + time[1:]   # capitalize() rebaixaria o nome do clube
    lados = r['lados']
    if lados['esquerda'] + lados['direita'] >= 0.70:
        lado = 'direita' if lados['direita'] >= lados['esquerda'] else 'esquerda'
        out.append((1.0, f'{Time} é um time de beirada: {_pct(lados["esquerda"])} das jogadas pela esquerda, '
                         f'{_pct(lados["direita"])} pela direita e só {_pct(lados["centro"])} pelo meio. O lado preferido é o da {lado}.'))
    elif lados['centro'] >= 0.40:
        out.append((1.0, f'{Time} gosta de atacar por dentro: {_pct(lados["centro"])} das jogadas pelo meio.'))
    if r['enfiada_sofridos'] is not None and r['sofridos'] >= 8 and r['enfiada_sofridos'] >= 0.40:
        out.append((2.0 + r['enfiada_sofridos'], f'O calcanhar de Aquiles está nas costas da defesa: {_pct(r["enfiada_sofridos"])} '
                                                 f'dos {r["sofridos"]} gols sofridos nasceram de passe e enfiada.'))
    gp, sp = r['gols_periodo'], r['sofridos_periodo']
    if r['gols'] >= 10:
        melhor = max(gp, key=gp.get)
        out.append((1.2 + (0.8 if melhor == '76-90' else 0), f'O período mais produtivo é o dos {melhor} minutos: {gp[melhor]} dos {r["gols"]} gols.'
                    + (' É um time de reta final.' if melhor == '76-90' else '')))
    if r['sofridos'] >= 8:
        pior = max(sp, key=sp.get)
        out.append((1.1, f'Na defesa, o momento mais perigoso é o dos {pior} minutos: {sp[pior]} gols sofridos.'))
    tf = r['tipos_feitos']
    if r['gols'] >= 10:
        top = max((k for k in tf if k != 'outros'), key=tf.get)
        out.append((0.8, f'Como o time marca: {tf[top]} gols de {top}' + (f', {tf["jogada ensaiada"]} de bola parada ensaiada'
                                                                          if top != 'jogada ensaiada' and tf['jogada ensaiada'] >= 5 else '') + '.'))
    for x in (r.get('protagonistas') or [])[:1]:
        if x['parte_chutes'] >= 0.35 and x['nome']:
            out.append((1.8 + x['parte_chutes'], f'{x["nome"]} carrega o ataque: {_pct(x["parte_chutes"])} dos chutes do time, '
                                                 f'{_pct(x["parte_dribles"])} dos dribles e conversão de {_pct(x["conversao"] or 0)}.'))
    if rec and rec['jogos'] >= 5 and r['jogos'] >= rec['jogos'] + 5:
        a, b = rec['resumo'], r
        ch_a, ch_b = a['chutes_gol_pj'] or 0, b['chutes_gol_pj'] or 0
        so_a, so_b = a['chutes_sofridos_gol_pj'] or 0, b['chutes_sofridos_gol_pj'] or 0
        if abs(ch_a - ch_b) >= 1.0:
            out.append((1.5, f'Nos últimos {rec["jogos"]} jogos, o ataque {"cresceu" if ch_a > ch_b else "caiu"}: '
                             f'{ch_a:.1f} chutes no gol por jogo, contra {ch_b:.1f} na temporada.'))
        if abs(so_a - so_b) >= 0.8:
            out.append((1.5, f'Atrás, {"a defesa piorou" if so_a > so_b else "a defesa melhorou"}: o adversário acertou '
                             f'{so_a:.1f} chutes no gol por jogo nos últimos {rec["jogos"]}, contra {so_b:.1f} na temporada.'))
    out.sort(key=lambda t: -t[0])
    return out


def da_reuniao(car, r, d, snap, log=print):
    """(matérias, notícias): uma matéria a cada A_CADA jogos jogados na temporada."""
    import imprensa
    ctx = imprensa._contexto(car, r, d, snap)
    nomes = {k: f.name.strip() for k, f in (ctx.get('P') or {}).items()}
    t = DS.temporada(d, nomes)
    if not t or t['jogos'] < A_CADA:
        return [], []
    marco = t['jogos'] // A_CADA * A_CADA
    ano = tuple(r['hoje'])[0]
    ultimo = car.get('raiox') or {}
    if ultimo.get('marco') == marco and ultimo.get('ano_jogo') in (ano, ano - 1):
        return [], []
    ck = car.get('ck')
    import carreira
    _, nome_save = carreira.time_do_usuario(d)
    rec = DS.janela(nome_save, A_CADA)
    time = r.get('time') or 'o time'
    fr = frases(t, rec, f'o {time}')
    car['raiox'] = {'marco': marco, 'ano_jogo': ano}
    if len(fr) < 3:
        return [], []
    chave = f'raiox|{ck}|{ano}|{marco}'
    if db.existe(ck, chave):
        return [], []
    rnd = random.Random(chave)
    top = fr[0][1]
    if 'calcanhar' in top:
        titulo = rnd.choice([f'Raio-x do {time}: o perigo mora nas costas da defesa', f'{time}: os números mostram o ponto fraco'])
    elif 'carrega o ataque' in top:
        nome = top.split(' carrega')[0]
        titulo = rnd.choice([f'Raio-x: o {time} vive do {nome}?', f'{nome} é o motor do {time}, dizem os números'])
    elif 'reta final' in top:
        titulo = f'Raio-x: o {time} é time de reta final'
    else:
        titulo = rnd.choice([f'Raio-x do {time} depois de {t["jogos"]} jogos', f'O {time} em números: {t["jogos"]} jogos de temporada'])
    corpo = [f'A Mesa Tática abriu os números do próprio jogo depois de {t["jogos"]} jogos: {t["gols"]} gols marcados, '
             f'{t["sofridos"]} sofridos, {t["posse"]}% de posse e {t["chutes_pj"]:.1f} chutes por jogo '
             f'({t["chutes_gol_pj"]:.1f} no gol).'] + [f for _, f in fr[:5]]
    m = {'chave': chave, 'frente': 'temporada', 'data': tuple(r['hoje']), 'autor': 'Mesa Tática · raio-x', 'titulo': titulo,
         'linha_fina': f'Os números da temporada: por onde ataca, quando marca, como sofre e quem carrega o time.',
         'corpo': corpo, 'dados': {'tipo': 'raiox', 'jogos': t['jogos']}}
    log(f'raio-x: {titulo}')
    return [m], [f'RAIO-X: {titulo}']
