# Mercado IA — autor: William (https://github.com/WilliamProgramadorBR)
"""Redator com IA (opcional) para a mídia da Central (10/10/2026).

Pega a edição da rodada (capas dos 3 jornais, programa "Bola na Mesa", perguntas da coletiva) e pede ao modelo para
REESCREVER os textos com mais variedade e personalidade, mantendo fatos, nomes, placares e números. Só texto: os
efeitos das respostas (moral, orçamento, setas) não passam pela IA.

Configuração em cerebro/ia.json (não compartilhe a chave):
  {"provedor": "gemini", "modelo": "<nome do modelo>", "chave": "<sua API key>", "ligado": true}
Sem configuração, desligado ou com erro/timeout: ficam os textos originais (nunca trava a reunião).
"""
import hashlib
import json
import os
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(HERE, 'ia.json')
CACHE = os.path.join(HERE, 'historico', 'redator_cache.json')
TIMEOUT = 75

PROMPT = """Você é a redação esportiva de um universo de futebol (Brasil, português do Brasil).
Reescreva os textos do JSON abaixo com estilo jornalístico vivo e variado, sem clichês repetidos.
Regras OBRIGATÓRIAS:
- Mantenha EXATAMENTE os mesmos fatos: nomes de jogadores e clubes, placares, números, posições, datas.
- Português do BRASIL: use elenco, time, gramado, torcida (nunca plantel, equipa, relvado, adeptos).
- Não invente resultados, lesões, transferências ou declarações que não estejam no texto.
- Respeite o tom de cada jornal: "sensacionalista" (manchete em CAIXA ALTA, exagerado), "analítico" (sóbrio, números),
  "torcedor" (paixão da arquibancada). No programa, cada comentarista mantém a personalidade indicada no papel.
- Manchetes com no máximo 70 caracteres; linhas finas e falas com no máximo 220 caracteres.
- Devolva SOMENTE o JSON, com a MESMA estrutura e as mesmas chaves, trocando apenas os valores de texto.
Clube do usuário: {clube}. Contexto da rodada: {contexto}

JSON:
{dados}"""


def config():
    try:
        with open(CONFIG, encoding='utf-8') as f:
            c = json.load(f)
        return c if c.get('ligado') and c.get('chave') and c.get('modelo') else None
    except (OSError, ValueError):
        return None


def _gemini(cfg, texto):
    url = (f'https://generativelanguage.googleapis.com/v1beta/models/{cfg["modelo"]}:generateContent'
           f'?key={cfg["chave"]}')
    corpo = {'contents': [{'parts': [{'text': texto}]}],
             'generationConfig': {'temperature': 0.9, 'responseMimeType': 'application/json'}}
    req = urllib.request.Request(url, data=json.dumps(corpo).encode('utf-8'),
                                 headers={'Content-Type': 'application/json'}, method='POST')
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        resp = json.loads(r.read().decode('utf-8'))
    return resp['candidates'][0]['content']['parts'][0]['text']


PROVEDORES = {'gemini': _gemini}


def _extrair(ed):
    """Só os textos da edição, num JSON enxuto (o que a IA pode mexer)."""
    return {
        'capas': [{'tom': c['tom'], 'manchete': c['manchete'], 'fina': c['fina'],
                   'chamadas': [{'titulo': x['titulo'], 'texto': x['texto']} for x in c['chamadas']]} for c in ed['capas']],
        'programa': [{'quem': l['quem'], 'papel': l['papel'], 'texto': l['texto']} for l in ed['programa']['linhas']],
        'coletiva': [{'reporter': p['reporter'], 'jornal': p['jornal_nome'], 'texto': p['texto']}
                     for p in (ed.get('coletiva') or {}).get('perguntas', [])],
        'analise': list((ed.get('duelo') or {}).get('analise') or []),
        'tatica': {k: list((ed.get('tatica') or {}).get(k) or []) for k in ('ataque', 'fracos_deles', 'nossos_fortes', 'nossos_fracos', 'recomendacoes')},
    }


