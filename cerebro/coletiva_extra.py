"""COLETIVAS — LOTE 2 (12/10/2026): perguntas que só existem porque a Central agora sabe mais do jogo.

Pedido do usuário: "pense no futebol, analise e crie mais coletivas, mais interativo e menos repetitivo". Cada cenário
nasce de um fato real da carreira e tem várias formas de perguntar (sorteadas), três respostas com tons diferentes e
consequências no vestiário (moral) e na manchete do dia seguinte:
  departamento médico  lesão do craque, desfalque em jogo grande, chance do substituto, volta, capitão fora,
                       dependência de um jogador;
  o adversário         o plano que a IA adversária usou (marcação individual no craque, bloco baixo, pressão alta,
                       pressão ofensiva) e o que ela deve fazer no próximo jogo; duelo com técnico famoso;
  a corrida            jogo de seis pontos, rival direto na cola, líder disparado, reta final, adversário brigando
                       contra a queda;
  o jogo               0 x 0 em casa, vitória com defesa vazada, jogo grande vencido sem o craque, rodízio que custou
                       pontos, garoto que estreou, time no limite físico;
  a imprensa           a manchete do jornal do dia vira pergunta ("a Gazeta disse que...").
Registrados em coletiva_cenarios.CENARIOS (o sorteio e o controle de repetição são os mesmos).
"""
import clube
from coletiva_cenarios import E, G, ESTRELAS, cen, op, _seq


def _t(nome):
    return clube.nome_time(nome)


def _pts(n):
    n = abs(n)
    return f'{n} ponto' + ('' if n == 1 else 's')

TECNICOS_FAMOSOS = {'Pep Guardiola', 'Carlo Ancelotti', 'Jürgen Klopp', 'Diego Simeone', 'Mikel Arteta', 'Arne Slot',
                    'Hansi Flick', 'Xabi Alonso', 'Luis Enrique', 'José Mourinho', 'Antonio Conte', 'Thomas Tuchel',
                    'Abel Ferreira', 'Filipe Luís', 'Enzo Maresca', 'Unai Emery', 'Simone Inzaghi', 'Zinedine Zidane'}


def _q(rnd, *formas):
    return rnd.choice(formas)


def _jog_por_nome(X, nome):
    return next((j for j in X['J'] if j['nome'] == nome), None)


def _instr(reg, nome):
    return any(i.startswith(nome) for i in (reg or {}).get('instrucoes') or [])


# ================================================================ departamento médico
@cen
def lesao_do_craque(X, rnd):
    a = X.get('lesao')
    if not a or a.get('rank', 9) > 6 or not 0 <= _d(X, a) <= 10:
        return None
    n, sub = a['nome'], a.get('sub')
    j = _jog_por_nome(X, n)
    js = _jog_por_nome(X, sub['nome']) if sub else None
    p = _q(rnd, f'Como o time vai jogar sem {n}?', f'{n} está no departamento médico. Qual o tamanho dessa perda?',
           f'Sem {n}, o time perde o principal jogador. Qual é o plano?')
    ops = [op(f'Ninguém substitui o {n}, mas o grupo é forte. ' + (f'O {sub["nome"]} está pronto e tem minha confiança.' if sub else 'Outros vão assumir.'),
              ([E(js['kc'], 4, 3, 'o técnico disse em público que confia nele para substituir o craque')] if js else []) + [G(1, 'o técnico passou confiança no elenco')],
              f'"O grupo é forte": técnico confia no elenco sem {n}', 'Discurso de união no momento difícil.'),
           op(f'É uma perda enorme. Vou ser sincero: o {n} faz uma diferença que poucos fazem no mundo.',
              ([E(j['kc'], 3, 2, 'o técnico exaltou a importância dele')] if j else []) + [G(-2, 'o técnico deixou no ar que o time depende de um jogador')],
              f'Técnico admite: "sem {n} perdemos muito"', 'Sinceridade que pode pesar no vestiário.'),
           op('Lesão faz parte do futebol. Time grande não chora: quem entrar vai ter que resolver.',
              [G(2, 'o técnico cobrou postura de quem vai entrar')] + ([E(js['kc'], 2, 2, 'ganhou a chance com cobrança pública')] if js else []),
              f'"Time grande não chora": técnico cobra o elenco sem {n}', 'Recado duro para os reservas.')]
    return 9.5 if a.get('rank', 9) <= 2 else 8, 'lesao', p, ops


