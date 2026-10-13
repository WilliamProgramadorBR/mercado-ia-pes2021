# Mercado IA — autor: William (https://github.com/WilliamProgramadorBR)
"""Identidade do clube do usuário para os textos (jornais, programa, notícias). Muda com a carreira (10/10/2026).

clube.definir('FLAMENGO') no começo da reunião; os textos usam clube.C['curto'], ['apelido'], ['em_estadio']...
Times sem cadastro recebem textos genéricos ("o estádio", "o CT").
"""
CONHECIDOS = {
    'MANCHESTER UNITED': dict(curto='Man Utd', apelido='United', estadio='Old Trafford', ct='Carrington',
                              em_ct='em Carrington', cidade='Manchester'),
    'FLAMENGO': dict(curto='Flamengo', apelido='Mengão', estadio='Maracanã', ct='Ninho do Urubu',
                     em_ct='no Ninho do Urubu', cidade='no Rio', voz='A Voz do Maracanã', em_estadio='no Maracanã',
                     estadio_txt='O Maracanã'),
}
C = {}


MINUSC = {'DE', 'DA', 'DO', 'DOS', 'DAS', 'E', 'Y', 'DEL', 'LA', 'EL'}   # 12/10/2026: "Atlético de Madrid"


def nome_time(nome):
    """'ATLÉTICO DE MADRID' -> 'Atlético de Madrid' (siglas curtas como 'PSV' ficam em maiúsculas)."""
    return ' '.join(p.lower() if i and p.upper() in MINUSC else p.capitalize() if len(p) > 3 else p.upper() if p.isupper() and len(p) <= 3 else p.capitalize()
                    for i, p in enumerate((nome or '').strip().split()))


def definir(nome_time_):
    nome = (nome_time_ or '').strip()
    base = CONHECIDOS.get(nome.upper())
    titulo = nome_time(nome)
    C.clear()
    C.update(base or dict(curto=titulo, apelido=titulo, estadio=None, ct=None, em_ct='no CT', cidade=None))
    C['nome'] = titulo
    # 'de' serve para nomes sem artigo (Old Trafford); quem precisa de artigo ("do Maracanã") vem no cadastro
    C.setdefault('em_estadio', f'em {C["estadio"]}' if C['estadio'] else 'no estádio')
    C.setdefault('estadio_txt', C['estadio'] or 'O estádio')
    C.setdefault('voz', f'A Voz de {C["estadio"]}' if C['estadio'] else 'A Voz da Arquibancada')
    C['voz_slogan'] = f'A voz das arquibancadas {"de " + C["cidade"] if C["cidade"] and not C["cidade"].startswith("no ") else "do " + C["curto"]}'
    C['em_cidade'] = (C['cidade'] if C['cidade'] and C['cidade'].startswith('no ') else f'em {C["cidade"]}') if C['cidade'] else 'aqui'
    return C


# 12/10/2026: clubes de nome feminino ("a Fiorentina", "da Juventus", "pela Roma") — corrige qualquer texto pronto
FEMININOS = {'ROMA', 'JUVENTUS', 'LAZIO', 'FIORENTINA', 'SAMPDORIA', 'ATALANTA', 'UDINESE', 'REAL SOCIEDAD', 'SALERNITANA',
             'CREMONESE', 'SPEZIA', 'REGGIANA', 'LUSITANA', 'PORTUGUESA', 'PONTE PRETA', 'CHAPECOENSE', 'INTERNAZIONALE',
             'ROMA FC', 'SS LAZIO', 'ACF FIORENTINA', 'JUVENTUS FC', 'AS ROMA'}
_TROCA = {'o': 'a', 'O': 'A', 'do': 'da', 'Do': 'Da', 'DO': 'DA', 'no': 'na', 'No': 'Na', 'NO': 'NA', 'ao': 'à', 'Ao': 'À',
          'AO': 'À', 'pelo': 'pela', 'Pelo': 'Pela', 'PELO': 'PELA', 'contra o': 'contra a', 'Contra o': 'Contra a'}
_RE = None


def art(nome):
    """'a' para 'Fiorentina', 'o' para 'Chelsea'."""
    return 'a' if (nome or '').strip().upper() in FEMININOS else 'o'


def concordar(txt):
    """Troca 'o Fiorentina' -> 'a Fiorentina', 'do Juventus' -> 'da Juventus', 'O ROMA' -> 'A ROMA' num texto pronto."""
    global _RE
    if not txt or not isinstance(txt, str):
        return txt
    if _RE is None:
        import re
        nomes = sorted({n for f in FEMININOS for n in (f, nome_time(f))}, key=len, reverse=True)
        _RE = re.compile(r'(?<![\w])(o|O|do|Do|DO|no|No|NO|ao|Ao|AO|pelo|Pelo|PELO)(\s+)(' + '|'.join(map(re.escape, nomes)) + r')(?![\w])')
    return _RE.sub(lambda m: _TROCA[m.group(1)] + m.group(2) + m.group(3), txt)


def titulo_nomes(x, nomes):
    """Troca os nomes de time em MAIÚSCULAS ('LIVERPOOL') pela forma de título ('Liverpool') em toda a estrutura."""
    import re
    ns = sorted({n.strip().upper() for n in nomes if n and n.strip()}, key=len, reverse=True)
    if not ns:
        return x
    rx = re.compile(r'(?<![\w])(' + '|'.join(map(re.escape, ns)) + r')(?![\w])')

    def f(v):
        if isinstance(v, str):
            resto = [ch for ch in rx.sub('', v) if ch.isalpha()]
            if resto and sum(ch.isupper() for ch in resto) / len(resto) > 0.6:
                return v   # texto todo em maiúsculas é grito de torcedor: fica como está
            return rx.sub(lambda m: nome_time(m.group(1)), v)
        if isinstance(v, list):
            return [f(y) for y in v]
        if isinstance(v, tuple):
            return tuple(f(y) for y in v)
        if isinstance(v, dict):
            return {k: f(y) for k, y in v.items()}
        return v
    return f(x)


def concordar_tudo(x):
    """concordar() em todas as strings de uma estrutura (dict/list), devolvendo uma cópia."""
    if isinstance(x, str):
        return concordar(x)
    if isinstance(x, list):
        return [concordar_tudo(v) for v in x]
    if isinstance(x, tuple):
        return tuple(concordar_tudo(v) for v in x)
    if isinstance(x, dict):
        return {k: concordar_tudo(v) for k, v in x.items()}
    return x


definir('MANCHESTER UNITED')