def _confere(orig, novo):
    """A resposta tem a mesma forma? (senão descarta)"""
    try:
        if len(novo['capas']) != len(orig['capas']) or len(novo['programa']) != len(orig['programa']) or \
                len(novo['coletiva']) != len(orig['coletiva']):
            return False
        for a, b in zip(orig['capas'], novo['capas']):
            if len(a['chamadas']) != len(b['chamadas']) or not b['manchete'] or not b['fina']:
                return False
        return all(isinstance(l.get('texto'), str) and l['texto'] for l in novo['programa'] + novo['coletiva'])
    except (KeyError, TypeError):
        return False


import re
import threading

_TRAVA = threading.Lock()
_NUM = re.compile(r'\d+(?:[.,]\d+)?')


def _fiel(orig, novo):
    """Os números do texto novo têm de aparecer no original NA MESMA ORDEM (subsequência): a IA pode omitir um número,
    mas nunca trocar placar, nota ou gols (11/10/2026: ela tinha trocado a marcação 91 do De Vrij por 81)."""
    a = [x.replace(',', '.') for x in _NUM.findall(orig or '')]
    b = [x.replace(',', '.') for x in _NUM.findall(novo or '')]
    i = 0
    for x in b:
        while i < len(a) and a[i] != x:
            i += 1
        if i == len(a):
            return False
        i += 1
    return True


def _troca(orig, novo, lim):
    novo = (novo or '').strip()[:lim]
    return novo if novo and _fiel(orig, novo) else orig


def reescrever(ed, clube='', contexto='', log=print):
    """Reescreve a edição no lugar. Devolve True se a IA foi usada."""
    cfg = config()
    if not cfg:
        return False
    orig = _extrair(ed)
    chave = hashlib.sha1(json.dumps(orig, ensure_ascii=False, sort_keys=True).encode('utf-8')).hexdigest()
    try:
        with open(CACHE, encoding='utf-8') as f:
            cache = json.load(f)
    except (OSError, ValueError):
        cache = {}
    novo = cache.get(chave)
    if not novo:
        try:
            texto = PROMPT.format(clube=clube, contexto=contexto, dados=json.dumps(orig, ensure_ascii=False, indent=1))
            try:
                novo = json.loads(PROVEDORES[cfg['provedor']](cfg, texto))
            except (TimeoutError, OSError):   # instabilidade passageira: mais uma tentativa
                novo = json.loads(PROVEDORES[cfg['provedor']](cfg, texto))
        except Exception as e:  # noqa: BLE001 - IA fora do ar, chave errada, timeout: fica o texto original
            log(f'aviso: redator IA não respondeu ({type(e).__name__}: {e}); textos originais mantidos')
            return False
        if not _confere(orig, novo):
            log('aviso: redator IA devolveu formato diferente; textos originais mantidos')
            return False
        cache[chave] = novo
        cache = dict(list(cache.items())[-60:])
        os.makedirs(os.path.dirname(CACHE), exist_ok=True)
        with _TRAVA:   # 12/10/2026: as chamadas da reunião rodam em paralelo; o arquivo do cache é um só
            with open(CACHE, 'w', encoding='utf-8') as f:
                json.dump(cache, f, ensure_ascii=False)
    for c, n in zip(ed['capas'], novo['capas']):
        c['manchete'], c['fina'] = _troca(c['manchete'], n['manchete'], 90), _troca(c['fina'], n['fina'], 260)
        for x, y in zip(c['chamadas'], n['chamadas']):
            x['titulo'], x['texto'] = _troca(x['titulo'], y['titulo'], 90), _troca(x['texto'], y['texto'], 260)
    for l, n in zip(ed['programa']['linhas'], novo['programa']):
        l['texto'] = _troca(l['texto'], n['texto'], 300)
    for p, n in zip((ed.get('coletiva') or {}).get('perguntas', []), novo['coletiva']):
        p['texto'] = _troca(p['texto'], n['texto'], 300)
    nt, ot = novo.get('tatica') or {}, ed.get('tatica')
    if ot:
        for k in ('ataque', 'fracos_deles', 'nossos_fortes', 'nossos_fracos', 'recomendacoes'):
            if isinstance(nt.get(k), list) and len(nt[k]) == len(ot.get(k) or []):
                ot[k] = [_troca(o, str(x), 300) for o, x in zip(ot[k], nt[k])]
    an = novo.get('analise')
    if ed.get('duelo') and isinstance(an, list) and len(an) == len(ed['duelo'].get('analise') or []):
        ed['duelo']['analise'] = [_troca(o, str(x), 320) for o, x in zip(ed['duelo']['analise'], an)]
    ed['redator'] = cfg['provedor']
    return True


