"""Patrocínio (etapa 3 da vida futebolística, 10/10/2026).

ATRATIVIDADE do clube (0-100), com dados do próprio jogo: sócios-torcedores (save 0xB629A4), espírito de equipe
(0xB629BC), força do elenco (média das 14 melhores notas), estrelas (Lenda/Ídolo/Superastro/Craque), posição na
liga e confiança da diretoria. Clube pequeno não atrai patrocinador grande: o valor cresce bem mais que linear.

PATROCINADOR MASTER: quando o clube está sem contrato, chegam 2-3 propostas (Central -> acoes 'caso'). Cada uma:
  - aporte anual na VERBA DE SALÁRIOS (escrita ao vivo no jogo: bloco de finanças +20);
  - meta de posição na liga ao fim da temporada: cumpriu -> bônus no ORÇAMENTO de transferências;
    não cumpriu -> multa contratual (sai do orçamento). Contrato de 1 temporada.
Quanto mais exigente a meta, maior o aporte.
"""
import math
import struct

SOCIOS, ESPIRITO = 0xB629A4, 0xB629BC
ALTO = ('Lenda', 'Ídolo', 'Superastro', 'Craque')
MARCAS = [('Vortex Bank', 'banco digital'), ('Aurora Air', 'companhia aérea'), ('Nordex Energia', 'energia'),
          ('Tri-Max Telecom', 'telecomunicações'), ('Kaiser Motors', 'montadora'), ('Lumen Apostas', 'casa de apostas'),
          ('Pampa Alimentos', 'alimentos'), ('Orbe Seguros', 'seguradora'), ('Atlas Construtora', 'construtora')]


def _mi(v):
    return f'R$ {v / 1e6:.1f} mi'.replace('.', ',')


def atratividade(d, r, car):
    socios = struct.unpack_from('<I', d, SOCIOS)[0]
    espirito = d[ESPIRITO] if d[ESPIRITO] <= 100 else 50
    notas = sorted((j['ovr'] for j in r['J']), reverse=True)[:14]
    forca = sum(notas) / max(1, len(notas))
    estrelas = sum(1 for j in r['J'] if j['status'] in ALTO)
    dire = car.get('diretoria') or {}
    tab = dire.get('tabela') or []
    eu = next((t for t in tab if t.get('eu')), None)
    pos = eu['pos'] if eu and eu.get('j') else None
    p_socios = max(0, min(35, (math.log10(max(socios, 1)) - 5) * 17.5))          # 100 mil -> 0; 10 mi -> 35
    p_forca = max(0, min(25, (forca - 68) * 1.6))                                   # 68 -> 0; ~84 -> 25
    p_estrelas = min(15, estrelas * 2.5)
    p_pos = 0 if pos is None else max(0, min(15, (11 - pos) * 1.5))
    p_esp = espirito / 10
    img = (car.get('patrocinio') or {}).get('imagem', 60)
    p_img = (img - 60) / 4                                                          # imagem do clube: -15 .. +10
    total = round(p_socios + p_forca + p_estrelas + p_pos + p_esp + p_img)
    return {'indice': max(0, min(100, total)), 'socios': socios, 'espirito': espirito, 'forca': round(forca, 1),
            'estrelas': estrelas, 'posicao': pos,
            'partes': {'torcida': round(p_socios), 'elenco': round(p_forca), 'estrelas': round(p_estrelas),
                       'campanha': round(p_pos), 'espírito': round(p_esp), 'imagem': round(p_img)}}


def _valor_base(indice):
    """R$ por ano: ~R$ 4 mi (índice 20), ~R$ 40 mi (81), ~R$ 67 mi (95). Exponencial: o topo vale muito mais."""
    return 2_000_000 * math.exp(indice * 0.037)


