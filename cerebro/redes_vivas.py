# Mercado IA — autor: William (https://github.com/WilliamProgramadorBR)
"""REDES VIVAS (12/10/2026): o feed acompanha o MOMENTO e ganha formatos novos.

Pedido do usuário: "na rede social dá um up também, crie mais textos, formas de interagir, deixa algo bem dinâmico...
que dê a sensação de algo novo toda hora que ver a Central". O que entra aqui:
  1. modelos novos (mesmo formato do redes_falas: categoria, autor, texto, tom) que só aparecem quando o momento
     sustenta: sequência de derrotas, crise, reação, invencibilidade, liderança perdida/conquistada, rival que encostou
     ou disparou, semana decisiva, lesão e volta do craque, a leitura dos analistas (Mesa Tática, Plantão do Esporte,
     Resenha Raiz), o técnico rival e o plano que ele deve usar;
  2. formatos: conta oficial do clube, perfis dos jogadores (verificados), thread de análise em partes, post que cita
     outro post, "Em alta" (assuntos do momento com nº de posts);
  3. comentários por assunto (além dos por tom);
  4. o feed "acontece" com o tempo: cada post ganha um atraso em minutos e a Central vai revelando os posts e
     somando curtidas desde a primeira vez que a edição é aberta.
"""
import datetime as dt
import json
import os

EXT = {2: 'duas', 3: 'três', 4: 'quatro', 5: 'cinco', 6: 'seis', 7: 'sete', 8: 'oito'}
ORD = {2: 'segunda', 3: 'terceira', 4: 'quarta', 5: 'quinta', 6: 'sexta'}
VEICULOS = {'@mesatatica', '@plantaodoesporte', '@resenharaiz'}

