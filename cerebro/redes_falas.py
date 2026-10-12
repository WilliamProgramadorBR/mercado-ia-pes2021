"""REDES SOCIAIS com mais vida (11/10/2026): banco de ~135 posts-modelo + respostas (comentários) embaixo dos posts.

Cada modelo: (categoria, autor, texto, tom). Autor e texto usam campos {assim}; o modelo só entra se TODOS os campos
existirem no contexto do momento (coerência: "doblete" só se alguém fez 2 gols; "líder" só se o time é líder etc.).
As categorias de jogo só entram na edição pós-jogo (último jogo recente); as de véspera, na pré-jogo.
Os números vêm do save (placar, notas, gols, tabela, destaques do mundo); o resto é opinião de torcedor.

Tons (para as respostas): pos (festa), neg (cobrança), hate (hater), riv (rival provocando), num (números),
meme, neu (neutro). Cada post pode ganhar até 3 respostas de outros perfis.
"""
import random
import string

# ---------------------------------------------------------------- modelos
M_ = [
    # ----- vitória (pós-jogo)
    ('vitoria', '{torc}', 'VITÓRIA! {nos} {gp} x {gc} {adv}. Que time, que time! 🔥', 'pos'),
    ('vitoria', '{torc}', 'Mais três pontos na conta. Segue o baile! 💃', 'pos'),
    ('vitoria', '@arquibancada_{sigla}', 'Saí rouco do estádio. Esse time joga por música 🎶', 'pos'),
    ('vitoria', '@futebol_raiz', 'O {nos} venceu o {adv} com autoridade. Time grande é assim: não dá chance.', 'neu'),
    ('vitoria', '@numerosdabola', '{nos} {gp} x {gc} {adv}. Melhor em campo: {craque} (nota {nota_craque}). 📊', 'num'),
    ('vitoria', '@tatica_pura', 'O {nos} sufocou o {adv} desde a saída de bola. A pressão funcionou de novo.', 'neu'),
    ('vitoria', '@{adv_slug}_raiz', 'Perdemos pro {nos}. Dói, mas era esperado. Bola pra frente. 😔', 'neu'),
    ('vitoria', '@zoeira_fc', 'O {adv} foi lá só pra ver o {craque} jogar de perto 🍿', 'meme'),
    ('vitoria', '@tiozao_do_futebol', 'No meu tempo, um {gp} a {gc} desse era capa de jornal. Hoje é só mais um dia no {nos}.', 'neu'),
    ('vitoria', '@resenha_fc', 'Fim de jogo: {nos} {gp} x {gc} {adv}. Quem viu, viu.', 'neu'),
    ('vitoria', '{torc}', '{craque_up} JOGOU DEMAIS HOJE! Nota {nota_craque} é pouco!', 'pos'),
    ('vitoria', '@vozdageral', 'Ouvi um senhor na saída dizendo que nunca viu o {nos} jogar tão bem. Eu concordo. 🥹', 'pos'),
    ('vitoria', '@secadorprofissional', 'Ganhou do {adv}, grande coisa. Quero ver contra time de verdade. 🙄', 'hate'),
    ('vitoria', '@carlao_pereira', 'Gostei da atitude hoje. Time que corre assim ganha de qualquer um. #BolaNaMesa', 'pos'),
    # ----- goleada
    ('goleada', '{torc}', '{gp} A {gc}!!! PASSAMOS O TRATOR NO {adv_up}!!! 🚜🔥', 'pos'),
    ('goleada', '@zoeira_fc', 'O goleiro do {adv} pediu música no Fantástico e ainda saiu no lucro 😂', 'meme'),
    ('goleada', '@memesdabola', 'O {adv} saindo de campo hoje: 🚶‍♂️🚶‍♂️🚶‍♂️ ({gp} a {gc})', 'meme'),
    ('goleada', '@numerosdabola', 'Goleada: {nos} {gp} x {gc} {adv}. Saldo de {saldo} gols numa noite só. 📊', 'num'),
    ('goleada', '@toninhomarrento', 'Avisa o {adv} que já pode parar de contar! 😂 #BolaNaMesa', 'meme'),
    ('goleada', '@{adv_slug}_raiz', 'Tomar {gp} do {nos}?? Vergonha. Alguém explica?? 😡', 'neg'),
    # ----- empate
    ('empate', '{torc}', 'Empate com o {adv}... esperava mais. 😐', 'neg'),
    ('empate', '@resenha_fc', '{nos} {gp} x {gc} {adv}. Jogo truncado, cada um com um ponto.', 'neu'),
    ('empate', '@tatica_pura', 'Faltou profundidade ao {nos}. Muita posse, pouca infiltração.', 'neu'),
    ('empate', '@zoeira_fc', 'Empate é igual beijo de irmã: ninguém fica satisfeito 😅', 'meme'),
    ('empate', '@futebol_raiz', 'Um ponto contra o {adv}. Não é o fim do mundo, mas acende o alerta.', 'neu'),
    ('empate', '@secadorprofissional', 'Empatou com o {adv} kkkk o poderoso {nos} 🤭', 'hate'),
    ('empate', '@carlao_pereira', 'Empate desse jeito tem cheiro de derrota. Tem que sair pra ganhar! #BolaNaMesa', 'neg'),
    # ----- derrota
    ('derrota', '{torc}', 'Inaceitável perder pro {adv}. Cadê a raça??? 😡', 'neg'),
    ('derrota', '{torc}', 'Calma, galera. Perder faz parte. No próximo tem mais. 🙏', 'neu'),
    ('derrota', '@secadorprofissional', 'O {nos} perdeu pro {adv} kkkkkkk dia lindo 😂😂', 'hate'),
    ('derrota', '@zoeira_fc', 'O {nos} hoje não ganhava nem par ou ímpar 🤡', 'meme'),
    ('derrota', '@{adv_slug}_raiz', 'GANHAMOS DO {nos_up}!!! {gc} A {gp}!!! QUE NOITE!!! 🔥🔥', 'riv'),
    ('derrota', '@tatica_pura', 'O {adv} achou o espaço entre as linhas do {nos} e explorou o jogo todo.', 'neu'),
    ('derrota', '@vozdageral', 'Silêncio na saída do estádio. Só se ouvia o vento.', 'neg'),
    ('derrota', '@tiozao_do_futebol', 'Isso é falta de alguém que bote o dedo na cara no vestiário. No meu tempo era diferente.', 'neg'),
    ('derrota', '@antigoat_fc', 'Cadê o {estrela}? Sumiu de novo em jogo que importa 👻', 'hate'),
    ('derrota', '@numerosdabola', 'Derrota: {nos} {gp} x {gc} {adv}. O {adv} foi mais eficiente. 📉', 'num'),
    # ----- o craque do jogo e os gols
    ('craque_jogo', '{torc}', '{craque} é diferenciado. Não tem outra palavra.', 'pos'),
    ('craque_jogo', '@numerosdabola', '{craque}: nota {nota_craque} contra o {adv}. Melhor do jogo. ⭐', 'num'),
    ('craque_jogo', '@arquibancada_{sigla}', 'Toda vez que a bola chega no {craque} o estádio levanta. 🙌', 'pos'),
    ('craque_jogo', '@helena_saraiva', 'O {craque} ocupou muito bem os espaços hoje. Leitura de jogo acima da média. #BolaNaMesa', 'neu'),
    ('craque_jogo', '@memesdabola', 'Os zagueiros do {adv} depois de marcar o {craque}: 🫠', 'meme'),
    ('doblete', '{torc}', '{autor_gol} fez {gols_autor} hoje!!! Pede música!!! 🎵⚽', 'pos'),
    ('doblete', '@numerosdabola', '{autor_gol}: {gols_autor} gols contra o {adv}. ⚽', 'num'),
    ('doblete', '@zoeira_fc', 'O {autor_gol} tá fazendo gol até sem querer 😂', 'meme'),
    ('gol', '{torc}', 'GOL DO {autor_gol_up}!!! Que bola!!! ⚽🔥', 'pos'),
    ('mal_jogador', '@zoeira_fc', '{pior} hoje: 👻 alguém viu? Nota {nota_pior}', 'meme'),
    ('mal_jogador', '{torc}', 'Não dá mais pro {pior}. Banco já! 🪑', 'neg'),
    ('mal_jogador', '@tiozao_do_futebol', 'O {pior} correu mais atrás do juiz do que da bola.', 'neg'),
    ('mal_jogador', '@tatica_pura', '{pior} perdeu muitos duelos no setor dele. Ponto a corrigir para o próximo jogo.', 'neu'),
    ('mal_jogador', '@secadorprofissional', 'Com o {pior} jogando assim, eu até torço pra ele continuar titular 😂', 'hate'),
    ('mal_jogador', '{torc}', 'Calma com o {pior}, gente. Todo mundo tem dia ruim. Já fez muito por nós.', 'neu'),
    # ----- véspera
    ('pre', '{torc}', 'Vem aí {jogo_prox}! Contagem regressiva ligada ⏳', 'pos'),
    ('pre', '@resenha_fc', 'Palpites para {jogo_prox}? Deixa nos comentários 👇', 'neu'),
    ('pre', '@numerosdabola', '{jogo_prox}: {prob_nos}% de chance de vitória do {nos} pelos números. 📊', 'num'),
    ('pre', '@tatica_pura', 'Chave do jogo contra o {prox}: quem vencer a briga do meio-campo leva.', 'neu'),
    ('pre', '@{prox_slug}_raiz', 'Contra o {nos} a gente cresce. Podem vir! 😤', 'riv'),
    ('pre', '@zoeira_fc', 'O {prox} já tá rezando antes do jogo 🙏😂', 'meme'),
    ('pre', '@tiozao_do_futebol', 'Jogo contra o {prox} se ganha antes, no vestiário. Atitude!', 'neu'),
    ('pre', '@secadorprofissional', 'Torcendo pro {prox} hoje igual torço pro meu time 😈', 'hate'),
    ('pre', '{torc}', 'Confio demais nesse time pro jogo contra o {prox}. Vamos com tudo! 💪', 'pos'),
    ('pre', '@vozdageral', 'A cidade já respira {jogo_prox}. Bandeiras nas janelas desde cedo.', 'pos'),
    ('pre', '@setorista_beto', 'Direto do CT: treino fechado hoje antes do jogo com o {prox}. Novidade a caminho? 👀', 'neu'),
    ('classico', '{torc}', 'SEMANA DE {classico_up}!!! NÃO EXISTE OUTRO ASSUNTO!!! 🔥', 'pos'),
    ('classico', '@{prox_slug}_raiz', 'Clássico é diferente. Esquece tabela, esquece fase. Vai ter troco. 😤', 'riv'),
    ('classico', '@resenha_fc', '{classico}: quem leva? 🤔', 'neu'),
    ('classico', '@tiozao_do_futebol', 'Em {classico} não tem favorito. Já vi time pior ganhar de time melhor muitas vezes.', 'neu'),
    ('classico', '@zoeira_fc', 'Os torcedores do {prox} já preparando a desculpa pra segunda-feira 😂', 'meme'),
    ('final', '{torc}', 'FINAL DA {final_comp_up}!!! VAI, {apelido_up}!!! 🏆', 'pos'),
    ('final', '@numerosdabola', 'Final da {final_comp}: {jogo_prox}. Jogo único, sem segunda chance. 🏆', 'num'),
    ('final', '@vozdageral', 'Nunca vi a cidade assim. É final, e todo mundo sabe o que está em jogo.', 'pos'),
    ('final', '@{prox_slug}_raiz', 'A taça já tem dono e não é vocês 🏆😤', 'riv'),
    ('final', '@futebol_raiz', 'Final é final. Favoritismo fica no vestiário.', 'neu'),
    ('perigo', '@{prox_slug}_raiz', '{perigo} vai deitar na defesa de vocês. {perigo_gols} gols e contando 😏', 'riv'),
    ('perigo', '@tatica_pura', 'Atenção máxima no {perigo}, do {prox}: {perigo_gols} gols na temporada. Tem que dobrar a marcação.', 'num'),
    ('perigo', '{torc}', 'Esse {perigo} não vai ver a cor da bola. Confia na nossa zaga. 🧱', 'pos'),
    # ----- pré-temporada
    ('pre_temporada', '{torc}', 'Saudade de jogo oficial! Que comece logo a temporada 🙏', 'pos'),
    ('pre_temporada', '@mercadodabola', 'Janela aberta: o {nos} vai às compras? Fiquem ligados 👀', 'neu'),
    ('pre_temporada', '@numerosdabola', 'Pré-temporada: amistoso serve para dar ritmo. Resultado não importa (mas importa um pouco). 📊', 'num'),
    ('pre_temporada', '@tiozao_do_futebol', 'Pré-temporada boa é aquela em que ninguém se machuca. O resto é treino.', 'neu'),
    ('pre_temporada', '@zoeira_fc', 'Torcida do {nos} em julho: "esse ano vai" 😂', 'meme'),
    ('pre_temporada', '{torc}', 'Meta da temporada: ganhar tudo de novo. Nem um título a menos! 🏆', 'pos'),
    # ----- tabela
    ('lider', '{torc}', 'LÍDER! {pts} pontos e ninguém alcança! 🔝', 'pos'),
    ('lider', '@numerosdabola', '{nos} na liderança: {pts} pontos em {jogos} jogos. 📊', 'num'),
    ('lider', '@secadorprofissional', 'Liderança agora não vale nada. Quero ver no fim 😏', 'hate'),
    ('lider', '@zoeira_fc', 'Os rivais olhando a tabela e vendo o {nos} lá em cima: 😩', 'meme'),
    ('lider', '@futebol_raiz', 'Regularidade é o nome do jogo. O {nos} é líder com sobra.', 'neu'),
    ('perseguidor', '{torc}', '{dif} pontos do líder. Dá pra buscar! Ninguém desiste! 💪', 'pos'),
    ('perseguidor', '@numerosdabola', '{nos} é o {pos}º, {dif} pontos atrás do {lider}. 📊', 'num'),
    ('perseguidor', '@secadorprofissional', '{pos}º lugar kkkk cadê o time que ia ganhar tudo? 🤭', 'hate'),
    ('mal_tabela', '{torc}', '{pos}º lugar não é a cara do {nos}. Precisa reagir JÁ. 😤', 'neg'),
    ('mal_tabela', '@zoeira_fc', 'O {nos} tá olhando a tabela de baixo pra cima 😬', 'meme'),
    ('mal_tabela', '@tiozao_do_futebol', 'Time grande no meio da tabela é crise, não adianta disfarçar.', 'neg'),
    # ----- o elenco
    ('art_time', '{torc}', '{art_time} já tem {gols_art} gols na temporada. Craque é craque! ⚽', 'pos'),
    ('art_time', '@numerosdabola', 'Artilheiro do {nos} na temporada: {art_time}, {gols_art} gols. 📊', 'num'),
    ('art_time', '@antigoat_fc', '{gols_art} gols do {art_time}? Metade contra time pequeno 🙄', 'hate'),
    ('art_time', '@memesdabola', 'Os goleiros da liga quando veem o {art_time}: 🏃‍♂️💨', 'meme'),
    ('garcom', '@numerosdabola', '{garcom} já deu {assist_gar} assistências. O garçom do {nos}. 🍽️', 'num'),
    ('garcom', '{torc}', 'Quem precisa de GPS quando tem o {garcom} dando passe? 🎯', 'pos'),
    ('jovem', '{torc}', '{jovem}, {idade_jovem} anos, já jogando assim. O futuro é agora! 🌟', 'pos'),
    ('jovem', '@scout_global', '{jovem} ({idade_jovem}) é um dos jovens mais interessantes do {nos}. Anotem.', 'num'),
    ('jovem', '@tiozao_do_futebol', 'Esse {jovem} ainda tem cara de juvenil, mas joga como gente grande.', 'pos'),
    ('veterano', '{torc}', '{veterano} com {idade_vet} anos e ainda correndo mais que os moleques. Respeito! 🫡', 'pos'),
    ('veterano', '@zoeira_fc', 'O {veterano} jogou contra o meu avô e ainda tá em campo 😂 lenda', 'meme'),
    ('capitao', '{torc}', 'Capitão {capitao}! Liderança não se compra, se conquista. ©️', 'pos'),
    ('capitao', '@arquibancada_{sigla}', 'Quando o {capitao} grita, o time inteiro acorda. Isso é capitão.', 'pos'),
    ('estrela', '{torc}', '{bolas} Bolas de Ouro. Quem quiser discutir, traz o currículo. 👑', 'pos'),
    ('estrela', '@antigoat_fc', 'Superestimado. O {estrela} só joga bem porque o time é bom.', 'hate'),
    ('estrela', '@numerosdabola', '{estrela}: {bolas} Bolas de Ouro na carreira. Lenda viva. 🏆', 'num'),
    ('estrela', '@futebol_raiz', 'Daqui a 20 anos, vamos contar pros netos que vimos o {estrela} jogar.', 'pos'),
    ('estrela', '@memesdabola', 'O {estrela} olhando a estante e pensando "falta espaço" 🏆🏆🏆', 'meme'),
    # ----- o mundo (destaques.py)
    ('revelacao', '@scout_global', '{rev}, {rev_idade} anos, {rev_time}: {rev_gols} gols com nota {rev_ovr}. Isso não é normal. 🔎', 'num'),
    ('revelacao', '{torc}', 'Diretoria, traz o {rev} do {rev_time}!! Esse moleque é bom demais!!', 'pos'),
    ('revelacao', '@futebol_raiz', 'Ninguém conhecia o {rev} no começo da temporada. Agora todo mundo quer. Futebol é isso. ⚽', 'neu'),
    ('revelacao', '@{rev_slug}_raiz', 'O {rev} é NOSSO e não está à venda!!! 😤', 'riv'),
    ('revelacao', '@mercadodabola', 'O {rev} ({rev_time}) virou o nome mais comentado do mercado. 👀', 'neu'),
    ('revelacao', '@antigoat_fc', '{rev} é fogo de palha. Daqui a seis meses ninguém lembra.', 'hate'),
    ('bola', '@numerosdabola', 'Corrida da Bola de Ouro hoje: 1º {bola1}, 2º {bola2}, 3º {bola3}. 🏆', 'num'),
    ('bola', '@resenha_fc', 'Bola de Ouro: {bola1}, {bola2} ou {bola3}? Vota aí 👇', 'neu'),
    ('bola_nosso', '{torc}', 'A Bola de Ouro já tem dono: {nosso_bola}! Não tem discussão! 🏆', 'pos'),
    ('bola_nosso', '@antigoat_fc', 'Se o {nosso_bola} ganhar a Bola de Ouro de novo eu largo o futebol 🙄', 'hate'),
    ('bola_nosso', '@secadorprofissional', 'Bola de Ouro pro {bola_rival}, e não aceito outra resposta 😤', 'hate'),
    ('art_mundo', '@numerosdabola', 'Artilheiro do mundo na temporada: {art_mundo} ({art_mundo_time}), {art_mundo_gols} gols. ⚽📊', 'num'),
    ('art_mundo', '@futebol_raiz', '{art_mundo_gols} gols do {art_mundo}. Tem gente que nasce com o gol no pé.', 'pos'),
    ('art_mundo', '@zoeira_fc', 'Zagueiro que pega o {art_mundo} pela frente já entra em campo rezando 😂', 'meme'),
    # ----- por posição
    ('pos_gk', '{torc}', '{gk} fechou o gol de novo! Paredão é pouco! 🧤', 'pos'),
    ('pos_gk', '@numerosdabola', '{gk}: {gk_sg} jogos sem sofrer gol na temporada. 🧤📊', 'num'),
    ('pos_cb', '{torc}', 'Zagueiro que faz gol é diferente! {cb} já tem {cb_gols}! 🧱⚽', 'pos'),
    ('pos_cb', '@zoeira_fc', 'O {cb} tá com mais gol que muito atacante da liga 😂', 'meme'),
    ('pos_lat', '@tatica_pura', '{lat} vira ponta quando o time ataca: {lat_assist} assistências. Lateral moderno.', 'num'),
    ('pos_vol', '@futebol_raiz', 'Ninguém fala do {vol}, mas sem ele esse time não para em pé. Carregador de piano.', 'pos'),
    # ----- elencos vitoriosos (vitoriosos.py)
    ('obrig', '@secadorprofissional', 'O {nos} tropeçou no {trop_adv}! Cadê o time que ganhava tudo? 😂', 'hate'),
    ('obrig', '{torc}', 'A gente ficou mal-acostumado, mas {trop_placar} com o {trop_adv} não dá. Acorda, time! 😤', 'neg'),
    ('obrig', '@tiozao_do_futebol', 'Time que ganha tudo esquece que o adversário também joga. Lição do {trop_placar}.', 'neu'),
    ('obrig', '@zoeira_fc', 'Torcida do {nos} depois de um tropeço: 😭😭😭 Resto do mundo: 🤷', 'meme'),
    ('joia', '{torc}', 'Coloca o {joia} pra jogar! {joia_idade} anos e talento de sobra 🌱', 'pos'),
    ('joia', '@scout_global', '{joia} ({joia_idade} anos, nota {joia_ovr}) precisa de minutos. Talento desperdiçado no banco.', 'num'),
    ('joia', '@tiozao_do_futebol', 'Esse {joia} tem cara de craque. No meu tempo já estava jogando.', 'pos'),
    ('renov', '{torc}', 'RENOVA COM O {renov_up}!!! Não deixa sair de graça! ✍️', 'pos'),
    ('renov', '@mercadodabola', 'Contrato de {renov} acaba em {renov_meses} meses. Clubes já monitoram. 👀', 'neu'),
    # ----- rumores (rumores.py)
    ('rumor', '{torc}', 'Se venderem o {rum_nome} pro {rum_clube} eu rasgo a carteirinha de sócio 😤', 'neg'),
    ('rumor', '@mercadodabola', 'Fontes: {rum_clube} acompanha {rum_nome} de perto. 👀', 'neu'),
    ('rumor', '@{rum_slug}_raiz', 'Vem, {rum_nome}! Aqui você vai ganhar tudo! 🙌', 'riv'),
    ('rumor', '@zoeira_fc', '{rum_nome} curtindo foto do {rum_clube} às 3 da manhã 👀👀', 'meme'),
    ('rumor', '@tiozao_do_futebol', 'No meu tempo jogador tinha amor à camisa. Hoje é só ligar que ele atende.', 'neg'),
    ('rumor', '@futebol_raiz', 'Vender o {rum_nome} agora seria um erro histórico do {nos}.', 'neu'),
    # ----- Data FIFA (data_fifa.py)
    ('fifa', '{torc}', 'Orgulho dos nossos defendendo as seleções: {fifa_nomes} 🌎', 'pos'),
    ('fifa_gol', '{torc}', '{fifa_art} marcou pela seleção! Esse é dos nossos! ⚽🌎', 'pos'),
    ('fifa_gol', '@numerosdabola', 'Data FIFA: {fifa_art} fez {fifa_gols} gol(s) pela seleção ({fifa_sel}). 📊', 'num'),
    ('fifa_esq', '@futebol_raiz', 'Explica aí: por que o {fifa_esq} ficou fora da seleção? Nota {fifa_esq_ovr}!', 'neg'),
    ('fifa_esq', '@zoeira_fc', '{fifa_esq} assistindo a seleção do sofá com pipoca 🍿📺', 'meme'),
    ('fifa_cans', '@setorista_beto', 'Departamento médico de olho em {fifa_cans}: voltou da seleção com muitos minutos nas pernas. 👀', 'neu'),
    ('fifa', '@tiozao_do_futebol', 'Data FIFA é o terror do torcedor de clube. Volta todo mundo cansado.', 'neu'),
    # ----- rodada e mês (rodada_mes.py)
    ('rodada', '@numerosdabola', 'Seleção da rodada {rd_n}: craque {rd_craque} ({rd_craque_time}). {rd_nossos} do {nos} no time ideal. ⭐', 'num'),
    ('rodada', '{torc}', '{rd_varios} dos nossos na seleção da rodada! Merecido demais 👏', 'pos'),
    ('rodada', '@resenha_fc', 'Seleção da rodada {rd_n} saiu. Quem faltou? 👇', 'neu'),
    ('mes', '@futebol_raiz', '{mes_top} foi o dono de {mes_nome}. {mes_gols} gols no mês. 🏅', 'pos'),
    ('mes', '@antigoat_fc', 'Jogador do mês o {mes_top}? Roubado. Só jogou contra time pequeno 🙄', 'hate'),
    # ----- a história do clube (historia.py)
    ('marco', '{torc}', 'Que orgulho! {marco_txt} 📜🏆', 'pos'),
    ('marco', '@numerosdabola', '{marco_txt} 📊', 'num'),
    ('marco', '@futebol_raiz', 'Tem marca que não se compra: {marco_txt}', 'pos'),
    ('marco', '@antigoat_fc', 'Marca histórica contra time pequeno também conta? 🙄', 'hate'),
    ('art_hist', '@numerosdabola', 'Artilheiro da era no {nos}: {art_hist}, {art_hist_gols} gols desde {hist_desde}. 📊', 'num'),
    ('art_hist', '{torc}', '{art_hist} já é lenda do clube. {art_hist_gols} gols com esta camisa! 👑', 'pos'),
    # ----- sempre
    ('geral', '@memesdabola', 'Torcedor do {nos} conferindo a tabela de 5 em 5 minutos: 👀📱', 'meme'),
    ('geral', '@tiozao_do_futebol', 'Futebol bom era quando o camisa 10 jogava de 10. Hoje é tudo "falso nove".', 'neu'),
    ('geral', '@futebol_raiz', 'Não importa a fase: a arquibancada do {nos} nunca abandona.', 'pos'),
    ('geral', '@vozdageral', 'Café, jornal e a escalação do {nos} na cabeça. Rotina de torcedor. ☕', 'neu'),
    ('geral', '@resenha_fc', 'Qual foi o maior jogo do {nos} que você viu ao vivo? 👇', 'neu'),
    ('geral', '{torc}', 'Se for pra contratar, que seja pra ser titular. Chega de figurante!', 'neu'),
    ('geral', '@toninhomarrento', 'Hoje no Bola na Mesa tem polêmica! Quem vai ficar bravo comigo dessa vez? 😂', 'meme'),
    ('geral', '@carlao_pereira', 'No meu tempo, zagueiro que tomava drible pedia desculpa pra torcida. #BolaNaMesa', 'neu'),
    ('geral', '@helena_saraiva', 'Spoiler do programa: tem dado que vai surpreender muita gente. 📊 #BolaNaMesa', 'num'),
]

