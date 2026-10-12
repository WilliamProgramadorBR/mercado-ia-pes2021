# Pesquisa: como o simulador do PES 2021 escolhe a escalação dos clubes da IA

Objetivo: nos jogos simulados (IA x IA), os clubes devem escalar os melhores na maioria das vezes, com rodízio
realista (cansaço, seta muito ruim, jogo menos importante), e não quase ao acaso como hoje.

## O que já sabemos (12/10/2026, temporada 2034/35 + início de 2035/36)

- Jogo simulado grava a súmula com exatamente 11 jogadores por time, todos titulares, 90 minutos, sem substituição.
- Um dos 10 melhores jogadores de linha dos 30 maiores clubes começa jogando só **54%** das vezes
  (liga 53%, copa 55%, Champions 51%).
- Não é cansaço: a condição física dos jogadores da IA fica em 95+; quem não jogou nada na semana começa só 51%.
- A seta pesa um pouco: seta 0 = 35-40%, seta 4 = 60-65%.
- Elenco inchado piora: melhor do setor começa 62% com até 24 jogadores e 53% com 33+.
- A escalação gravada no bloco tático de cada clube (save 0x133C50 + bloco*600, +0) vale para o USUÁRIO (bate 100%),
  mas é ignorada para os clubes da IA (4,5 de 11 em comum com o jogo seguinte, o mesmo que o acaso).

Conclusão: a escolha acontece dentro do código do simulador, no executável. Não há dado no save que a controle.

## Plano

### Fase A — achar o código (só leitura, jogo aberto numa cópia da carreira)
1. Antes de avançar o calendário, localizar na memória a PRÓXIMA súmula que o jogo vai gravar (registros de
   596 bytes; o pulso já lê essa área e sabe o número do próximo jogo).
2. Colocar um ponto de parada de ESCRITA (breakpoint de hardware) nos bytes das linhas dos jogadores dessa súmula.
3. Avançar um dia no calendário. Quando o simulador escrever a escalação, o depurador para e mostra a instrução;
   a pilha de chamadas leva à função que escolheu os 11.

Ferramenta: x64dbg (gratuito) com o plugin ScyllaHide (esconde o depurador do jogo). Alternativa sem instalar nada:
um mini-depurador em Python (API de depuração do Windows: DebugActiveProcess + registradores DR0-DR3), feito por nós.

### Fase B — entender a regra
Desmontar a função (Ghidra, que precisa de Java 21, ou a biblioteca capstone no Python) e descobrir os pesos:
nota, seta, posição, sorteio. Esperado: um sorteio ponderado com peso pequeno para a nota.

### Fase C — corrigir
Escrever um módulo do Sider (como o AI_Tweaks) que, ao abrir o jogo, procura o trecho do código pelo padrão de bytes
e troca só os valores da regra (ex.: aumentar o peso da nota, reduzir o sorteio). Com:
- chave para ligar e desligar;
- conferência do padrão (se o executável for diferente, o módulo não mexe em nada);
- teste numa CÓPIA da carreira: simular algumas rodadas e medir de novo (meta: craque começa 75-85%).

## Riscos
- O jogo pode fechar se perceber o depurador (por isso ScyllaHide e cópia da carreira).
- Trabalho de pesquisa: pode levar várias sessões; o resultado não é garantido.
- Nada é alterado no jogo real até a Fase C passar no teste da cópia.

## Medição (antes e depois)
Scripts em scratchpad/sinergia (copiar para cá quando estabilizar): `rodizio.py`, `setas.py`, `posicao.py`,
`realismo.py` (favorito vence quanto, correlação força x tabela, finalistas da Champions).

## Resultado (12/10/2026)

Achado com o x64dbg (ponto de parada de escrita na súmula de um jogo simulado e, depois, na escalação de um clube):

- A função que joga a partida simulada (`0x141332010`) chama o "técnico da IA" (`0x1414FF0E0` → `0x141504580`)
  com o **modo 3** fixo no código (`0x1413321FC`: `mov dword ptr [rbp+0xE4], 3`). No modo 3 a escalação guardada é
  descartada e outra é montada quase ao acaso.
- O **modo 1** mantém a escalação guardada e só troca quem está indisponível (lesão, suspensão).
- O registro de cada clube (600 B) começa em +56 do "bloco" que usávamos; a **escalação** (40 B: posição no elenco
  de cada vaga, 11 primeiros = titulares), os cobradores e o capitão ficam no **fim** do registro.
- A súmula de um jogo simulado guarda quem **terminou** em campo (3 substituições na mesma posição).

Teste (11 clubes, rodada da Champions de 20/10/2035): os 11 escritos entraram em campo; as 3 diferenças por clube
foram as substituições.

Solução em uso: `cerebro/escalacao_ia.py` + `central._tecnico_ia_thread` — patch 3 → 1 só na memória (o executável
não é alterado) e, antes de cada rodada, a escalação de cada clube da IA escrita com os melhores por posição e rodízio
realista (jogo grande = força máxima; jogo menor = descanso para quem jogou 2+ vezes na semana). O time do usuário
nunca é tocado.