MODELOS = [
    # ----- sequência de derrotas (pós-jogo)
    ('seq_derrotas', '{torc}', '{n_d_cap} derrotas seguidas. Não é fase, é alerta. Alguém acorda esse time! 😤', 'neg'),
    ('seq_derrotas', '@numerosdabola', '{nos} nos últimos jogos: {forma}. As {n_d_ext} derrotas seguidas acendem a luz amarela. 📉', 'num'),
    ('seq_derrotas', '@secadorprofissional', 'Mais uma do {nos} kkkkk {n_d_ext} seguidas, tá lindo de ver 😂', 'hate'),
    ('seq_derrotas', '@zoeira_fc', 'Torcedor do {nos} abrindo o app depois da {n_d_ord} derrota seguida: 🙈', 'meme'),
    ('seq_derrotas', '@tiozao_do_futebol', 'Sequência ruim se quebra no treino de amanhã, não em coletiva. No meu tempo era assim.', 'neu'),
    ('seq_derrotas', '@vozdageral', 'Saída do estádio hoje: ninguém falava nada. Só se ouvia o barulho das catracas.', 'neg'),
    ('seq_derrotas', '{torc}', 'Calma, gente. Time grande também perde {n_d_ext} seguidos. O que não pode é entregar a temporada. 🙏', 'neu'),
    ('seq_derrotas', '@memesdabola', 'O {nos} depois de {n_d_ext} derrotas seguidas tentando lembrar como se ganha um jogo: 🤔📖', 'meme'),
    ('seq_derrotas', '@futebol_raiz', 'Não é o fim do mundo, mas é o fim da desculpa. O {nos} precisa reagir já.', 'neg'),
    ('seq_derrotas', '@arquibancada_{sigla}', 'Quem é {apelido} de verdade aparece agora, na fase ruim. Ninguém solta a mão! 🤝', 'pos'),
    # ----- crise
    ('crise', '{torc}', 'CHEGA! {sv} jogos sem vencer. Quero explicação da diretoria E do técnico. 😡', 'neg'),
    ('crise', '@antigoat_fc', 'Fim de ciclo. Esse elenco já deu o que tinha que dar. 🙄', 'hate'),
    ('crise', '@setorista_beto', 'Clima pesado no CT hoje: treino fechado e conversa longa do técnico com o elenco no gramado. 👀', 'neu'),
    ('crise', '@futebol_raiz', 'Crise se resolve com trabalho e silêncio. Barulho de fora não ganha jogo.', 'neu'),
    ('crise', '@memesdabola', 'O {nos} procurando a última vitória: 🔍🔍🔍', 'meme'),
    ('crise', '@resenha_fc', 'Quem é o maior culpado pela fase do {nos}? Técnico, elenco ou diretoria? 👇', 'neu'),
    # ----- reação
    ('reacao', '{torc}', 'VOLTAMOS!!! Acabou a seca, agora é emendar uma sequência! 🔥', 'pos'),
    ('reacao', '@futebol_raiz', 'Time grande se mede pela reação. Depois de duas derrotas, o {nos} respondeu em campo.', 'pos'),
    ('reacao', '@secadorprofissional', 'Ganhou do {adv} e já acha que voltou. Tá bom, campeão 🙄', 'hate'),
    ('reacao', '@numerosdabola', 'Fim da sequência negativa: {nos} {gp} x {gc} {adv}. 📈', 'num'),
    # ----- invencibilidade
    ('invicto', '@numerosdabola', '{inv} jogos sem perder para o {nos}. 📊🧱', 'num'),
    ('invicto', '{torc}', '{inv} jogos sem perder!!! Esse time não sabe o que é derrota! 🔥', 'pos'),
    ('invicto', '@zoeira_fc', 'Os adversários do {nos} tentando lembrar a última vez que ganharam deles: 🤔', 'meme'),
    ('invicto', '@antigoat_fc', 'Invencibilidade contra quem? Quero ver quando pegar time de verdade 🙄', 'hate'),
    # ----- a tabela
    ('perdeu_lider', '@{rival_slug}_raiz', 'LÍDER É O {rival_up}!!! Pode chorar, {nos}! 🔝😤', 'riv'),
    ('perdeu_lider', '@numerosdabola', 'Troca na ponta da {liga}: o {rival} passou o {nos}. Eram {dif_antes} pontos de vantagem duas rodadas atrás. 📊', 'num'),
    ('perdeu_lider', '{torc}', 'Perder a liderança pro {rival} dói demais. Mas a gente pega de volta. 💪', 'neg'),
    ('perdeu_lider', '@zoeira_fc', 'O {nos} dormiu líder e acordou olhando o {rival} de baixo 😬', 'meme'),
    ('perdeu_lider', '@secadorprofissional', 'A liderança do {nos} durou menos que promessa de campanha 😂', 'hate'),
    ('perdeu_lider', '@tiozao_do_futebol', 'Liderança em {mes} não ganha título. Mas perder a ponta assim, tropeçando, preocupa.', 'neu'),
    ('assumiu_lider', '{torc}', 'LÍDER!!! O {nos_up} É LÍDER!!! 🔝🔥', 'pos'),
    ('assumiu_lider', '@{rival_slug}_raiz', 'Liderança emprestada. Daqui a pouco a gente pega de volta 😤', 'riv'),
    ('assumiu_lider', '@numerosdabola', 'Novo líder da {liga}: {nos}. 📊', 'num'),
    ('rival_encostou', '@numerosdabola', 'A vantagem do {nos} sobre o {rival} caiu de {dif_antes} para {dif_pts} em duas rodadas. 📉', 'num'),
    ('rival_encostou', '@{rival_slug}_raiz', 'Tá chegando a hora, {nos}... 👀 {dif_pontinhos}', 'riv'),
    ('rival_encostou', '{torc}', 'O {rival} tá na cola e o time dormindo. ACORDA!!! ⏰', 'neg'),
    ('rival_encostou', '@tiozao_do_futebol', 'Quem lidera não deve olhar o retrovisor. Mas que o {rival} está grande no espelho, está.', 'neu'),
    ('rival_disparou', '@numerosdabola', 'O {rival} abriu {dif_pts} sobre o {nos}. Eram {dif_antes} duas rodadas atrás. 📊', 'num'),
    ('rival_disparou', '{torc}', 'Ainda dá, mas desse jeito não. O {rival} não perde mais! 😩', 'neg'),
    ('rival_disparou', '@{rival_slug}_raiz', 'Tchau, {nos}! Acena pra gente aí de baixo 👋😂', 'riv'),
    # ----- a semana decisiva
    ('semana', '{torc}', 'Semana que vale a temporada: {jogo1} e {jogo2}. Coração não aguenta! 😰🔥', 'pos'),
    ('semana', '@resenha_fc', '{jogo1_curto} e {jogo2_curto} em {gap} dias. Quem você pouparia? 👇', 'neu'),
    ('semana', '@tatica_pura', 'Semana de gestão: poupar na {comp1}? Arriscar no {comp2}? O técnico do {nos} tem uma decisão difícil.', 'neu'),
    ('semana', '@setorista_beto', 'Departamento físico em alerta máximo: {jogo1_curto} e {jogo2_curto} em {gap} dias. 👀', 'neu'),
    ('semana', '@zoeira_fc', 'Torcedor do {nos} nessa semana: 💊💊💊 (remédio pra pressão)', 'meme'),
    # ----- departamento médico
    ('lesao', '@setorista_beto', 'Boletim: {lesionado} segue no departamento médico e deve ser desfalque{les_grande_txt}. 🏥', 'neu'),
    ('lesao', '{torc}', 'Volta logo, {lesionado}! O time sente sua falta 🙏💔', 'pos'),
    ('lesao', '@numerosdabola', 'Sem {lesionado}, o {nos} perde o autor de {les_parte}% dos gols da temporada. 📉', 'num'),
    ('lesao', '@zoeira_fc', 'Torcedor do {nos} ligando pro departamento médico de 5 em 5 minutos pra saber do {lesionado}: 📞', 'meme'),
    ('lesao', '@secadorprofissional', 'Sem o {lesionado} o {nos} é time comum. Agora a gente vai ver 😏', 'hate'),
    ('lesao', '@tatica_pura', 'Sem {lesionado}, o {nos} precisa mudar a referência do ataque. Quem assume esse papel?', 'neu'),
    ('volta', '{torc}', '{volta_up} DE VOLTA!!! Agora sim! 🔥', 'pos'),
    ('volta', '@setorista_beto', '{volta} treinou normalmente com o grupo e está liberado pelo departamento médico. 👀', 'neu'),
    ('volta', '@memesdabola', 'Os zagueiros da liga vendo que o {volta} voltou: 😰', 'meme'),
    # ----- a leitura dos analistas (pós-jogo)
    ('analise', '@mesatatica', 'Na prancheta: {porque1}', 'neu'),
    ('analise', '@plantaodoesporte', '{placar_txt}. {porque1}', 'neu'),
    ('analise', '@resenharaiz', 'Explicando pra galera: {porque1_min} {emoji_res}', 'meme'),
    ('analise2', '@mesatatica', 'Outro ponto que explica o jogo: {porque2}', 'neu'),
    ('analise2', '@tatica_pura', 'Concordo com a Mesa Tática, mas tem mais: {porque2_min}', 'neu'),
    ('marcacao', '@tatica_pura', 'Viram a marcação individual em cima do {marcado_ult}? O {adv} colou um homem nele o jogo todo.', 'neu'),
    ('marcacao', '@zoeira_fc', 'O marcador do {adv} seguiu o {marcado_ult} até no vestiário 😂', 'meme'),
    # ----- o próximo adversário (pré-jogo)
    ('tec_rival', '@tatica_pura', 'Pelo que o {prox} vem mostrando, o {tec_rival} deve {jeito_rival}. O {nos} precisa estar pronto para isso.', 'neu'),
    ('tec_rival', '@mesatatica', 'Prévia tática: o {prox} do {tec_rival} deve {jeito_rival}.', 'neu'),
    ('marcacao_prev', '@setorista_beto', 'Informação de bastidor: o {prox} treinou marcação individual. O alvo seria o {marcado}. 👀', 'neu'),
    ('marcacao_prev', '@zoeira_fc', 'O {prox} vai colar um marcador no {marcado}. Coitado do marcador 😂', 'meme'),
    ('pressao_rival', '@{prox_slug}_raiz', 'Pegamos o {nos} na hora certa. Tá todo mundo nervoso lá 😏', 'riv'),
    ('pressao_rival', '@secadorprofissional', 'Contra o {prox} vai ser a {n_d_prox} seguida, anota aí 😈', 'hate'),
]