RESPOSTAS = {
    'pos': ['Monstro demais 🔥', 'Esse time é outro patamar', 'Concordo 100%', 'Que fase, meu Deus 😍', 'Respeita o {apelido}!',
            'Assinado embaixo ✍️', 'Melhor time do mundo e não aceito discussão', 'Chorei aqui 🥹', 'É o {apelido}, caramba!'],
    'neg': ['Calma, é fase', 'Fora todo mundo!! 😡', 'Respira, ano passado a gente ganhou tudo', 'Faltou atitude mesmo',
            'O técnico tem culpa nisso também', 'Ainda confio nesse grupo 🙏', 'Quero ver reação no próximo jogo'],
    'hate': ['Chora mais 😂', 'Hater não tira folga, né?', 'Pode não gostar, mas tem que respeitar', 'Isso é inveja pura kkkk',
             'Quero ver o seu time ganhar um décimo disso', '@toninhomarrento esse aí precisa de um programa só pra ele 😂'],
    'riv': ['Vem pro jogo que a gente conversa 😂', 'Vocês nem chegam perto', 'Sonhar é de graça 😴', 'Respeito, mas vão perder',
            'Print pra cobrar depois 📸'],
    'num': ['Os números não mentem 📊', 'Absurdo', 'E ainda tem gente que discute', 'Salvei pra jogar na cara de quem duvida',
            'Fonte confiável 👍'],
    'meme': ['KKKKKKKK', 'Eu de novo 😂', 'Melhor post do dia', 'Morri 💀', 'Marca aquele seu amigo que duvidou'],
    'neu': ['Concordo', 'Bom ponto', 'Depende muito do jogo', 'Vamos ver no próximo jogo', 'Discordo, mas respeito'],
}
FAS = ['@ana_{sigla}', '@joaovictor_10', '@tiaze_do_futebol', '@marcelo.rv', '@bia_torcedora', '@gui_camisa10', '@seujorge_fut',
       '@lucas_ultras', '@pedrinho.fc', '@carol.bola', '@rafa_arquibancada', '@dudu_{sigla}', '@leo.fut', '@manu_tatica']

