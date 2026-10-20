# Arquitetura

## Natureza da IA

O Mercado IA combina duas abordagens.

**Regras de especialista com memória.** O mercado, o vestiário, a diretoria e a imprensa observam o estado da carreira, aplicam regras de futebol e economia, avaliam alternativas e escolhem ações sob restrições. Essas regras não ajustam os próprios pesos: o que muda com o tempo é a memória (livro-caixa, identidade dos clubes, histórico da carreira).

**Componentes que aprendem com os resultados.** Três partes se ajustam a cada jogo do usuário:

- **Estatística do duelo** (`duelo.py`): regressão ridge do saldo de gols, puxada para valores de referência e com peso maior nos jogos recentes, reajustada a cada jogo. Inclui o "momento" do usuário (média rápida menos média lenta do quanto ele superou o esperado).
- **Rede neural** (`rede_v3.py`): comitê de cinco redes residuais pequenas que corrigem só o saldo previsto pela estatística. É retreinada do zero a cada jogo, num processo separado, com peso por recência. A cada 100 jogos novos, um reajuste automático testa tamanhos, regularizações e recências andando no tempo e só troca a configuração se a nova ganhar.
- **IA adversária** (`ia_adversaria.py`): aprende quais características de plano funcionam contra o usuário. A recompensa de cada jogo é o saldo acima do esperado, descontado o erro recente da prévia e limitado a ±2 gols. A escolha entre os planos candidatos usa amostragem de Thompson, e o aprendizado antigo perde 3% de peso a cada jogo.

Quem lidera o duelo (estatística ou rede, pelos pontos do bolão nos últimos 100 jogos) decide o plano do adversário. Toda mudança nos modelos é validada com teste andando no tempo (treina só com os jogos anteriores e prevê o seguinte) antes de entrar.

## Componentes

### Captura

`memoria.py` fotografa a memória do jogo **de fora**, pelo Windows (`ReadProcessMemory`/`VirtualQueryEx`), lendo só regiões comprometidas e legíveis. A foto contém os atributos atuais dos jogadores da carreira, inclusive evolução e regens. O módulo `MercadoIA.lua` (Sider) não lê nem escreve memória: ele só registra o pedido do usuário (teclas no jogo), e o vigia tira a foto.

### Reconstrução

`dados.py` identifica fichas de 380 bytes e decodifica atributos, posições, estilos e habilidades. `save_ml.py` reconstrói times, elencos, camisas, contadores e formações a partir do save descriptografado. Outros leitores do save trazem súmulas, classificação, finanças, contratos, plano de jogo e o desempenho do clube.

### Avaliação esportiva

`encaixe.py` escala o melhor XI dentro da formação real e mede:

- força estimada;
- complementaridade de estilos;
- profundidade;
- idade do XI e ciclo do elenco.

### Mercado

`mercado.py` executa rodadas. Clubes mais fortes agem primeiro, vendedores podem reagir nas rodadas seguintes e um atleta não pode ser transferido duas vezes na mesma janela.

Cada candidato combina ganho tático, posição natural, idade, preço, nível do vendedor e identidade do comprador. O clube vendedor rejeita negócios que destruam seu XI sem uma justificativa econômica suficiente. Dois sinais refinam a escolha:

- o **encaixe no plano de jogo** do comprador (`encaixe_plano.py`: estilo e instruções avançadas), que só ordena candidatos que já passaram por todas as regras;
- a **insatisfação dos jogadores** nos clubes da IA (`vestiario_ia.py`: minutos abaixo do esperado), que baixa o preço e facilita a saída.

### Identidade e memória

`memoria_clubes.py` mantém um arquivo separado por carreira. A identidade inicial considera força e composição etária; pequenas diferenças determinísticas evitam clubes idênticos.

O livro-caixa registra compras, vendas, investimento, receita e orçamento remanescente. A cada nova temporada entra uma receita proporcional ao tamanho e à ambição do clube.

O que o jogo apaga na virada de temporada (súmulas, estatísticas, desempenho do clube) é guardado antes no banco `historico/imprensa.db`, uma linha por temporada.

### Transação segura

`aplicar.py`:

1. cria backup;
2. descriptografa uma cópia;
3. aplica apenas transferências ainda válidas;
4. atualiza elenco, camisas, contadores e escalações;
5. recriptografa;
6. descriptografa novamente;
7. compara o `data.dat` resultante byte a byte;
8. verifica se o save original não mudou durante o processo;
9. substitui o save;
10. só então confirma a janela e a memória econômica.

## Limitações conhecidas

- os endereços de memória são específicos da versão testada (PES 2021 1.1.0.0);
- o orçamento dos clubes da IA é uma simulação externa; só o orçamento do usuário é o valor real do save;
- salários e agentes ainda não entram nas negociações do mercado;
- empréstimos e contratações de jogadores livres permanecem experimentais;
- o módulo `tecnico.py` ainda não faz parte do fluxo padrão; a escalação dos clubes da IA é feita por `escalacao_ia.py`;
- os componentes que aprendem dependem de partidas **jogadas** pelo usuário (o jogo não registra estatísticas das simuladas) e começam neutros numa carreira nova.