@cen
def desfalque_jogo_grande(X, rnd):
    a = X.get('lesao')
    if not a or not a.get('grandes') or not 0 <= _d(X, a) <= 10:
        return None
    g = a['grandes'][0]
    alvo = g['classico'] or g['adv']
    n = a['nome']
    p = _q(rnd, f'O {alvo} sem {n}: muda o jeito de jogar?', f'Dá para encarar o {alvo} sem o {n}?',
           f'Sem {n}, o que o torcedor pode esperar do {alvo}?')
    return 9, 'lesao', p, [
        op('Vamos mudar sim. Sem ele, o time precisa ser mais coletivo, mais paciente. Tenho uma ideia clara.',
           [G(2, 'o técnico mostrou um plano para o jogo grande sem o craque')], f'Técnico já tem plano para o {alvo} sem {n}', 'Confiança tática antes do jogo grande.'),
        op(f'A torcida pode esperar um time que vai morrer em campo. Com ou sem {n}, a gente vai para cima.',
           [G(3, 'o técnico pediu entrega total para o jogo grande', 2)], '"Vamos morrer em campo": técnico inflama o jogo grande', 'Discurso de guerra empolga a arquibancada.'),
        op(f'Vamos esperar até a última hora. O {n} é dúvida, não está descartado.',
           [G(0, 'o técnico fez mistério sobre o craque')], f'Mistério: técnico não descarta {n}', 'Jogo psicológico com o adversário.')]


@cen
def chance_do_substituto(X, rnd):
    a = X.get('lesao')
    sub = (a or {}).get('sub')
    if not sub or not 0 <= _d(X, a) <= 14:
        return None
    js = _jog_por_nome(X, sub['nome'])
    if not js:
        return None
    p = _q(rnd, f'É a grande chance do {sub["nome"]}?', f'O {sub["nome"]} está pronto para assumir a vaga do {a["nome"]}?',
           f'Muita gente duvida do {sub["nome"]}. O que você diz?')
    return 7, 'jogador', p, [
        op(f'O {sub["nome"]} trabalha em silêncio há muito tempo. Merece e vai aproveitar.',
           [E(js['kc'], 6, 3, 'o técnico o elogiou em público como substituto do craque')], f'Técnico banca {sub["nome"]}: "merece e vai aproveitar"', 'O reserva ganha moral.'),
        op(f'Ninguém tem a vaga garantida. O {sub["nome"]} começa, mas vai ter que mostrar no jogo.',
           [E(js['kc'], 1, 2, 'ganhou a vaga, mas sob observação')], f'{sub["nome"]} tem a vaga, mas sob pressão', 'Cobrança que motiva... ou trava.'),
        op('Vou testar alternativas. Talvez nem seja ele: posso mudar o desenho do time.',
           [E(js['kc'], -4, 3, 'o técnico deu a entender que ele não é a solução')], f'{sub["nome"]} não é garantido nem com o craque fora', 'O reserva fica sabendo pela imprensa.')]


@cen
def volta_do_craque(X, rnd):
    v = X.get('lesao_volta')
    if not v or not 0 <= _d(X, v) <= 7:
        return None
    n = v['nome']
    j = _jog_por_nome(X, n)
    if not j:
        return None
    p = _q(rnd, f'{n} está de volta. Já começa jogando?', f'{n} recuperado: volta direto ou aos poucos?',
           f'A torcida pede {n} no time. Ele aguenta 90 minutos?')
    return 8, 'lesao', p, [
        op('Volta aos poucos. Não vou arriscar o jogador mais importante por um jogo.',
           [E(j['kc'], 1, 2, 'o técnico cuidou da volta dele com calma')], f'{n} volta aos poucos', 'Prudência do departamento médico prevalece.'),
        op('Craque é craque. Se está liberado, joga. O time precisa dele agora.',
           [E(j['kc'], 4, 2, 'o técnico o colocou direto de volta'), G(1, 'o grupo ganhou o craque de volta')], f'Sem rodeios: {n} volta direto ao time', 'Risco calculado... ou não.'),
        op(f'Quem jogou no lugar dele foi bem. O {n} vai ter que reconquistar a vaga.',
           [E(j['kc'], -4, 3, 'o técnico disse que ele terá de reconquistar a vaga'), G(2, 'o técnico valorizou quem segurou a ausência')],
           f'{n} terá que reconquistar a vaga', 'Recado do técnico divide opiniões.')]