_FMT = string.Formatter()


def _campos(t):
    return {f for _, f, _, _ in _FMT.parse(t) if f}


def _slug(t):
    import unicodedata
    t = unicodedata.normalize('NFKD', t or '').encode('ascii', 'ignore').decode().lower()
    return ''.join(c for c in t if c.isalnum())[:20]


def _n(x):
    return f'{x:.1f}'.replace('.', ',')


# ---------------------------------------------------------------- o contexto do momento
def contexto(M, fase):
    """(campos, categorias ativas) a partir do mundo do Bola na Mesa (bola_na_mesa.mundo)."""
    try:
        from clube import C as CL
        apelido = CL.get('apelido') or M['nos']
    except Exception:  # noqa: BLE001
        apelido = M['nos']
    nos = M['nos']
    c = {'nos': nos, 'nos_up': nos.upper(), 'sigla': M['sigla'], 'torc': f'@{M["sigla"]}_raiz', 'apelido': apelido,
         'apelido_up': apelido.upper()}
    cats = {'geral'}
    u = M.get('ult')
    if fase != 'pre' and u and u['recente']:
        c.update(adv=u['adv'], adv_up=u['adv'].upper(), adv_slug=_slug(u['adv']), gp=u['gp'], gc=u['gc'], saldo=abs(u['gp'] - u['gc']))
        res = 'V' if u['gp'] > u['gc'] else 'E' if u['gp'] == u['gc'] else 'D'
        cats.add({'V': 'vitoria', 'E': 'empate', 'D': 'derrota'}[res])
        if res == 'V' and u['gp'] - u['gc'] >= 3:
            cats.add('goleada')
        nota = [j for j in u['nos'] if j['nota']]
        if nota:
            top = max(nota, key=lambda j: j['nota'] + 0.6 * j['gols'] + 0.3 * j['assist'])
            c.update(craque=top['nome'], craque_up=top['nome'].upper(), nota_craque=_n(top['nota']))
            cats.add('craque_jogo')
            pior = min((j for j in nota if j['min'] >= 45), key=lambda j: j['nota'], default=None)
            if pior and pior['nota'] < 6 and pior is not top:
                c.update(pior=pior['nome'], nota_pior=_n(pior['nota']))
                cats.add('mal_jogador')
        mg = max(u['nos'], key=lambda j: j['gols'], default=None)
        if mg and mg['gols']:
            c.update(autor_gol=mg['nome'], autor_gol_up=mg['nome'].upper(), gols_autor=mg['gols'])
            cats.add('doblete' if mg['gols'] >= 2 else 'gol')
    pj = M.get('pj') or {}
    if fase == 'pre' and pj.get('casa'):
        adv = pj.get('adversario') or (pj['fora'] if pj['casa'] == nos else pj['casa'])
        c.update(prox=adv, prox_slug=_slug(adv), jogo_prox=f'{pj["casa"]} x {pj["fora"]}')
        cats.add('pre')
        pr = pj.get('prob') or {}
        if pr:
            c['prob_nos'] = pr.get('casa') if pj['casa'] == nos else pr.get('fora')
        if pj.get('classico'):
            c.update(classico=pj['classico'], classico_up=pj['classico'].upper())
            cats.add('classico')
        if pj.get('final'):
            c.update(final_comp=pj.get('competicao'), final_comp_up=(pj.get('competicao') or '').upper())
            cats.add('final')
        js = [x for x in ((M.get('dest') or {}).get('clubes') or {}).get(adv) or [] if x['jogos'] >= 3 and x['gols'] >= 3]
        if js:
            c.update(perigo=js[0]['nome'], perigo_gols=js[0]['gols'])
            cats.add('perigo')
    oficiais = [p for p in M.get('jogos') or [] if tuple(p['data']) >= tuple(M['ini']) and not (100 <= p['comp'] <= 110 or p['comp'] == 56)]
    if not oficiais:
        cats.add('pre_temporada')
    eu, tab = M.get('eu'), M.get('tab') or []
    if eu and eu.get('j', 0) >= 5:
        c.update(pos=eu['pos'], pts=eu['pts'], jogos=eu['j'])
        if eu['pos'] == 1:
            cats.add('lider')
        elif eu['pos'] <= 4:
            c.update(dif=tab[0]['pts'] - eu['pts'], lider=tab[0]['time'])
            cats.add('perseguidor')
        elif eu['pos'] >= 7:
            cats.add('mal_tabela')
    J = M.get('J') or []
    art = max(J, key=lambda j: j['t_gols'], default=None)
    if art and art['t_gols'] >= 5:
        c.update(art_time=art['nome'], gols_art=art['t_gols'])
        cats.add('art_time')
    gar = max(J, key=lambda j: j['t_assist'], default=None)
    if gar and gar['t_assist'] >= 4:
        c.update(garcom=gar['nome'], assist_gar=gar['t_assist'])
        cats.add('garcom')
    jov = max((j for j in J if j['idade'] <= 21 and j['t_jogos'] >= 3), key=lambda j: j['t_jogos'], default=None)
    if jov:
        c.update(jovem=jov['nome'], idade_jovem=jov['idade'])
        cats.add('jovem')
    vet = max((j for j in J if j['idade'] >= 33 and j['t_jogos'] >= 3), key=lambda j: j['idade'], default=None)
    if vet:
        c.update(veterano=vet['nome'], idade_vet=vet['idade'])
        cats.add('veterano')
    cap = next((j for j in J if j.get('capitao')), None)
    if cap:
        c['capitao'] = cap['nome']
        cats.add('capitao')
    perfis = M.get('perfis') or {}
    fam = max(((pf['fama'], k) for k, pf in perfis.items() if pf.get('bolas')), default=None)
    if fam:
        j = next((j for j in J if j['k'] == fam[1]), None)
        if j:
            c.update(estrela=j['nome'], bolas=len(perfis[fam[1]]['bolas']))
            cats.add('estrela')
    D = M.get('dest') or {}
    rv = next((x for x in D.get('revelacoes') or [] if x['gols'] + x['assist'] >= 6), None)
    if rv:
        c.update(rev=rv['nome'], rev_time=rv['time'], rev_gols=rv['gols'], rev_idade=rv['idade'], rev_ovr=rv['ovr'], rev_slug=_slug(rv['time']))
        cats.add('revelacao')
    bo = D.get('bola_de_ouro') or []
    if len(bo) >= 3 and D.get('max_jogos', 0) >= 8:
        c.update(bola1=bo[0]['nome'], bola2=bo[1]['nome'], bola3=bo[2]['nome'])
        cats.add('bola')
        meu = next((x for x in bo[:3] if x['nosso']), None)
        rival = next((x for x in bo[:3] if not x['nosso']), None)
        if meu and rival:
            c.update(nosso_bola=meu['nome'], bola_rival=rival['nome'])
            cats.add('bola_nosso')
    try:   # por posição (12/10/2026)
        import bola_na_mesa as _b
        gks = [j for j in J if j['pos'] == 'GK' and j['t_jogos'] >= 4]
        if gks:
            g = max(gks, key=lambda j: j['t_jogos'])
            sg = _b._sem_sofrer(M, g['k'])
            if sg >= 3:
                c.update(gk=g['nome'], gk_sg=sg)
                cats.add('pos_gk')
    except Exception:  # noqa: BLE001
        pass
    z = max((j for j in J if j['pos'] == 'CB' and j['t_gols'] >= 2), key=lambda j: j['t_gols'], default=None)
    if z:
        c.update(cb=z['nome'], cb_gols=z['t_gols'])
        cats.add('pos_cb')
    lt = max((j for j in J if j['pos'] in ('LB', 'RB') and j['t_assist'] >= 3), key=lambda j: j['t_assist'], default=None)
    if lt:
        c.update(lat=lt['nome'], lat_assist=lt['t_assist'])
        cats.add('pos_lat')
    vo = max((j for j in J if j['pos'] in ('DMF', 'CMF') and j['t_jogos'] >= 6 and j['t_gols'] + j['t_assist'] <= 2), key=lambda j: j['t_jogos'], default=None)
    if vo:
        c['vol'] = vo['nome']
        cats.add('pos_vol')
    VT = M.get('vit') or {}
    import datetime as _d2
    _dd = lambda x: (_d2.date(*M['hoje']) - _d2.date(*x)).days
    if VT.get('tropeco') and _dd(VT['tropeco']['data']) <= 6:
        t = VT['tropeco']
        c.update(trop_adv=t['adv'], trop_placar=f'{t["gp"]} x {t["gc"]}')
        cats.add('obrig')
    if VT.get('joia') and _dd(VT['joia']['data']) <= 14:
        c.update(joia=VT['joia']['nome'], joia_idade=VT['joia']['idade'], joia_ovr=VT['joia']['ovr'])
        cats.add('joia')
    if VT.get('renovacoes') and _dd(VT.get('data') or M['hoje']) <= 14:
        x = VT['renovacoes'][0]
        c.update(renov=x['nome'], renov_up=x['nome'].upper(), renov_meses=x['meses'])
        cats.add('renov')
    RM = sorted(M.get('rumores') or [], key=lambda x: -x['calor'])
    if RM:
        c.update(rum_nome=RM[0]['nome'], rum_clube=RM[0]['clube'], rum_slug=_slug(RM[0]['clube']))
        cats.add('rumor')
    F = M.get('fifa')
    import datetime as _d1
    if F and (_d1.date(*M['hoje']) - _d1.date(*F['data'])).days <= 10:
        if F['convocados']:
            c['fifa_nomes'] = ', '.join(x['nome'] for x in F['convocados'][:4])
            cats.add('fifa')
            art = max(F['convocados'], key=lambda x: x['gols'])
            if art['gols']:
                c.update(fifa_art=art['nome'], fifa_gols=art['gols'], fifa_sel=art['selecao'].title())
                cats.add('fifa_gol')
        if F['esquecidos']:
            c.update(fifa_esq=F['esquecidos'][0]['nome'], fifa_esq_ovr=F['esquecidos'][0]['ovr'])
            cats.add('fifa_esq')
        if F['cansados']:
            c['fifa_cans'] = F['cansados'][0]['nome']
            cats.add('fifa_cans')
    RD = M.get('rd') or {}
    import datetime as _d0
    _rec = lambda x, dias: x and (_d0.date(*M['hoje']) - _d0.date(*x['data'])).days <= dias
    if _rec(RD.get('rodada'), 8):
        x = RD['rodada']
        c.update(rd_n=x['rodada'], rd_craque=x['craque']['nome'], rd_craque_time=x['craque']['time'], rd_nossos=len(x['nossos']))
        if len(x['nossos']) >= 2:
            c['rd_varios'] = len(x['nossos'])
        cats.add('rodada')
    if _rec(RD.get('mes'), 12):
        x = RD['mes']
        c.update(mes_top=x['top']['nome'], mes_nome=x['mes'], mes_gols=x['top']['gols'])
        cats.add('mes')
    H = M.get('hist') or {}
    import datetime as _dt
    rec = [m for m in H.get('marcos') or [] if (_dt.date(*M['hoje']) - _dt.date(*(int(x) for x in m['data'].split('-')))).days <= 10]
    if rec:
        c['marco_txt'] = rec[0]['texto']
        cats.add('marco')
    ah = (H.get('artilheiros') or [None])[0]
    if ah and ah['gols'] >= 50:
        c.update(art_hist=ah['nome'], art_hist_gols=ah['gols'], hist_desde=H.get('desde', ''))
        cats.add('art_hist')
    am = (D.get('artilheiros') or [None])[0]
    if am and am['gols'] >= 8 and not am['nosso']:
        c.update(art_mundo=am['nome'], art_mundo_time=am['time'], art_mundo_gols=am['gols'])
        cats.add('art_mundo')
    return c, cats