PESO = {'seq_derrotas': 4.2, 'crise': 4, 'reacao': 3.5, 'invicto': 2.2, 'perdeu_lider': 4.2, 'assumiu_lider': 3.8,
        'rival_encostou': 3.2, 'rival_disparou': 3, 'semana': 3.4, 'lesao': 3.4, 'volta': 3, 'analise': 3.6, 'analise2': 2.2,
        'marcacao': 2.8, 'tec_rival': 2.8, 'marcacao_prev': 2.6, 'pressao_rival': 2.4}

RESP_CAT = {
    'seq_derrotas': ['Duas seguidas não é o fim do mundo', 'Tá na hora de mexer no time', 'Eu avisei que ia dar ruim', 'Confio no grupo, vai virar 🙏',
                     'Treino dobrado já!', 'Ano passado também teve fase ruim e a gente ganhou tudo'],
    'crise': ['Fora todo mundo', 'Respeita a história do clube', 'Paciência tem limite', 'Acredito na virada', 'Diretoria calada como sempre'],
    'perdeu_lider': ['Liderança se recupera no confronto direto 😤', 'Ainda tem muito campeonato', 'Dói, mas o campeonato é longo',
                     'Chora não, a gente volta', 'Eles vão tropeçar, anota'],
    'rival_encostou': ['Nada de olhar pro lado', 'Tá ficando perigoso', 'Esse rival não perde mais?', 'Calma, ainda estamos na frente'],
    'lesao': ['Força, guerreiro 🙏', 'Volta logo, craque', 'Sem ele o time é outro 😔', 'Hora do reserva mostrar serviço', 'Melhoras! ❤️'],
    'volta': ['Agora vai! 🔥', 'Que falta ele fez', 'Sem pressa, volta com calma', 'O craque voltou!'],
    'semana': ['Coração não aguenta', 'Vai ser semana de unha roída', 'Poupa na copa!', 'Nada de poupar, é jogar com tudo!', 'Semana que define a temporada'],
    'analise': ['Análise perfeita 👏', 'Finalmente alguém explicou', 'Discordo, o problema foi outro', 'Mandem isso pro técnico', 'Melhor análise que vi hoje'],
    'oficial': ['Vamos, {apelido}! 🔥', 'Seguimos juntos!', 'Bora reagir!', 'Lotar o estádio no próximo!', 'Cadê a reação?'],
    'jogador': ['Juntos! ❤️', 'Confio em você', 'É isso! 👏', 'Volta mais forte', 'Monstro!', 'Representa!'],
    'tec_rival': ['Vai ser jogo duro', 'Nosso técnico vai saber responder', 'Esse técnico é bom demais', 'Se vier assim, a gente castiga'],
}