# ---------------------------------------------------------------- matérias da imprensa (imprensa.py, 11/10/2026)
ESTILOS = {
    'pos_jogo': 'noticiário pós-jogo de TV/jornal: narra o jogo e destaca as atuações por setor (ataque, meio, defesa) '
                'com as estatísticas; pode avaliar o esquema tático com base no texto',
    'pre_jogo': 'prévia de jornal: clima de expectativa, prováveis escalações, favoritismo pelos números',
    'jogo_da_rodada': 'coluna de TORCEDOR apaixonado comparando os craques, tom de resenha de bar, provocativo e '
                      'divertido, mas sempre usando os números dados',
    'temporada': 'coluna de análise sobre a temporada: campanha, metas, momento, destaques',
    'mercado': 'coluna de bastidores do mercado da bola: quem reforçou quem e o que isso muda',
    'premios': 'reportagem especial de fim de temporada sobre a votação dos jornalistas (seleção ideal, artilheiro, '
               'revelação): tom de premiação, solene e com orgulho de quem entrou',
    'rodada': 'coluna da rodada/do mês: seleção ideal pelas notas, craque, prêmio do mês; tom de resenha esportiva de segunda-feira',
    'selecoes': 'reportagem de Data FIFA: convocados, quem jogou pela seleção, quem foi esquecido, o desgaste na volta ao clube',
    'revelacao': 'perfil jornalístico de um jogador que surpreendeu o mundo ("quem é ele?"): tom de descoberta, '
                 'contraste entre o pouco que se esperava e os números que ele tem',
}

PROMPT_MATERIAS = """Você é a redação esportiva de um universo de futebol (português do Brasil).
Reescreva cada matéria do JSON abaixo como texto jornalístico de verdade, com fluidez e personalidade, no ESTILO indicado.
Regras OBRIGATÓRIAS:
- Cada parágrafo novo corresponde ao parágrafo de mesmo índice: mesma quantidade de parágrafos.
- Use SOMENTE os fatos do próprio parágrafo: nomes, clubes, placares, notas, estatísticas e datas. Não invente
  lances, minutos de gols, lesões, cartões, declarações nem números que não estejam no parágrafo.
- Todo número que você escrever tem de aparecer no parágrafo original (pode omitir números, nunca trocar).
- Português do BRASIL (elenco, time, gramado, torcida; nunca plantel, equipa, relvado, adeptos).
- Título com no máximo 80 caracteres; linha fina com no máximo 160; parágrafos com no máximo 520 caracteres.
- Devolva SOMENTE o JSON: {{"materias": [{{"id": ..., "titulo": ..., "linha_fina": ..., "paragrafos": [...]}}]}}.
Clube do usuário: {clube}

JSON:
{dados}"""


def _fiel_conj(orig, novo):
    """Cada número do texto novo existe no original (contando repetições). A ordem pode mudar (texto reescrito)."""
    from collections import Counter
    a = Counter(x.replace(',', '.') for x in _NUM.findall(orig or ''))
    b = Counter(x.replace(',', '.') for x in _NUM.findall(novo or ''))
    return all(a[k] >= v for k, v in b.items())