PESO_CAT = {'vitoria': 3, 'empate': 3, 'derrota': 3, 'goleada': 3, 'craque_jogo': 2.5, 'doblete': 2.5, 'gol': 2, 'mal_jogador': 2,
            'pre': 3, 'classico': 4, 'final': 4, 'perigo': 2.5, 'pre_temporada': 2.5, 'lider': 1.5, 'perseguidor': 1.5,
            'mal_tabela': 2, 'revelacao': 1.8, 'bola': 1.4, 'bola_nosso': 1.6, 'art_mundo': 1.2, 'estrela': 1.2,
            'art_time': 1.3, 'garcom': 1.1, 'marco': 4, 'art_hist': 0.7, 'rodada': 1.6, 'mes': 2, 'fifa': 1.5, 'fifa_gol': 2.5, 'fifa_esq': 2.5, 'fifa_cans': 1.5, 'rumor': 2.6, 'obrig': 3.5, 'joia': 2, 'renov': 1.8, 'pos_gk': 1.5, 'pos_cb': 1.6, 'pos_lat': 1.2, 'pos_vol': 1.0, 'jovem': 1, 'veterano': 0.8, 'capitao': 0.7, 'geral': 0.6}


# pauta do programa -> categorias de post que ela já cobre (o assunto não aparece 4 vezes no feed)
PAUTA_CAT = {'resultado': ('vitoria', 'empate', 'derrota'), 'craque_do_jogo': ('craque_jogo',), 'revelacao': ('revelacao',),
             'artilheiro_time': ('art_time',), 'bola_de_ouro': ('bola',), 'artilharia_mundial': ('art_mundo',),
             'perigo_adversario': ('perigo',), 'lenda': ('estrela',), 'garcom': ('garcom',), 'jovem_promessa': ('jovem',),
             'veterano': ('veterano',), 'lideranca': ('lider',), 'classico': ('classico',), 'final_pre': ('final',),
             'previa': ('pre',), 'goleada_nossa': ('goleada',), 'decepcao': ('mal_jogador',), 'marco_historico': ('marco',), 'selecao_rodada': ('rodada',), 'jogador_mes': ('mes',), 'data_fifa': ('fifa_gol', 'fifa_esq'), 'rumor_mercado': ('rumor',), 'obrigacao_vencer': ('obrig',), 'joia_base': ('joia',), 'renovacao_pauta': ('renov',), 'goleiro_paredao': ('pos_gk',), 'zagueiro_artilheiro': ('pos_cb',), 'lateral_garcom': ('pos_lat',), 'volante_carregador': ('pos_vol',)}