def _slug(t):
    import unicodedata
    t = unicodedata.normalize('NFKD', t or '').encode('ascii', 'ignore').decode().lower()
    return ''.join(ch for ch in t if ch.isalnum())[:20]


def _handle(nome):
    """Perfil 'oficial' de um jogador: @williamoficial, @kylewalker."""
    s = _slug(nome)
    return '@' + (s + 'oficial' if len(s) <= 8 else s)


def _dias(a, b):
    return (dt.date(*tuple(a)[:3]) - dt.date(*tuple(b)[:3])).days


def _ia_reg(adv, data):
    try:
        reg = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'historico', 'ia_adversaria.json'),
                             encoding='utf-8')).get('registro') or []
    except (OSError, ValueError):
        return None
    up = lambda s: (s or '').strip().upper()
    return next((x for x in reversed(reg) if up(x.get('adversario')) == up(adv) and list(x.get('data') or []) == list(data or [])), None)


def _jeito(pl):
    if not pl:
        return None
    if pl.get('linha_defensiva', 5) <= 4:
        return 'se fechar atrás e apostar no contra-ataque'
    if pl.get('estilo_defensivo') == 0 and pl.get('pressao') == 0 and pl.get('linha_defensiva', 5) >= 6:
        return 'pressionar alto desde a saída de bola'
    if pl.get('estilo_ofensivo') == 1:
        return 'ficar com a bola e rodar o jogo'
    return 'esperar o erro e sair rápido no contra-ataque'