@cen
def capitao_lesionado(X, rnd):
    a = X.get('lesao')
    if not a or not a.get('capitao') or not 0 <= _d(X, a) <= 10:
        return None
    lideres = sorted((j for j in X['J'] if j['nome'] != a['nome'] and j['t_jogos'] >= 3), key=lambda j: -j['moral'])[:1]
    if not lideres:
        return None
    l0 = lideres[0]
    return 7, 'lideranca', f'Com o capitão {a["nome"]} fora, quem usa a braçadeira?', [
        op(f'O {l0["nome"]}. É um líder natural e o grupo respeita.',
           [E(l0['kc'], 5, 3, 'o técnico o anunciou como capitão na ausência do titular')], f'{l0["nome"]} herda a braçadeira', 'Escolha bem recebida no vestiário.'),
        op('A braçadeira continua sendo do capitão. Em campo, vários vão liderar.',
           [E(f'{a["k"][0]}:{a["k"][1]}', 2, 2, 'o técnico manteve a braçadeira simbolicamente com ele')],
           'Técnico mantém braçadeira simbólica com o capitão lesionado', 'Gesto de respeito ao capitão.'),
        op('Isso eu resolvo no vestiário, não aqui.',
           [], 'Técnico faz mistério sobre a braçadeira', 'A imprensa especula nomes.')]


@cen
def dependencia_do_craque(X, rnd):
    J = [j for j in X['J'] if j['t_jogos'] >= 5]
    gols = sum(j['t_gols'] for j in J)
    if gols < 10:
        return None
    top = max(J, key=lambda j: j['t_gols'])
    parte = top['t_gols'] / gols
    if parte < 0.38:
        return None
    p = _q(rnd, f'{round(parte * 100)}% dos gols do time são do {top["nome"]}. O time depende demais dele?',
           f'Se o {top["nome"]} não marca, quem marca?', f'O time virou "{top["nome"]} e mais dez"?')
    return 6.5, 'estilo', p, [
        op(f'O {top["nome"]} faz gols porque o time cria para ele. É mérito coletivo.',
           [E(top['kc'], 1, 2, 'o técnico dividiu o mérito dos gols'), G(1, 'o técnico valorizou o coletivo')], 'Técnico: "os gols dele são do time todo"', 'Resposta diplomática.'),
        op('Concordo que precisamos de mais gente fazendo gol. Os meias e os pontas têm que aparecer.',
           [G(-1, 'o técnico cobrou gols dos outros jogadores')], 'Técnico cobra gols além do artilheiro', 'O recado vai direto para meias e pontas.'),
        op(f'Se eu tenho o {top["nome"]}, vou usar o {top["nome"]}. Quem tem um craque desses não reclama.',
           [E(top['kc'], 4, 2, 'o técnico o chamou de diferencial do time')], f'"Quem tem {top["nome"]} não reclama"', 'O artilheiro se sente o dono do time.')]


# ================================================================ o adversário (IA adversária)
@cen
def anulado_pela_marcacao(X, rnd):
    reg = X.get('ia_ult')
    if not reg or X['res'] == 'V':
        return None
    alvo = next((i[len('Marcação ('):-1] for i in reg.get('instrucoes') or [] if i.startswith('Marcação (')), None)
    j = _jog_por_nome(X, alvo) if alvo else None
    lj = next((x for x in X['linhas'] if x['nome'] == alvo), None)
    # 12/10/2026: só se o marcado jogou de verdade e foi mal (o William estava lesionado contra o Palace)
    if not j or not lj or lj['min'] < 45 or lj['gols'] or (lj['nota'] or 0) >= 6.5:
        return None
    p = _q(rnd, f'O {_t(X["adv"])} colou um marcador no {alvo} o jogo inteiro. Faltou plano B?',
           f'Com marcação individual no {alvo}, o time travou. Como sair disso?',
           f'O {reg.get("tecnico") or "técnico adversário"} anulou o {alvo}. Você foi surpreendido?')
    return 8.5, 'tatica', p, [
        op(f'Faltou. Quando marcam o {alvo}, o espaço aparece em outro lugar e não soubemos achar. Isso é comigo.',
           [G(2, 'o técnico assumiu a falha tática')], 'Técnico assume: "faltou plano B"', 'Autocrítica rara após a derrota.'),
        op(f'O {alvo} precisa aprender a se livrar da marcação. Craque de verdade decide mesmo marcado.',
           [E(j['kc'], -4, 2, 'o técnico cobrou que ele resolva mesmo marcado')], f'Técnico cobra {alvo}: "craque decide marcado"', 'A cobrança pública incomoda o craque.'),
        op(f'Eles jogaram para não perder. Marcar homem a homem é admitir que o {X["nos"]} é maior.',
           [G(2, 'o técnico disse que o adversário se rendeu ao tamanho do time')], f'Técnico provoca: "marcar homem a homem é respeito"', 'O rival não gostou.')]


