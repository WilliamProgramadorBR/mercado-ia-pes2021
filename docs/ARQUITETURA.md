# Arquitetura

## Natureza da IA

O Mercado IA é um sistema especialista: observa o estado da carreira, aplica regras de futebol e economia, avalia alternativas e escolhe ações sob restrições. Ele possui memória persistente, mas ainda não aprende os próprios pesos a partir dos resultados.

## Componentes

### Captura

`MercadoIA.lua` fotografa uma região somente leitura da memória. A foto contém atributos atuais dos jogadores da carreira, inclusive evolução e regens.

### Reconstrução

`dados.py` identifica fichas de 380 bytes e decodifica atributos, posições, estilos e habilidades. `save_ml.py` reconstrói times, elencos, camisas, contadores e formações a partir do save descriptografado.

### Avaliação esportiva

`encaixe.py` escala o melhor XI dentro da formação real e mede:

- força estimada;
- complementaridade de estilos;
- profundidade;
- idade do XI e ciclo do elenco.

### Mercado

`mercado.py` executa rodadas. Clubes mais fortes agem primeiro, vendedores podem reagir nas rodadas seguintes e um atleta não pode ser transferido duas vezes na mesma janela.

Cada candidato combina ganho tático, posição natural, idade, preço, nível do vendedor e identidade do comprador. O clube vendedor rejeita negócios que destruam seu XI sem uma justificativa econômica suficiente.

### Identidade e memória

`memoria_clubes.py` mantém um arquivo separado por carreira. A identidade inicial considera força e composição etária; pequenas diferenças determinísticas evitam clubes idênticos.

O livro-caixa registra compras, vendas, investimento, receita e orçamento remanescente. A cada nova temporada entra uma receita proporcional ao tamanho e à ambição do clube.

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

- os endereços de memória são específicos da versão testada;
- o orçamento é uma simulação externa, não o caixa interno de todos os clubes;
- salários, agentes, vontade do jogador e resultados esportivos ainda não são lidos;
- empréstimos e contratações de jogadores livres permanecem experimentais;
- o módulo `tecnico.py` ainda não faz parte do fluxo de aplicação padrão;
- a formação é conhecida, mas as instruções táticas completas ainda não entram na pontuação.
