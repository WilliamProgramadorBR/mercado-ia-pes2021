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


def definir(nome_time):
    nome = (nome_time or '').strip()
    base = CONHECIDOS.get(nome.upper())
    MINUSC = {'DE', 'DA', 'DO', 'DOS', 'DAS', 'E', 'Y', 'DEL', 'LA', 'EL'}   # 12/10/2026: "Atlético de Madrid"
    titulo = ' '.join(p.lower() if i and p.upper() in MINUSC else p.capitalize() if len(p) > 3 else p.upper() if p.isupper() and len(p) <= 3 else p.capitalize()
                      for i, p in enumerate(nome.split()))
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


definir('MANCHESTER UNITED')