@cen
def furar_ferrolho(X, rnd):
    reg = X.get('ia_ult')
    pl = (reg or {}).get('plano') or {}
    if not reg or X['res'] == 'V' or pl.get('linha_defensiva', 9) > 4:
        return None
    p = _q(rnd, f'O {_t(X["adv"])} se fechou lá atrás. Como furar um ferrolho assim?', 'Contra time retrancado o seu time parece não ter ideia. O que falta?',
           f'Dez jogadores atrás da linha da bola: o {_t(X["adv"])} encontrou o caminho para te parar?')
    return 7.5, 'tatica', p, [
        op('Paciência e bola parada. Contra bloco baixo, você não pode se desesperar.', [G(1, 'o técnico mostrou calma após o tropeço')],
           'Técnico pede paciência contra retrancas', 'Leitura tática do jogo.'),
        op('Faltou coragem para arriscar o drible e o chute de fora. Vou cobrar isso no treino.', [G(-1, 'o técnico cobrou ousadia do elenco')],
           'Técnico cobra ousadia contra time fechado', 'Treinos de finalização à vista.'),
        op(f'O {_t(X["adv"])} não veio jogar futebol. Veio para não perder, e conseguiu. Isso não é mérito.', [G(1, 'o técnico criticou a postura do adversário')],
           f'Técnico critica o {_t(X["adv"])}: "não veio jogar"', 'O rival rebate nos jornais.')]


@cen
def nas_costas_da_pressao(X, rnd):
    reg = X.get('ia_ult')
    pl = (reg or {}).get('plano') or {}
    if not reg or X['res'] != 'V' or pl.get('linha_defensiva', 0) < 6 or pl.get('pressao', 1) != 0:
        return None
    p = _q(rnd, f'O {_t(X["adv"])} pressionou alto e o seu time achou o espaço nas costas. Foi o plano?',
           'Contra a pressão alta, o time jogou rápido e venceu. Estava treinado para isso?')
    return 7, 'tatica', p, [
        op('Foi treinado sim. Sabíamos que eles iam subir a linha, e a velocidade dos nossos atacantes faz o resto.',
           [G(2, 'o técnico revelou o plano vencedor')], 'Técnico revela o segredo: "sabíamos que iam pressionar"', 'Vitória tática.'),
        op('Mérito dos jogadores. Eu só desenho; quem executa é que ganha o jogo.', [G(3, 'o técnico deu todo o mérito ao elenco')],
           '"Quem executa ganha": técnico divide os méritos', 'O vestiário gosta.'),
        op(f'Contra nós, pressionar alto é suicídio. O {_t(X["adv"])} vai aprender.', [G(1, 'o técnico provocou o adversário')],
           'Técnico provoca: "pressionar alto contra nós é suicídio"', 'Declaração ousada.')]


@cen
def adversario_estudou(X, rnd):
    reg = X.get('ia_ult')
    if not reg or X['res'] != 'D' or not reg.get('olheiro'):
        return None
    p = _q(rnd, f'O {_t(X["adv"])} parecia saber tudo sobre o seu time. O seu jogo ficou previsível?',
           'A imprensa diz que os adversários já decoraram o seu time. Está na hora de mudar?')
    return 8, 'tatica', p, [
        op('Talvez. Vou mexer em algumas coisas: um time campeão precisa surpreender.', [G(1, 'o técnico prometeu novidades táticas')],
           'Técnico promete mudanças: "time campeão surpreende"', 'Expectativa por novidades.'),
        op('Previsível é quem perde sempre. Uma derrota não muda uma ideia de jogo.', [G(1, 'o técnico defendeu o modelo de jogo')],
           'Técnico defende o modelo: "uma derrota não muda a ideia"', 'Convicção ou teimosia?'),
        op('Eles se fecharam e tiveram sorte. Não vou mudar nada por um resultado.', [G(-1, 'o técnico minimizou a derrota')],
           'Técnico fala em sorte do adversário', 'A explicação não convence.')]


@cen
def duelo_de_tecnicos(X, rnd):
    reg = X.get('ia_prox')
    t = (reg or {}).get('tecnico')
    if not t or t not in TECNICOS_FAMOSOS:
        return None
    adv = _t(X['prox']['adv'])
    p = _q(rnd, f'Do outro lado estará o {t}. Como é enfrentar um técnico desse nível?', f'{t} contra você: vai ser um jogo de xadrez?',
           f'O {adv} do {t} costuma complicar a vida dos grandes. Já estudou o adversário?')
    return 7.5, 'proximo', p, [
        op(f'Admiro muito o trabalho do {t}. Vai ser um jogo de detalhes, de quem errar menos.', [G(1, 'o técnico mostrou respeito ao rival')],
           f'Respeito: técnico elogia {t} antes do duelo', 'Clima cordial antes do jogo.'),
        op(f'Respeito, mas quem joga são os jogadores. E os meus são melhores.', [G(3, 'o técnico afirmou que o elenco é melhor')],
           f'"Os meus são melhores": técnico provoca o {adv}', 'Provocação esquenta o jogo.'),
        op('Estudamos tudo: como eles saem, como pressionam, como marcam. Não vai ter surpresa.', [G(2, 'o técnico passou segurança na preparação')],
           'Técnico garante: "não vai ter surpresa"', 'Preparação minuciosa.')]