def contexto(M, fase, c, cats):
    """Completa os campos/categorias do redes_falas.contexto com o momento, a lesão, a análise e o próximo rival."""
    import momento as _mo
    hoje = tuple(M['hoje'])
    mo = M.get('momento') or {}
    u = M.get('ult') or {}
    pos_ok = fase != 'pre' and u.get('recente')
    # o momento só vale para o pós-jogo se foi calculado DEPOIS do último jogo (a edição ao vivo chega antes da reunião)
    mo_atual = bool(mo) and (not u or not mo.get('ultimo') or list(mo['ultimo']['data']) == list(u['p']['data']))
    c['mes'] = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro',
                'novembro', 'dezembro'][hoje[1] - 1]
    if mo and mo_atual:
        s = mo.get('seq') or {}
        forma = mo.get('forma') or ''
        c['forma'] = ' '.join(forma)
        if pos_ok and s.get('d', 0) >= 2:
            c.update(n_d=s['d'], n_d_ext=EXT.get(s['d'], str(s['d'])), n_d_cap=EXT.get(s['d'], str(s['d'])).capitalize(),
                     n_d_ord=ORD.get(s['d'], f'{s["d"]}ª'))
            cats.add('seq_derrotas')
        if s.get('d', 0) >= 3 or s.get('sv', 0) >= 4:
            c['sv'] = s['sv']
            cats.add('crise')
        if pos_ok and forma.endswith('V') and forma[:-1].endswith('DD'):
            cats.add('reacao')
        if s.get('inv', 0) >= 8:
            c['inv'] = s['inv']
            cats.add('invicto')
        L = mo.get('liga') or {}
        rv = L.get('rival') or {}
        if rv:
            d1 = abs(rv['dif'])
            c.update(rival=rv['nome'], rival_up=rv['nome'].upper(), rival_slug=_slug(rv['nome']), dif=d1,
                     dif_antes=abs(rv['dif_antes']), liga=L.get('nome') or 'liga', dif_pts=f'{d1} ponto' + ('' if d1 == 1 else 's'),
                     dif_pontinhos='1 pontinho' if d1 == 1 else f'{d1} pontinhos')
            if L.get('lideranca') == 'perdeu':
                cats.add('perdeu_lider')
            elif L.get('lideranca') == 'assumiu':
                cats.add('assumiu_lider')
            if rv.get('movimento') == 'encostou' and rv['dif'] > 0:
                cats.add('rival_encostou')
            elif rv.get('movimento') == 'disparou':
                cats.add('rival_disparou')
    # a semana decisiva (vale no pré e no pós): só jogos que ainda não aconteceram
    gs = [dict(x, dias=_dias(x['data'], hoje)) for x in (mo.get('proximos') or []) if x['tags'] and 0 <= _dias(x['data'], hoje) <= 10]
    if len(gs) >= 2:
        a, b = gs[0], gs[1]
        c.update(jogo1=_mo.descreve_jogo(a), jogo2=_mo.descreve_jogo(b), jogo1_curto=a['adv'], jogo2_curto=b['adv'],
                 comp1=a['comp'].replace('UEFA ', ''), comp2=b['classico'] or b['comp'].replace('UEFA ', ''), gap=max(1, b['dias'] - a['dias']))
        cats.add('semana')
    # departamento médico
    les, vol = M.get('lesao'), M.get('lesao_volta')
    voltou = vol and les and vol.get('nome') == les.get('nome') and tuple(vol['data']) >= tuple(les['data'])
    if les and not voltou and 0 <= _dias(hoje, les['data']) <= 10:
        g = (les.get('grandes') or [None])[0]
        c.update(lesionado=les['nome'], les_parte=les.get('parte_gols', 0), les_slug=_slug(les['nome']),
                 les_grande_txt=(f' no {g["classico"]}' if g and g.get('classico') else f' contra o {g["adv"]}' if g else ''))
        cats.add('lesao')
    if vol and 0 <= _dias(hoje, vol['data']) <= 7:
        c.update(volta=vol['nome'], volta_up=vol['nome'].upper())
        cats.add('volta')
    # a análise do último jogo (só se é deste jogo)
    an = [a for a in M.get('analise') or [] if a['chave'] not in ('corrida', 'momento')]
    if pos_ok and an and list(M.get('analise_data') or []) == list(u['p']['data']):
        t0 = an[0]['texto']
        c.update(porque1=t0, porque1_min=t0[0].lower() + t0[1:], placar_txt=f'{c["nos"]} {u["gp"]} x {u["gc"]} {u["adv"]}',
                 emoji_res={'V': '🔥', 'E': '😐', 'D': '😬'}['V' if u['gp'] > u['gc'] else 'E' if u['gp'] == u['gc'] else 'D'])
        cats.add('analise')
        if len(an) > 1:
            c.update(porque2=an[1]['texto'], porque2_min=an[1]['texto'][0].lower() + an[1]['texto'][1:])
            cats.add('analise2')
        reg = _ia_reg(u['adv'], u['p']['data'])
        marc = next((i[len('Marcação ('):-1] for i in (reg or {}).get('instrucoes') or [] if i.startswith('Marcação (')), None)
        if marc and any(j['nome'] == marc and j['min'] >= 45 for j in u.get('nos') or []):
            c['marcado_ult'] = marc
            cats.add('marcacao')
    # o próximo adversário: o plano que a IA preparou (técnico, jeito de jogar, marcação)
    pj = M.get('pj') or {}
    if fase == 'pre' and c.get('prox') and pj.get('data'):
        reg = _ia_reg(pj.get('adversario') or c['prox'], pj['data'])
        if reg and reg.get('tecnico'):
            j = _jeito(reg.get('plano'))
            if j:
                c.update(tec_rival=reg['tecnico'], jeito_rival=j)
                cats.add('tec_rival')
            marc = next((i[len('Marcação ('):-1] for i in reg.get('instrucoes') or [] if i.startswith('Marcação (')), None)
            if marc:
                c['marcado'] = marc
                cats.add('marcacao_prev')
        s = (mo.get('seq') or {}) if mo_atual else {}
        if s.get('d', 0) >= 2:
            c['n_d_prox'] = ORD.get(s['d'] + 1, f'{s["d"] + 1}ª')
            cats.add('pressao_rival')
    return c, cats


