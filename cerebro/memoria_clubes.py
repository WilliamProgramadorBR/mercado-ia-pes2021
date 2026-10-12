"""Memória esportiva e econômica persistente dos clubes controlados pela IA.

O save do PES não expõe de forma confiável toda a economia dos adversários. Este
arquivo mantém um livro-caixa externo, separado por carreira, e uma identidade
estável para cada clube. Nada é gravado durante ensaios: aplicar.py só persiste a
memória depois que o save criptografado passou pela conferência de ida e volta.
"""
import hashlib
import json
import math
import os
import statistics as st

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(HERE, 'historico', 'memoria_clubes.json')
SCHEMA = 1


def load(path=PATH):
    if not os.path.exists(path):
        return {'schema': SCHEMA, 'carreiras': {}}
    try:
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
    except (OSError, ValueError):
        return {'schema': SCHEMA, 'carreiras': {}}
    data.setdefault('schema', SCHEMA)
    data.setdefault('carreiras', {})
    return data


def save(data, path=PATH):
    """Gravação atômica: um arquivo incompleto nunca substitui a memória válida."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def career(data, key):
    return data['carreiras'].setdefault(key, {'clubes': {}, 'historico': []})


def _unit(name, salt):
    raw = hashlib.sha256(f'{salt}|{name}'.encode('utf-8')).digest()
    return int.from_bytes(raw[:8], 'little') / ((1 << 64) - 1)


def make_profile(team, evaluation):
    """Cria uma personalidade estável a partir da realidade do elenco e do nome do clube."""
    ages = [p.age for p in team.players]
    avg_age = st.mean(ages) if ages else 27
    youth_share = sum(a <= 23 for a in ages) / max(1, len(ages))
    old_share = sum(a >= 30 for a in ages) / max(1, len(ages))
    tier = evaluation['forca']

    if tier >= 84:
        archetype = 'elite'
    elif youth_share >= 0.34 and avg_age <= 26.5:
        archetype = 'formador'
    elif avg_age >= 28.5 or old_share >= 0.35:
        archetype = 'reconstrucao'
    elif tier < 75:
        archetype = 'modesto'
    elif youth_share >= 0.25:
        archetype = 'vendedor'
    else:
        archetype = 'equilibrado'

    defaults = {
        'elite':         (1.18, 0.38, 0.35, 0.35, 30),
        'formador':      (0.98, 0.92, 0.55, 0.78, 24),
        'vendedor':      (0.94, 0.72, 0.48, 0.88, 27),
        'reconstrucao':  (1.04, 0.78, 0.62, 0.66, 27),
        'modesto':       (0.88, 0.55, 0.38, 0.82, 29),
        'equilibrado':   (1.00, 0.55, 0.50, 0.58, 29),
    }
    ambition, youth, risk, selling, max_age = defaults[archetype]
    # Pequenas diferenças determinísticas: personalidade, não roleta por execução.
    ambition *= 0.94 + 0.12 * _unit(team.name, 'ambicao')
    youth = min(1.0, max(0.0, youth + (_unit(team.name, 'base') - 0.5) * 0.14))
    risk = min(1.0, max(0.0, risk + (_unit(team.name, 'risco') - 0.5) * 0.18))
    selling = min(1.0, max(0.0, selling + (_unit(team.name, 'venda') - 0.5) * 0.14))
    return {
        'tipo': archetype,
        'ambicao': round(ambition, 2),
        'juventude': round(youth, 2),
        'risco': round(risk, 2),
        'propensao_venda': round(selling, 2),
        'idade_alvo': max_age,
        'criado_com_forca': round(tier, 1),
        'criado_com_idade_media': round(avg_age, 1),
    }


def base_budget(tier, profile, rival=False, seed_budget=1.0):
    value = seed_budget * 0.6 * math.exp((tier - 70) / 4)
    value *= profile['ambicao']
    if rival:
        value *= 1.6
    return round(value, 1)


def prepare(career_state, team, evaluation, year, rival=False, seed_budget=1.0):
    """Retorna (perfil, orçamento disponível), renovando receita quando muda a temporada."""
    clubs = career_state.setdefault('clubes', {})
    state = clubs.setdefault(team.name, {})
    profile = state.setdefault('perfil', make_profile(team, evaluation))
    base = base_budget(evaluation['forca'], profile, rival, seed_budget)
    if 'orcamento' not in state:
        state['orcamento'] = base
        state['ultima_temporada'] = year
    elif year > state.get('ultima_temporada', year):
        seasons = min(5, year - state.get('ultima_temporada', year))
        annual_revenue = base * (0.55 + 0.25 * profile['ambicao'])
        state['orcamento'] = round(min(base * 2.5, state['orcamento'] + seasons * annual_revenue), 1)
        state['ultima_temporada'] = year
    state['ultima_forca'] = evaluation['forca']
    state['ultima_formacao'] = evaluation.get('formacao', '')
    return profile, round(state['orcamento'], 1)


def record(career_state, applied, year, window):
    """Aplica ao livro-caixa apenas negócios que realmente entraram no save."""
    clubs = career_state.setdefault('clubes', {})
    summary = {'temporada': year, 'janela': window, 'negocios': []}
    for move, _shirt in applied:
        buyer = clubs.get(move.para)
        seller = clubs.get(move.de)
        if buyer is not None:
            buyer['orcamento'] = round(max(0.0, buyer.get('orcamento', 0) - move.valor), 1)
            buyer['compras'] = buyer.get('compras', 0) + 1
            buyer['investido'] = round(buyer.get('investido', 0) + move.valor, 1)
        if seller is not None:
            seller['orcamento'] = round(seller.get('orcamento', 0) + move.valor, 1)
            seller['vendas'] = seller.get('vendas', 0) + 1
            seller['recebido'] = round(seller.get('recebido', 0) + move.valor, 1)
        summary['negocios'].append({
            'jogador': move.jogador, 'de': move.de, 'para': move.para,
            'valor': move.valor, 'motivo': move.motivo,
        })
    career_state.setdefault('historico', []).append(summary)
    # Impede crescimento infinito sem perder o arco recente da carreira.
    career_state['historico'] = career_state['historico'][-24:]