@cen
def plano_do_adversario(X, rnd):
    reg = X.get('ia_prox')
    pl = (reg or {}).get('plano') or {}
    if not reg or not pl:
        return None
    adv = _t(X['prox']['adv'])
    if pl.get('linha_defensiva', 5) <= 4:
        jeito = 'se fechar e sair no contra-ataque'
    elif pl.get('estilo_defensivo') == 0 and pl.get('pressao') == 0:
        jeito = 'pressionar alto desde a saída de bola'
    else:
        return None
    marc = next((i[len('Marcação ('):-1] for i in reg.get('instrucoes') or [] if i.startswith('Marcação (')), None)
    p = (f'Tudo indica que o {adv} vai {jeito}' + (f' e colar um marcador no {marc}' if marc else '') + '. Como pretende responder?')
    return 6.5, 'proximo', p, [
        op('Já treinamos as duas situações. O time sabe o que fazer.', [G(1, 'o técnico tranquilizou o grupo')], f'Técnico já tem a resposta ao {adv}', 'Tranquilidade antes do jogo.'),
        op('Não vou falar do plano aqui. O adversário lê jornal também.', [], 'Técnico faz mistério sobre o plano', 'Jogo de informação.'),
        op(f'Se o {adv} vier assim, vai encontrar um time pronto para castigar.', [G(2, 'o técnico demonstrou confiança')],
           f'Técnico avisa o {adv}: "vamos castigar"', 'Recado direto ao adversário.')]


# ================================================================ a corrida
@cen
def jogo_de_seis_pontos(X, rnd):
    ds = X.get('pj_disputa')
    if not ds or not ds.get('mesma_zona') or not X.get('prox'):
        return None
    adv = _t(X['prox']['adv'])
    p = _q(rnd, f'Contra o {adv} é jogo de seis pontos. É uma final?', f'Vencer o {adv} vale quase o campeonato?',
           f'O {adv} briga pela mesma coisa que vocês. O vestiário sente a pressão?')
    return 9, 'corrida', p, [
        op('É uma final, sim. E finais a gente não joga, a gente ganha.', [G(3, 'o técnico tratou o jogo como final', 2)],
           f'"Finais a gente ganha": técnico eleva o tom contra o {adv}', 'Clima de decisão.'),
        op('São três pontos como os outros. Se eu tratar como final, o time trava.', [G(1, 'o técnico tirou o peso do jogo')],
           'Técnico tira o peso: "são três pontos"', 'Estratégia para aliviar a pressão.'),
        op(f'A pressão está toda do lado do {adv}. Nós estamos onde queremos estar.', [G(2, 'o técnico jogou a pressão para o rival')],
           f'Técnico joga a pressão para o {adv}', 'Guerra psicológica.')]


@cen
def rival_na_cola(X, rnd):
    co = X.get('corrida')
    if not co or not co.get('rivais') or co['pos'] != 1:
        return None
    rv = co['rivais'][0]
    if rv['dif'] > 0 or abs(rv['dif']) > 3:
        return None
    p = _q(rnd, f'O {rv["nome"]} está a {_pts(rv["dif"])}. Dá para dormir tranquilo na liderança?',
           f'Liderança apertada, o {rv["nome"]} na cola. Olha para a tabela?', f'O {rv["nome"]} não para de vencer. Isso preocupa?')
    return 8, 'corrida', p, [
        op('Não olho para o lado. Se fizermos a nossa parte, o resto não importa.', [G(1, 'o técnico focou só no próprio time')],
           'Técnico ignora o rival: "fazemos a nossa parte"', 'Foco total.'),
        op(f'Claro que olho. O {rv["nome"]} é muito forte e vai até o fim. Não podemos tropeçar.', [G(1, 'o técnico alertou o grupo sobre o rival')],
           f'Técnico respeita o {rv["nome"]}: "vai até o fim"', 'Alerta ligado.'),
        op(f'Quem está na frente somos nós. A pressão é deles.', [G(2, 'o técnico passou confiança na liderança')],
           f'"A pressão é deles": técnico provoca o {rv["nome"]}', 'O rival responde nos jornais.')]