# ---------------------------------------------------------------- formatos especiais
def especiais(M, fase, rnd, c, cats):
    """Posts com formato próprio: conta oficial, jogadores, thread de análise. [{'autor','texto','pauta','tom',...}]"""
    out = []
    of = f'@{c["sigla"]}_oficial'
    u = M.get('ult') or {}
    pos_ok = fase != 'pre' and u.get('recente')
    nos = c['nos']
    if pos_ok:
        res = 'V' if u['gp'] > u['gc'] else 'E' if u['gp'] == u['gc'] else 'D'
        txt = f'FIM DE JOGO | {nos} {u["gp"]} x {u["gc"]} {u["adv"]}'
        txt += {'V': ' 🔥 Que vitória!', 'E': '. Seguimos.', 'D': '. Cabeça erguida, o próximo jogo já começou.'}[res]
        if 'seq_derrotas' in cats:
            txt = f'FIM DE JOGO | {nos} {u["gp"]} x {u["gc"]} {u["adv"]}. Momento difícil, e é agora que a gente se une. Juntos até o fim. 🤝'
        out.append({'autor': of, 'texto': txt, 'pauta': 'redes|oficial', 'tom': 'neu', 'verificado': True, 'tipo': 'oficial'})
        nota = [j for j in u.get('nos') or [] if j['nota']]
        top = max(nota, key=lambda j: j['nota'] + 0.6 * j['gols'], default=None)
        if top and res == 'V':
            out.append({'autor': _handle(top['nome']), 'nome_exibicao': top['nome'], 'verificado': True, 'tipo': 'jogador', 'pauta': 'redes|jogador', 'tom': 'pos',
                        'texto': rnd.choice(['Que noite! Obrigado, torcida, vocês são demais 🙌⚽', 'Três pontos e muito trabalho. Seguimos! 💪',
                                             'Noite especial. Obrigado a todos pelo apoio! ❤️'])})
        g = max(u.get('nos') or [], key=lambda j: j['gols'], default=None)
        if g and g['gols'] and (not top or g['nome'] != top['nome'] or res != 'V'):
            out.append({'autor': _handle(g['nome']), 'nome_exibicao': g['nome'], 'verificado': True, 'tipo': 'jogador', 'pauta': 'redes|jogador',
                        'tom': 'pos' if res == 'V' else 'neu',
                        'texto': 'Gol pra vocês! ⚽❤️' if res == 'V' else 'O gol não valeu de nada sem a vitória. Vamos trabalhar. 💪'})
        cap = next((j for j in M.get('J') or [] if j.get('capitao')), None)
        if cap and res == 'D':
            txt = ('Momento difícil, mas é agora que se vê quem é quem. Ninguém solta a mão de ninguém. 🤝' if 'seq_derrotas' in cats
                   else 'Não foi o resultado que queríamos. A gente sabe o que precisa melhorar. Juntos! 💪')
            out.append({'autor': _handle(cap['nome']), 'nome_exibicao': cap['nome'], 'verificado': True, 'tipo': 'jogador',
                        'pauta': 'redes|jogador', 'tom': 'neu', 'texto': txt})
        if 'analise' in cats and c.get('porque2'):   # thread em partes
            partes = [c['porque2']] + ([f'Pela frente: {c["jogo1"]} e {c["jogo2"]}. Pouco tempo para corrigir.'] if 'semana' in cats else [])
            out.append({'autor': '@mesatatica', 'verificado': True, 'tipo': 'thread', 'pauta': 'redes|analise', 'tom': 'neu',
                        'texto': f'🧵 Por que o jogo foi assim ({c["placar_txt"]}). 1) {c["porque1"]}',
                        'partes': [f'{i + 2}) {t}' for i, t in enumerate(partes)]})
    les = M.get('lesao') or {}
    if 'lesao' in cats and les.get('data') and _dias(M['hoje'], les['data']) <= 4:   # boletim e post do jogador: só nos primeiros dias
        out.append({'autor': of, 'verificado': True, 'tipo': 'oficial', 'pauta': 'redes|lesao', 'tom': 'neu',
                     'texto': f'🏥 Boletim médico: {c["lesionado"]} segue em tratamento no departamento médico. O clube divulgará a evolução da recuperação.'})
        out.append({'autor': _handle(c['lesionado']), 'nome_exibicao': c['lesionado'], 'verificado': True, 'tipo': 'jogador', 'pauta': 'redes|lesao',
                    'tom': 'pos', 'texto': rnd.choice(['Obrigado por todas as mensagens. A recuperação já começou. Volto mais forte 💪🙏',
                                                       'Dia a dia, passo a passo. Logo estou de volta com vocês ❤️'])})
    if 'volta' in cats:
        out.append({'autor': _handle(c['volta']), 'nome_exibicao': c['volta'], 'verificado': True, 'tipo': 'jogador', 'pauta': 'redes|volta',
                    'tom': 'pos', 'texto': 'De volta ao que eu mais amo. Obrigado a todos que me ajudaram na recuperação ⚽❤️'})
    pj = M.get('pj') or {}
    if fase == 'pre' and c.get('jogo_prox'):
        import clube
        jogo = f'{clube.nome_time(pj.get("casa"))} x {clube.nome_time(pj.get("fora"))}' if pj.get('casa') else c['jogo_prox']
        out.append({'autor': of, 'verificado': True, 'tipo': 'oficial', 'pauta': 'redes|oficial', 'tom': 'pos',
                    'texto': f'É DIA DE JOGO! 🏟️ {jogo} | {pj.get("competicao") or ""}'.rstrip(' |')
                             + (' — é clássico! 🔥' if c.get('classico') else '')})
        if c.get('tec_rival'):
            frases = (['"Pegamos o {nos} na hora certa. Eles estão em dúvida, nós não."', '"O {nos} está nervoso. Dá para sentir de longe."']
                      if 'pressao_rival' in cats else
                      ['"Respeitamos o {nos}, mas não temos medo de ninguém."', '"Vamos jogar de igual para igual, como sempre fazemos."',
                       '"Sabemos onde machucar o {nos}. Estudamos muito."'])
            out.append({'autor': f'@{c["prox_slug"]}_oficial', 'verificado': True, 'tipo': 'oficial', 'pauta': 'redes|tec_rival', 'tom': 'riv',
                        'texto': f'🎙️ {c["tec_rival"]} na coletiva: ' + rnd.choice(frases).format(nos=nos)})
    return out