def posts(M, fase, rnd, n=9, ja=(), pautas=()):
    """n posts novos [(autor, texto, categoria, tom)] coerentes com o momento; evita textos já publicados e dá só
    1 post extra para assunto que o programa já levou para a rede."""
    c, cats = contexto(M, fase)
    vistos = {t for t in ja}
    cobertas = {x for p in pautas for x in PAUTA_CAT.get(p, ())}
    cands = []
    for cat, autor, texto, tom in M_:
        if cat not in cats or not (_campos(autor) | _campos(texto)) <= set(c):
            continue
        t = texto.format(**c)
        if t in vistos:
            continue
        cands.append((PESO_CAT.get(cat, 1) * rnd.uniform(0.4, 1.6), autor.format(**c), t, cat, tom))
    cands.sort(key=lambda x: -x[0])
    out, por_autor, por_cat = [], {}, {}
    for _, a, t, cat, tom in cands:
        if len(out) >= n or por_autor.get(a, 0) >= 2 or por_cat.get(cat, 0) >= (1 if cat in cobertas else 3):
            continue
        out.append((a, t, cat, tom))
        por_autor[a] = por_autor.get(a, 0) + 1
        por_cat[cat] = por_cat.get(cat, 0) + 1
    return out, c


def respostas(tom, autor, c, rnd, curtidas):
    """Até 3 comentários de outros perfis embaixo do post."""
    banco = RESPOSTAS.get(tom) or RESPOSTAS['neu']
    k = rnd.choices([0, 1, 2, 3], weights=[2, 4, 3, 2])[0]
    out, usados, quem_ja = [], set(), {autor}
    for _ in range(k):
        t = rnd.choice(banco)
        quem = rnd.choice(FAS).format(sigla=c.get('sigla', 'fc'))
        if t in usados or quem in quem_ja:
            continue
        usados.add(t)
        quem_ja.add(quem)
        out.append({'autor': quem, 'texto': t.format(**{k2: v for k2, v in c.items() if isinstance(v, (str, int))}),
                    'curtidas': max(1, int(curtidas * rnd.uniform(0.002, 0.04)))})
    return out


def tom_de(autor, texto):
    """Tom de um post que veio das pautas do programa (para escolher as respostas)."""
    a = autor.lower()
    if 'antigoat' in a or 'secador' in a:
        return 'hate'
    if 'zoeira' in a or 'memes' in a:
        return 'meme'
    if 'numeros' in a:
        return 'num'
    if a.endswith('_raiz') and '😤' in texto:
        return 'riv'
    if any(x in texto for x in ('😡', '💔', 'Vergonha', 'vergonha', 'Inadmissível', 'Dói')):
        return 'neg'
    if any(x in texto for x in ('🔥', '🏆', '!!!', '🐐', '😍')):
        return 'pos'
    return 'neu'