@cen
def perseguidor(X, rnd):
    co = X.get('corrida')
    if not co or not co.get('rivais') or co['pos'] == 1:
        return None
    rv = next((r for r in co['rivais'] if r['dif'] > 0), None)
    if not rv or rv['dif'] > 6:
        return None
    p = _q(rnd, f'A {_pts(rv["dif"])} do {rv["nome"]}. Ainda dá?', 'Correr atrás é mais fácil ou mais difícil?',
           f'O {rv["nome"]} pode tropeçar? Vocês estão torcendo contra?')
    return 7.5, 'corrida', p, [
        op('Dá, e vai dar. Faltam jogos suficientes, e o time está pronto.', [G(2, 'o técnico acredita na virada da tabela')],
           'Técnico garante: "ainda dá"', 'Fé na virada.'),
        op('Não dependemos só de nós. Precisamos vencer e esperar.', [G(0, 'o técnico admitiu depender do rival')],
           'Técnico admite: "não dependemos só de nós"', 'Realismo que esfria a torcida.'),
        op(f'Quem persegue não tem nada a perder. A pressão é toda do {rv["nome"]}.', [G(2, 'o técnico pôs a pressão no rival')],
           f'Técnico: "a pressão é do {rv["nome"]}"', 'Jogo psicológico.')]


@cen
def reta_final(X, rnd):
    co = X.get('corrida')
    if not co or co.get('restantes', 99) > 4:
        return None
    z = co['nome_zona']
    p = _q(rnd, f'Faltam {co["restantes"]} rodadas. O que você diz ao grupo agora?', f'Reta final na briga ({z}). Como segurar os nervos?')
    return 8.5, 'corrida', p, [
        op('Digo que cada jogo é uma vida. Não existe amanhã.', [G(3, 'o técnico motivou o grupo para a reta final', 2)],
           '"Cada jogo é uma vida": técnico motiva para a reta final', 'Clima de decisão.'),
        op('Digo para curtirem. Chegar até aqui já é mérito; agora é jogar solto.', [G(2, 'o técnico tirou o peso da reta final')],
           'Técnico pede leveza na reta final', 'Ambiente tranquilo.'),
        op('Não digo nada. Quem precisa de discurso a essa altura não deveria estar aqui.', [G(-1, 'o técnico foi duro com o elenco na reta final')],
           'Técnico seco: "quem precisa de discurso não deveria estar aqui"', 'Frase forte repercute.')]


@cen
def adversario_dando_a_vida(X, rnd):
    ds = X.get('pj_disputa')
    if not ds or ds.get('mesma_zona') or not ds.get('adv') or not X.get('prox'):
        return None
    adv = _t(X['prox']['adv'])
    zona = (ds['adv'].get('texto') or '').split(':')[0]
    p = _q(rnd, f'O {adv} está desesperado ({zona}). Vai ser o jogo mais pegado da temporada?',
           f'Pegar o {adv} brigando pela vida é perigoso?')
    return 7, 'proximo', p, [
        op('É o jogo mais perigoso. Time que briga por sobrevivência joga com a faca nos dentes.', [G(2, 'o técnico alertou o grupo')],
           f'Alerta: "o {adv} vai jogar com a faca nos dentes"', 'Respeito ao adversário.'),
        op('Respeito, mas o problema é deles. Nós temos os nossos objetivos.', [G(1, 'o técnico manteve o foco')],
           '"O problema é deles": técnico mantém o foco', 'Frieza antes do jogo.'),
        op(f'Se o {adv} está nessa situação, é porque não fez a parte dele antes. Não vou ter pena.', [G(1, 'o técnico foi duro com o adversário')],
           f'Técnico sem pena do {adv}', 'A frase irrita o rival.')]


# ================================================================ o jogo
@cen
def zero_a_zero_em_casa(X, rnd):
    if not X['casa'] or X['gp'] != 0 or X['gc'] != 0:
        return None
    p = _q(rnd, '0 x 0 em casa. Faltou criatividade?', 'A torcida saiu vaiando o empate sem gols. Entende?', 'Onde estavam os gols hoje?')
    return 7, 'resultado', p, [
        op('Faltou o último passe. Criamos, mas sem a calma na hora de decidir.', [G(0, 'o técnico analisou o empate com calma')], 'Técnico: "faltou o último passe"', 'Análise sóbria.'),
        op('A vaia é justa. Em casa, esse time tem obrigação de vencer.', [G(-2, 'o técnico concordou com a vaia da torcida')], 'Técnico dá razão à vaia', 'O vestiário sente o golpe.'),
        op('Um ponto contra um time fechado não é tragédia. Ninguém vai ganhar sempre.', [G(1, 'o técnico protegeu o grupo após o empate')],
           'Técnico minimiza: "um ponto não é tragédia"', 'A torcida não gostou.')]