def citacoes(posts, rnd, c):
    """Um ou dois posts que citam outro post do feed (resposta de torcedor a hater/rival, perfil de números checando)."""
    out = []
    alvos = [p for p in posts if p.get('tom') in ('hate', 'riv') and not p.get('cita')]
    rnd.shuffle(alvos)
    for p in alvos[:2]:
        txt = rnd.choice(['Esse aí some quando a gente ganha 😂', 'Salvei o print. Na volta a gente conversa 📸',
                          'Vive de secar, não tem um título pra contar 🤭', 'Fala isso no estádio, quero ver 😤',
                          f'Respeita o {c.get("apelido") or c["nos"]}!'])
        out.append({'autor': c['torc'], 'texto': txt, 'pauta': 'redes|citacao', 'tom': 'pos', 'tipo': 'citacao',
                    'cita': {'autor': p['autor'], 'texto': p['texto']}})
    nums = [p for p in posts if p.get('tom') == 'neg' and not p.get('cita')]
    if nums and rnd.random() < 0.6:
        p = rnd.choice(nums)
        out.append({'autor': '@futebol_raiz', 'texto': rnd.choice(['A cobrança é justa, mas sem exagero.', 'Torcedor tem razão de reclamar. Agora é hora de apoiar.',
                                                                    'Isso aqui resume o sentimento da arquibancada hoje.']),
                    'pauta': 'redes|citacao', 'tom': 'neu', 'tipo': 'citacao', 'cita': {'autor': p['autor'], 'texto': p['texto']}})
    return out