def propostas(d, r, car, hoje, rnd):
    """Caso com 2-3 propostas de patrocínio master, se o clube estiver sem contrato. No máximo 1 vez por temporada."""
    temporada = hoje[0] if hoje[1] >= 7 else hoje[0] - 1
    pat = car.setdefault('patrocinio', {})
    if pat.get('contrato') or pat.get('oferta_temporada') == temporada:
        return []
    if any(c['tipo'] == 'patrocinio' for c in car.get('casos', [])):
        return []
    at = atratividade(d, r, car)
    pat['atratividade'] = at
    pat['oferta_temporada'] = temporada
    base = _valor_base(at['indice'])
    n_times = len((car.get('diretoria') or {}).get('tabela') or []) or 20
    meta_natural = max(1, min(n_times, round((100 - at['indice']) / 100 * n_times * 0.8) + 1))
    marcas = rnd.sample(MARCAS, 3)
    niveis = [('conservadora', meta_natural + 3, 0.75, 0.10, 0.10),
              ('equilibrada', meta_natural, 1.0, 0.20, 0.25),
              ('agressiva', max(1, meta_natural - 3), 1.45, 0.35, 0.50)]
    if at['indice'] < 35:
        niveis = niveis[:2]
    opcoes = []
    for (nivel, meta, mult, bonus_f, multa_f), (marca, setor) in zip(niveis, marcas):
        meta = max(1, min(n_times, meta))
        anual = int(round(base * mult * rnd.uniform(0.92, 1.08) / 100_000) * 100_000)
        bonus, multa = int(anual * bonus_f), int(anual * multa_f)
        opcoes.append({
            'id': str(len(opcoes) + 1),
            'texto': f'{marca} ({setor}): {_mi(anual)}/ano na verba de salários; meta: '
                     f'{"ser campeão" if meta == 1 else f"terminar em {meta}º ou melhor"} (bônus {_mi(bonus)} / multa {_mi(multa)})',
            'efeitos': [{'k': '*', 'delta': 1, 'rodadas': 1, 'motivo': 'o clube fechou um novo patrocínio master'}],
            'patrocinio': {'marca': marca, 'setor': setor, 'nivel': nivel, 'anual': anual, 'meta_pos': meta,
                           'bonus': bonus, 'multa': multa, 'temporada': temporada},
            'eco': (f'{marca} é o novo patrocinador master', f'Contrato de {_mi(anual)} por temporada.')})
    opcoes.append({'id': str(len(opcoes) + 1), 'texto': 'Recusar todas e esperar propostas melhores na próxima temporada',
                   'efeitos': [], 'eco': ('Clube recusa propostas de patrocínio', 'A diretoria considerou os valores baixos.')})
    partes = ', '.join(f'{k} {v}' for k, v in at['partes'].items())
    return [{'id': f'patr|{temporada}', 'tipo': 'patrocinio', 'sub': 'master', 'data': list(hoje), 'gravidade': 'leve',
             'envolvidos': [], 'nomes': [], 'perfil': [f'atratividade {at["indice"]}/100'],
             'titulo': 'Propostas de patrocínio master',
             'relato': f'O departamento comercial recebeu propostas para a camisa. Atratividade do clube: {at["indice"]}/100 '
                       f'({partes}). Sócios: ' + f'{at["socios"]:,}'.replace(',', '.') + '. Quanto mais exigente a meta, maior o dinheiro.',
             'opcoes': opcoes}]


def fechar_temporada(car, r, hoje):
    """Na virada da temporada: confere a meta do contrato pela tabela da liga. Devolve (delta_orcamento, notícia) ou None."""
    pat = car.get('patrocinio') or {}
    c = pat.get('contrato')
    if not c:
        return None
    temporada = hoje[0] if hoje[1] >= 7 else hoje[0] - 1
    if temporada <= c['temporada']:
        return None
    pos = (pat.get('ultima_posicao') or {}).get(str(c['temporada']))
    pat['historico'] = (pat.get('historico') or []) + [{**c, 'posicao_final': pos}]
    pat['contrato'] = None
    if pos is None:
        return 0, f'Fim do contrato com a {c["marca"]}. A posição final não pôde ser conferida; sem bônus nem multa.'
    if pos <= c['meta_pos']:
        return c['bonus'], f'Meta cumprida: {pos}º lugar. A {c["marca"]} paga bônus de {_mi(c["bonus"])}.'
    return -c['multa'], (f'Meta não cumprida ({pos}º, meta {c["meta_pos"]}º). A {c["marca"]} aciona a multa contratual: '
                         f'{_mi(c["multa"])}.')