@cen
def vitoria_com_defesa_vazada(X, rnd):
    if X['res'] != 'V' or X['gc'] < 2:
        return None
    p = _q(rnd, f'Venceram, mas sofreram {X["gc"]} gols. A defesa preocupa?', 'Três pontos, mas a defesa tomou um baile em alguns momentos. Satisfeito?')
    zags = [j for j in X['linhas'] if j['pos'] in ('CB', 'LB', 'RB')]
    pior = min(zags, key=lambda j: j['nota'], default=None)
    return 6.5, 'resultado', p, [
        op('Preocupa. Vencer tomando gol não é sustentável. Vamos corrigir no treino.', [G(0, 'o técnico apontou o problema defensivo')],
           'Técnico admite: "defesa precisa melhorar"', 'Alerta mesmo com a vitória.'),
        op('Prefiro ganhar de 4 a 3 do que perder de 1 a 0. Meu time é para atacar.', [G(2, 'o técnico defendeu o estilo ofensivo')],
           '"Prefiro 4 a 3": técnico defende o ataque', 'A torcida adora.'),
        op(f'Alguns jogadores precisam de mais concentração. {pior["nome"]} sabe do que estou falando.' if pior else 'Teve desatenção, e quem errou sabe.',
           ([E(pior['kc'], -4, 2, 'o técnico o cobrou em público pelos gols sofridos')] if pior else []) + [G(-1, 'o técnico expôs falhas individuais')],
           'Técnico expõe falhas da defesa', 'Cobrança pública na zaga.')]


@cen
def vitoria_sem_o_craque(X, rnd):
    a = X.get('lesao')
    if not a or X['res'] != 'V' or not 0 <= _d(X, a) <= 20:
        return None
    if any(x['nome'] == a['nome'] for x in X['linhas']):
        return None
    n = a['nome']
    melhor = max(X['linhas'], key=lambda j: j['nota'], default=None)
    p = _q(rnd, f'Sem {n} e mesmo assim o time venceu. Mostra a força do grupo?', f'O time provou que vive sem o {n}?')
    return 7.5, 'resultado', p, [
        op('Mostra que temos elenco. Todo mundo entendeu a responsabilidade.', [G(3, 'o técnico exaltou o grupo sem o craque')],
           f'"Temos elenco": vitória sem {n} exalta o grupo', 'Moral alta no vestiário.'),
        op(f'O {melhor["nome"]} foi gigante hoje. Assumiu o jogo quando precisávamos.' if melhor else 'Os mais experientes assumiram o jogo.',
           ([E(melhor['kc'], 5, 2, 'o técnico o destacou como o líder da vitória sem o craque')] if melhor else []),
           f'{melhor["nome"] if melhor else "Elenco"} assume o protagonismo sem {n}', 'Novo protagonista.'),
        op(f'Ninguém vive sem o {n}. Ganhamos, mas o time é outro com ele.', [G(-1, 'o técnico disse que o time depende do craque')],
           f'Técnico: "o time é outro com {n}"', 'Os titulares de hoje não gostaram.')]


@cen
def rodizio_custou_caro(X, rnd):
    if X['res'] != 'D' or len(X['linhas']) < 11:
        return None
    titulares = {x['nome'] for x in X['linhas'] if x.get('titular')}
    craques = sorted((j for j in X['J'] if j['t_jogos'] >= 5), key=lambda j: -j['ovr'])[:6]
    poupados = [j for j in craques if j['nome'] not in titulares and not (X.get('lesao') and X['lesao']['nome'] == j['nome'])]
    if len(poupados) < 2:
        return None
    nomes = ', '.join(j['nome'] for j in poupados[:3])
    p = _q(rnd, f'{nomes} começaram no banco e o time perdeu. Arrependido do rodízio?', 'Poupou titulares e perdeu. Foi um erro?')
    return 8, 'escalacao', p, [
        op('O rodízio é necessário. O calendário não perdoa; perder um jogo é melhor que perder um jogador.', [G(1, 'o técnico defendeu o rodízio')],
           'Técnico defende o rodízio: "melhor perder um jogo que um jogador"', 'Gestão de elenco em debate.'),
        op('Errei. Mexi demais e o time perdeu a identidade. Responsabilidade minha.', [G(2, 'o técnico assumiu o erro na escalação')],
           'Técnico assume o erro: "mexi demais"', 'Autocrítica.'),
        op('Quem entrou tinha que dar conta. Não deram, e vão ouvir isso.', [G(-3, 'o técnico culpou os reservas pela derrota', 2)],
           'Técnico culpa os reservas', 'O banco fica revoltado.')]