def _troca_livre(orig, novo, lim):
    novo = (novo or '').strip()
    return novo if novo and len(novo) <= lim and _fiel_conj(orig, novo) else orig


def reescrever_materias(materias, clube='', log=print):
    """Reescreve as matérias no lugar (uma chamada para todas). Marca m['ia'] = True nas que mudaram."""
    cfg = config()
    if not cfg or not materias:
        return False
    orig = {'materias': [{'id': i, 'estilo': m.get('estilo') or ESTILOS.get(m['frente'], ''), 'titulo': m['titulo'],   # 12/10: estilo do veículo
                          'linha_fina': m.get('linha_fina') or '', 'paragrafos': list(m['corpo'])}
                         for i, m in enumerate(materias)]}
    chave = 'mat|' + hashlib.sha1(json.dumps(orig, ensure_ascii=False, sort_keys=True).encode('utf-8')).hexdigest()
    try:
        with open(CACHE, encoding='utf-8') as f:
            cache = json.load(f)
    except (OSError, ValueError):
        cache = {}
    novo = cache.get(chave)
    if not novo:
        texto = PROMPT_MATERIAS.format(clube=clube, dados=json.dumps(orig, ensure_ascii=False, indent=1))
        try:
            try:
                novo = json.loads(PROVEDORES[cfg['provedor']](cfg, texto))
            except (TimeoutError, OSError):
                novo = json.loads(PROVEDORES[cfg['provedor']](cfg, texto))
        except Exception as e:  # noqa: BLE001
            log(f'aviso: redator IA (matérias) não respondeu ({type(e).__name__}: {e}); textos originais mantidos')
            return False
        cache[chave] = novo
        cache = dict(list(cache.items())[-60:])
        os.makedirs(os.path.dirname(CACHE), exist_ok=True)
        with _TRAVA:   # 12/10/2026: as chamadas da reunião rodam em paralelo; o arquivo do cache é um só
            with open(CACHE, 'w', encoding='utf-8') as f:
                json.dump(cache, f, ensure_ascii=False)
    por_id = {x.get('id'): x for x in (novo.get('materias') or []) if isinstance(x, dict)}
    usadas = 0
    for i, m in enumerate(materias):
        n = por_id.get(i)
        if not n or not isinstance(n.get('paragrafos'), list) or len(n['paragrafos']) != len(m['corpo']):
            continue
        corpo = [_troca_livre(o, str(x), 560) for o, x in zip(m['corpo'], n['paragrafos'])]
        trocados = sum(a != b for a, b in zip(corpo, m['corpo']))
        m['corpo'] = corpo
        m['titulo'] = _troca_livre(m['titulo'], n.get('titulo'), 90)
        m['linha_fina'] = _troca_livre(m.get('linha_fina') or '', n.get('linha_fina'), 180)
        if trocados:
            m['ia'] = True
            usadas += 1
    return usadas > 0


# ---------------------------------------------------------------- Bola na Mesa + redes (bola_na_mesa.py, 11/10/2026)
PROMPT_FALAS = """Você é o roteirista de um programa esportivo de TV brasileiro em formato de mesa-redonda, e também
escreve os posts de torcedores e perfis de futebol nas redes sociais.
Reescreva cada item do JSON abaixo como fala natural de TV (ou post de rede social), respeitando a PERSONALIDADE de quem fala:
{pessoas}
Regras OBRIGATÓRIAS:
- Mesmo id, mesma ordem, mesma quantidade de itens. Cada item continua com o MESMO assunto e as mesmas pessoas/clubes citados.
- Todo número que você escrever tem de aparecer no texto original do item (pode omitir, nunca trocar nem inventar).
  Não escreva números por extenso ("nota dez", "três gols") que não estejam no original.
- Cada número mantém o SIGNIFICADO original (probabilidade continua probabilidade de vitória/empate/derrota; nota é nota).
- Não invente fatos (lesões, gols, cartões, transferências, declarações de jogadores).
- Zoeira e cobrança são bem-vindas, mas sem ofensa pessoal, preconceito ou palavrão.
- Português do BRASIL coloquial de TV esportiva. Falas com no máximo 300 caracteres; posts com no máximo 220 (pode usar emoji e gíria).
- Devolva SOMENTE o JSON: {{"itens": [{{"id": ..., "texto": ...}}]}}.
Clube em foco: {clube}

JSON:
{dados}"""