def em_alta(M, fase, c, cats, rnd):
    """'Em alta': assuntos do momento com o número de posts (proporcional ao tamanho da torcida)."""
    import math
    base = math.log10(M.get('socios') or 200_000)
    tag = lambda s: '#' + ''.join(p.capitalize() for p in _slug(s.replace(' ', '_')).split('_')) if s else None
    import clube
    camel = lambda s: '#' + ''.join(w[:1].upper() + w[1:] for w in __import__('re').split(r'[^0-9A-Za-zÀ-ÿ]+', clube.nome_time(s or '')) if w)
    ts = []
    ap = c.get('apelido') or c['nos']
    if 'seq_derrotas' in cats or 'crise' in cats:
        ts.append((camel(f'Acorda {ap}'), 3.0))
    if 'perdeu_lider' in cats:
        ts.append((camel(f'{c["rival"]} Líder'), 2.6))
    if 'assumiu_lider' in cats:
        ts.append((camel(f'{ap} Líder'), 2.8))
    if 'lesao' in cats:
        ts.append((camel(f'Força {c["lesionado"]}'), 2.2))
    if 'volta' in cats:
        ts.append((camel(f'{c["volta"]} Voltou'), 2.0))
    if c.get('classico'):
        ts.append((camel(c['classico']), 3.2))
    if 'semana' in cats:
        ts.append(('#SemanaDecisiva', 1.8))
    if fase != 'pre' and c.get('adv'):
        ts.append((camel(c['nos']) + 'x' + camel(c['adv'])[1:], 2.4))
    if fase == 'pre' and c.get('prox'):
        ts.append((camel(c['nos']) + 'x' + camel(c['prox'])[1:], 2.4))
    if c.get('craque'):
        ts.append((camel(c['craque']), 1.6))
    if c.get('pior'):
        ts.append((camel(f'Fora {c["pior"]}') if 'seq_derrotas' in cats else camel(c['pior']), 1.3))
    if 'analise' in cats:
        ts.append(('#MesaTática', 1.1))
    ts.append((camel(ap), 1.5))
    vistos, out = set(), []
    for t, w in sorted(ts, key=lambda x: -x[1] * rnd.uniform(0.8, 1.2)):
        if t and t not in vistos and len(out) < 6:
            vistos.add(t)
            out.append({'tag': t, 'posts': int(10 ** (base - 2.3) * w * rnd.uniform(0.6, 1.5))})
    return sorted(out, key=lambda x: -x['posts'])


def ritmo(posts, rnd):
    """Atraso (minutos) de cada post: ~40% já estão no ar; o resto aparece ao longo de ~2 horas."""
    n = len(posts)
    k = max(4, int(n * 0.4))
    atrasos = sorted(rnd.uniform(2, 130) for _ in range(max(0, n - k)))
    for i, p in enumerate(posts):
        p['min'] = 0 if i < k else round(atrasos[i - k])
    return posts