@cen
def time_no_limite(X, rnd):
    cansados = [j for j in X['J'] if j.get('condicao') is not None and j['condicao'] < 75 and j['t_jogos'] >= 5]
    if len(cansados) < 3 or not X.get('prox'):
        return None
    nomes = ', '.join(j['nome'] for j in cansados[:3])
    p = _q(rnd, f'{nomes} estão no limite físico. Vai poupar contra o {X["prox"]["adv"]}?',
           'O departamento físico acende o alerta: vários titulares no limite. Como administrar?')
    return 7, 'fisico', p, [
        op('Vou rodar o time. Prefiro perder um pouco de força do que perder jogadores por lesão.', [G(2, 'o técnico protegeu os jogadores cansados')],
           'Técnico vai poupar titulares', 'Gestão do físico.'),
        op('Jogo grande não se poupa. Quem estiver em pé, joga.', [G(-1, 'o técnico ignorou o desgaste do elenco')] + [E(j['kc'], -2, 2, 'jogou cansado por decisão do técnico') for j in cansados[:2]],
           '"Quem estiver em pé joga": técnico ignora o desgaste', 'Risco de lesão aumenta.'),
        op('O físico é com a comissão. Vou ouvir os números e decidir no dia.', [G(1, 'o técnico confiou na ciência do esporte')],
           'Técnico vai decidir pelos números do físico', 'Decisão técnica.')]


@cen
def estreia_do_garoto(X, rnd):
    g = next((x for x in X['linhas'] if (x.get('idade') or 30) <= 20 and x.get('t_jogos', 9) <= 2), None)
    if not g:
        return None
    p = _q(rnd, f'Estreia do {g["nome"]}, {g["idade"]} anos. O que achou?', f'O garoto {g["nome"]} entrou em campo. Veio para ficar?')
    return 6.5, 'jogador', p, [
        op('Tem muito talento. Vai ganhar minutos com calma, sem pressão.', [E(g['kc'], 4, 3, 'o técnico elogiou a estreia dele')],
           f'Técnico aprova a estreia de {g["nome"]}', 'O garoto ganha confiança.'),
        op('Gostei, mas ainda tem muito a aprender. Não vamos criar um monstro.', [E(g['kc'], 1, 2, 'o técnico pediu calma com ele')],
           f'Pés no chão com {g["nome"]}', 'Prudência com o jovem.'),
        op('Esse garoto vai ser o melhor do mundo. Anotem o que estou dizendo.', [E(g['kc'], 6, 3, 'o técnico o chamou de futuro melhor do mundo'), G(-1, 'os veteranos acharam exagero')],
           f'"Vai ser o melhor do mundo": técnico exalta {g["nome"]}', 'A frase vira manchete — e pressão.')]


# ================================================================ a imprensa
@cen
def a_manchete_do_dia(X, rnd):
    capas = [c for c in X.get('capas') or [] if c.get('manchete')]
    if not capas:
        return None
    c = rnd.choice(capas)
    m = c['manchete'].strip()
    if len(m) < 12 or len(m) > 90:
        return None
    p = f'O jornal {c["nome"]} estampou hoje: "{m}". Concorda?'
    return 5.5, 'imprensa', p, [
        op('Respeito o trabalho da imprensa. Cada um tem a sua leitura; a minha está no campo.', [G(1, 'o técnico tratou a imprensa com respeito')],
           f'Técnico responde ao {c["nome"]} com elegância', 'Relação cordial com a imprensa.'),
        op('Concordo em parte. Tem coisa ali que eu mesmo já disse ao grupo.', [G(0, 'o técnico concordou com a crítica do jornal')],
           f'Técnico concorda com o {c["nome"]}', 'O vestiário lê o jornal com outros olhos.'),
        op('Não leio jornal. Quem escreve isso nunca entrou num vestiário.', [G(1, 'o técnico blindou o grupo das críticas')],
           'Técnico detona a imprensa: "nunca entraram num vestiário"', 'A crônica esportiva reage.')]


def _d(X, a):
    """Dias desde a data registrada no fato (lesão/volta) até o dia da coletiva."""
    import datetime as dt
    return (dt.date(*X['hoje'][:3]) - dt.date(*tuple(a['data'])[:3])).days