def reescrever_falas(ep, clube='', log=print):
    """Reescreve as falas do programa e os posts no lugar (uma chamada). True se a IA trocou algum texto."""
    cfg = config()
    if not cfg:
        return False
    import bola_na_mesa as bnm
    alvos = []   # (dicionário, limite)
    itens = []
    for b in ep['blocos']:
        for f in b['falas']:
            itens.append({'id': len(itens), 'quem': bnm.PESSOAS[f['quem']][0], 'tipo': 'fala', 'pauta': b['titulo'], 'texto': f['texto']})
            alvos.append((f, 320))
    for p in ep['posts']:
        itens.append({'id': len(itens), 'quem': p['autor'], 'tipo': 'post', 'texto': p['texto']})
        alvos.append((p, 240))
    pessoas = '\n'.join(f'- {bnm.PESSOAS[q][0]}: {e}' for q, e in bnm.ESTILO_PESSOA.items()) + \
        '\n- posts (@perfis): torcedor apaixonado, perfil de zoeira, perfil de números, setorista, perfil de mercado'
    orig = {'itens': itens}
    chave = 'bnm|' + hashlib.sha1(json.dumps(orig, ensure_ascii=False, sort_keys=True).encode('utf-8')).hexdigest()
    try:
        with open(CACHE, encoding='utf-8') as f:
            cache = json.load(f)
    except (OSError, ValueError):
        cache = {}
    novo = cache.get(chave)
    if not novo:
        texto = PROMPT_FALAS.format(pessoas=pessoas, clube=clube, dados=json.dumps(orig, ensure_ascii=False, indent=1))
        try:
            try:
                novo = json.loads(PROVEDORES[cfg['provedor']](cfg, texto))
            except (TimeoutError, OSError):
                novo = json.loads(PROVEDORES[cfg['provedor']](cfg, texto))
        except Exception as e:  # noqa: BLE001
            log(f'aviso: redator IA (Bola na Mesa) não respondeu ({type(e).__name__}: {e}); textos originais mantidos')
            return False
        cache[chave] = novo
        cache = dict(list(cache.items())[-60:])
        os.makedirs(os.path.dirname(CACHE), exist_ok=True)
        with _TRAVA:   # 12/10/2026: as chamadas da reunião rodam em paralelo; o arquivo do cache é um só
            with open(CACHE, 'w', encoding='utf-8') as f:
                json.dump(cache, f, ensure_ascii=False)
    por_id = {x.get('id'): x for x in (novo.get('itens') or []) if isinstance(x, dict)}
    trocas = 0
    for i, (alvo, lim) in enumerate(alvos):
        n = por_id.get(i)
        if not n:
            continue
        t = _troca_livre(alvo['texto'], str(n.get('texto') or ''), lim)
        trocas += t != alvo['texto']
        alvo['texto'] = t
    return trocas > 0


if __name__ == '__main__':
    # teste rápido da chave/modelo: python redator.py
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    cfg = config()
    if not cfg:
        print('ia.json ausente, desligado ou sem chave/modelo. Veja ia.json.exemplo.')
        sys.exit(1)
    try:
        r = PROVEDORES[cfg['provedor']](cfg, 'Responda só com o JSON {"ok": true, "frase": "<uma manchete curta de futebol em português>"}')
        print('IA respondeu:', r)
    except Exception as e:  # noqa: BLE001
        print('falhou:', type(e).__name__, e)
