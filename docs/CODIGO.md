# Mercado IA: guia completo do código e do propósito

**Autor:** William ([github.com/WilliamProgramadorBR](https://github.com/WilliamProgramadorBR)), com Claude (Anthropic) como par de programação.

## 1. Propósito

O Mercado IA transforma a Master League do eFootball PES 2021 numa **vida de técnico**. O jogo original simula o resto do mundo de forma pobre: clubes da IA não contratam com lógica, escalam quase ao acaso, a imprensa é genérica e o adversário não estuda você. O projeto resolve isso por fora do jogo, sem mexer no executável:

- **Mercado inteligente:** cada clube da IA tem identidade, economia e carências, e negocia com lógica.
- **Vestiário:** moral, status, conflitos, pedidos dos jogadores, disciplina e torcida. A moral vira a seta de condição dentro do jogo.
- **Imprensa viva:** jornais com tons diferentes, coletivas com consequências, o programa *Bola na Mesa*, redes sociais e análises pós-jogo que explicam o porquê do resultado.
- **IA adversária:** o técnico do computador estuda o seu time, monta um plano dentro do estilo do clube e aprende com o resultado. **Nunca há atributos turbinados**, só tática.
- **Técnico da IA:** corrige o rodízio quase aleatório do simulador da Konami (os clubes passam a escalar os melhores) e poupa jogadores antes de jogos grandes.
- **Diretor de campeonato:** quem disputa título, vaga ou rebaixamento joga com força máxima, conforme a liga aperta.
- **Duelo estatística × rede neural:** dois modelos disputam quem prevê melhor os jogos; quem vence decide.
- **Painel:** aplicativo que reúne tudo isso, com instalador para a comunidade.

O princípio geral: **tudo nasce de dados reais do jogo**, como o save, a memória e as súmulas. Quando um dado não existe, o projeto não inventa um número.

## 2. Arquitetura

```text
PES 2021 ── Sider ── MercadoIA.lua (foto da memória, overlay, teclas 8/9/1/2/3)
   │
   ├─ salva a carreira (ML0000000X, criptografado)
   │
Painel (Qt6) ── liga e supervisiona os serviços, mostra tudo
   ├─ vigia.py      percebe o save novo → descriptografa uma cópia (pesXdecrypter) →
   │                mercado (aplicar.py) e reunião do vestiário (aplicar_vestiario.py) →
   │                recriptografa, confere byte a byte e troca o save (troca_save.py)
   └─ central.py    servidor local (http://127.0.0.1:8765): página da Central, pulso ao vivo da memória,
                    técnico da IA (escalações), IA adversária (táticas), duelo, imprensa ao vivo
```

Toda leitura ou escrita na **memória** do jogo usa ReadProcessMemory/WriteProcessMemory (`memoria.py`, `ao_vivo.py`), e cada escrita confere o valor antes e depois. O executável não tem ASLR (base `0x140000000`). Toda edição do **save** acontece numa cópia, que só é instalada depois da criptografia e da conferência de ida e volta.

## 3. Pastas

| Pasta | Conteúdo |
|---|---|
| `cerebro/` | o motor (Python, só biblioteca padrão) e a Central (`central/index.html`) |
| `cerebro/historico/` | dados da carreira, gerados (nunca vão para o git nem para o pacote) |
| `painel/` | o aplicativo Qt6 (PySide6) |
| `empacotar/` | o montador do pacote (Python embutido) e o instalador (Inno Setup) |
| `sider/` | `MercadoIA.lua`, o módulo carregado pelo Sider |
| `pesquisa/` | engenharia reversa do simulador e as ferramentas de medição |
| `docs/` | manual do jogador, arquitetura, dependências, empacotamento e este guia |

## 4. Os módulos do `cerebro/`

### 4.1 Base: caminhos, save e memória

| Módulo | Função |
|---|---|
| `caminhos.py` | Fonte única das pastas. A ordem de prioridade é: variável de ambiente, depois `config.json`, depois o padrão. Detecta o jogo (Steam e registro) e os saves (Documentos, inclusive no OneDrive). Dentro do Painel, esconde as janelas dos programas auxiliares. |
| `save_ml.py` | Lê e escreve a tabela de times e elencos no `data.dat` descriptografado. |
| `dados.py` | Fichas dos cerca de 24 mil jogadores a partir da foto da memória (`mercado_snap.bin`). |
| `memoria.py` | Foto da memória tirada de fora do jogo, mais o PID do jogo. |
| `ao_vivo.py` | Escrita na memória com conferência: setas, mensagens, apelidos, orçamento. |
| `troca_save.py` | Troca segura do save: confere, faz backup e troca de forma atômica. |
| `carreira.py` | Descobre qual é o time do usuário em qualquer carreira. |
| `jogadores_save.py` | Registro de 156 B de cada jogador (inclui o contador de lesão em +116). |
| `partidas_save.py` | Súmulas e calendário (`todas`, `agenda`). |
| `liga_save.py` | A classificação que o próprio jogo guarda. |
| `estatisticas_save.py` | Estatísticas detalhadas dos jogadores. |
| `financas_save.py` | Finanças do clube do usuário. |
| `mensagens_save.py` | Caixa de mensagens nativa: leitura e inserção. |
| `premios_save.py` | Prêmios individuais e time do mês. |
| `tatica_save.py` | Plano de jogo dos clubes. São blocos de 600 B a partir de `0x133C50`: planos, instruções avançadas e escalação em bloco+600. |
| `familiaridade.py` | Entrosamento tático do elenco do usuário, com os números do jogo. |
| `selecoes.py` | Onde começam as seleções na tabela de times, pelos dados do save (jogador de seleção também está num clube; clube nunca repete jogador), sem depender do idioma do patch. |
| `temporada.py` | A liga e o calendário de qualquer carreira (europeia ou de ano civil). |
| `trava.py` | Trava entre processos. |
| `unica.py` | Garante uma única cópia do vigia e da Central. |

### 4.2 Mercado de transferências

| Módulo | Função |
|---|---|
| `mercado.py` | Motor de decisão: diagnóstico, alvos, propostas e limites. Elencos de no máximo 28 jogadores, com corte de excedentes. |
| `aplicar.py` | Aplica uma janela de transferências no save (tem o modo `--ensaio`). |
| `simular.py` | Simula uma janela sem gravar nada. |
| `encaixe.py` | Força do XI, encaixe de estilos, profundidade e ciclo. Calcula a nota por posição, inclusive a aptidão em posição secundária (`pp_POS`). |
| `encaixe_plano.py` | Bônus para quem encaixa no plano de jogo do clube comprador. |
| `comparar_mercado.py` | Ensaio do mercado com e sem esse encaixe. |
| `memoria_clubes.py` | Perfis e livro-caixa persistente dos clubes da IA. |
| `janela.py` | Lembra o que já foi feito em cada janela. |
| `potencial.py` | Potencial estimado e origem do jogador. |
| `vestiario_ia.py` | Insatisfeitos nos clubes da IA. |
| `tecnico.py` | Escalação preferida dentro da formação de cada clube. |

### 4.3 Vestiário e vida de técnico

| Módulo | Função |
|---|---|
| `vestiario.py` | Relatório do elenco: status, moral, conflitos e líderes. Também carrega a foto da memória. |
| `aplicar_vestiario.py` | **A reunião.** Roda a cada save e orquestra tudo: moral → setas, mídia, liga, próximo jogo, corrida, momento, destaques, história, Data FIFA, lesões, análise, celular, rumores e Central. |
| `decisoes.py` | Pedidos dos jogadores e decisões do técnico. |
| `humor.py` | Modificadores de moral a partir de fatos reais. |
| `exigencias.py` | Perfil e exigências de cada jogador. |
| `disciplina.py` | Casos de disciplina. |
| `crises.py` | Crises, imagem do clube e patrocinador. |
| `calendario.py` | Rodízio e calendário. |
| `compromissos.py` | Promessas do técnico, cobradas pela súmula. |
| `diretoria.py` | Metas e confiança do presidente. |
| `diretoria_nativa.py` | A diretoria do próprio jogo. |
| `patrocinio.py` | Atratividade do clube e contratos. |
| `dificuldade.py` | Dificuldade dinâmica do vestiário. |
| `torcida.py` | Termômetro da arquibancada. |
| `celular.py` | Mensagens do celular do técnico. |
| `rumores.py` | Rumores de mercado sobre os jogadores do usuário. |
| `saidas.py` | Saídas e chegadas do elenco, com a narrativa de cada uma. |
| `vitoriosos.py` | Obrigação de vencer, renovações e jóias da base. |
| `lesoes.py` | Departamento médico: detecta a lesão, avalia o cenário completo e acompanha a volta. |
| `apelidos.py` | Apelidos nativos dados pela torcida. |
| `legado.py` | Memória do mundo: Bolas de Ouro, títulos e perfis. |
| `historia.py` | Livro dos recordes da era do usuário. |
| `marcos.py` | Finais e títulos. |
| `classicos.py` | Rivalidades reais. |
| `clube.py` | Identidade do clube nos textos. Também corrige o artigo ("a Fiorentina") e a caixa dos nomes de time. |

### 4.4 Imprensa

| Módulo | Função |
|---|---|
| `midia.py` | Fatos da rodada, capas dos três jornais, programa e coletiva. |
| `jornal_extra.py` | Texto de abertura, aspas de jogadores e quadros. |
| `imprensa.py` | As frentes (pré-jogo, pós-jogo, liga, mundo...) e as matérias ao vivo. |
| `imprensa_db.py` | Banco SQLite da imprensa. |
| `imprensa_mundo.py` | Prêmios e revelações. |
| `midia_liga.py` | Cobertura da liga inteira. |
| `destaques.py` | Números de todos os jogadores do mundo. |
| `rodada_mes.py` | Seleção da rodada e jogador do mês. |
| `time_do_mes.py` | Time do mês oficial comparado com a seleção da imprensa. |
| `data_fifa.py` | Jogadores do clube nas seleções. |
| `viradas.py` | Viradas em mata-mata. |
| `confronto.py` | O 4 x 4 do jogo da rodada. |
| `analise_tatica.py` | Relatório da comissão técnica. |
| `proximo_jogo.py` | Prévia, probabilidades, enquete e a disputa em jogo. |
| `coletiva_cenarios.py` | Coletivas: o contexto e o sorteio. Total de 137 cenários. |
| `coletiva_extra.py` | Coletivas, lote 2: lesões, a IA adversária e a corrida. |
| `coletiva_momento.py` | Coletivas, lote 3: o momento acumulado. |
| `coletiva_viva.py` | Coletiva no dia do jogo. |
| `momento.py` | **O momento acumulado:** sequência, a tabela **oficial** agora comparada com duas rodadas atrás (rival que encostou ou disparou, liderança), semana decisiva e o clima do time. |
| `analise_jogo.py` | Pós-jogo que explica o porquê, em três veículos fictícios: Mesa Tática, Plantão do Esporte e Resenha Raiz. |
| `bola_na_mesa.py` | O programa de TV e as enquetes. |
| `pautas_momento.py` | Pautas do momento no programa. |
| `redes_falas.py` | Banco de posts e comentários das redes sociais. |
| `redes_vivas.py` | Redes ligadas ao momento: contas oficiais, jogadores, threads, citações, "Em alta" e o ritmo do feed. |
| `segredos.py` | Chave do Gemini no `.env`, criptografada pela conta do Windows (DPAPI); ordem de leitura: variável de ambiente → `.env` → `ia.json` antigo. |
| `redator.py` | IA de texto **opcional** (Google Gemini, com a chave do próprio usuário) que reescreve no estilo de cada veículo. |

### 4.5 As IAs de jogo

| Módulo | Função |
|---|---|
| `escalacao_ia.py` | **Técnico da IA.** Um patch só na memória troca o modo 3 do simulador para o modo 1 (o jogo passa a respeitar a escalação guardada), e o módulo escreve a escalação de cada clube com importância do jogo (decisivo, grande, normal, menor, poupar, relax). Também faz os palpites do duelo e consulta o líder no rodízio. |
| `disputa.py` | **Diretor de campeonato:** a pressão de cada time é a proximidade da linha da zona multiplicada pelo momento da temporada. |
| `olheiro.py` | Estuda o usuário: plano de jogo, ameaças, velocidade, jogo aéreo e vulnerabilidades (lateral fraco, armador, zaga lenta, laterais que sobem). Ignora jogadores lesionados. |
| `ia_adversaria.py` | **IA adversária**, em etapas: postura dentro da identidade do clube, personalidade do técnico, contra-olheiro, instruções avançadas, candidatos, escolha (amostragem de Thompson ou rede neural, conforme o duelo) e aprendizado. Os planos originais são devolvidos byte a byte. |
| `rede.py` | Rede neural pequena em Python puro: camada tanh, saídas de Poisson e treino com Adam. Converte gols esperados em palpite de placar e calcula os pontos do bolão. |
| `duelo.py` | **Duelo estatística × rede:** as duas arenas, palpites, pontuação, liderança em 100 jogos e aprendizado contínuo. Nos seus jogos (v2), a estatística é uma regressão que se ajusta aos jogos recentes, e os dois modelos enxergam a ficha do jogo e explicam o palpite (`porque_est`/`porque_rede`). |
| `desempenho_save.py` | **Desempenho do clube** (tela Informações do time › Desempenho do clube), só leitura: área de jogo e de desarme, posse, chutes, passes, gols por período e tipos de gol, feitos e sofridos, mais a tabela da temporada por jogador. Guarda uma foto por reunião (`historico/desempenho_hist.json`) e devolve os últimos N jogos antes de uma data, sem olhar o futuro e sem usar foto velha. Cada temporada também fica para sempre no banco (`imprensa.db`, tabela `hist_desempenho`), como a história do clube: o jogo zera esses números na virada. |
| `mercado_fluxo.py` | **Fluxo do mercado** para a tela "Mercado IA" do Painel: eventos de cada etapa do vigia, rodadas com os jogadores movidos, alerta de recarregar a carreira e conferência no save seguinte (se o jogo gravou por cima, devolve os negócios ao limite da janela e refaz o mercado). |
| `premiacao.py` | **A noite da Bola de Ouro:** quando o save traz uma edição nova do prêmio de melhor do mundo (ou um continental com alguém do clube no pódio), monta a cerimônia uma vez e espalha por capas, matérias em três vozes, vestiário (moral), celular, redes, coletiva e um slide na Central. |
| `raio_x.py` | **Raio-x do time na imprensa:** a cada 8 jogos jogados, uma matéria com os números do próprio jogo (por onde ataca, quando marca e sofre, como saem os gols, quem carrega o time, últimos jogos x temporada). |
| `rede_v3.py` | **Rede v3 dos seus jogos:** comitê de 5 redes residuais pequenas sobre a estatística (mexe só no saldo), com 51 entradas — inclusive jogador por jogador (velocidade e jogo aéreo x zagueiros, quem está quente, dependência do artilheiro). Retreina do zero a cada jogo, em processo separado, com peso maior para os jogos recentes; a cada 100 jogos novos, um reajuste automático testa tamanhos e regularizações andando no tempo e só troca a configuração se ela ganhar (`historico/rede_usuario_v3_config.json`). |
| `ficha_jogo.py` | **Ficha do jogo:** XI provável, condição física, carga de 14 dias, descanso, desfalques, espírito de equipe e moral dos dois lados antes de um jogo seu (só leitura). |
| `pretreinar_rede.py` | Pré-treino da rede com o histórico de súmulas, com teste contra a estatística. |

### 4.6 Serviços e Central

| Módulo | Função |
|---|---|
| `vigia.py` | Roda em segundo plano: detecta o save, executa mercado e reunião, e grava erros e batimento. |
| `central.py` | Servidor da Central. Threads: pulso, imprensa ao vivo, guarda do vigia (religa se travar), técnico da IA e IA adversária. |
| `central_dados.py` | Exporta o estado da carreira para a página. |
| `central_rede.py` | Acesso pela rede Wi-Fi, com PIN. |
| `pulso.py` | Leitura ao vivo da memória (resultados, tabela, próximo jogo). |
| `acoes.py` | Diário de ações da Central e os efeitos ao vivo. |
| `escudos.py` | Escudos oficiais. |
| `laboratorio.py` | Comparação de saves de teste (pesquisa). |
| `central/index.html` | A página da Central (HTML, CSS e JS sem bibliotecas externas). |

## 5. O Painel (`painel/`)

| Módulo | Função |
|---|---|
| `app.py` | Janela Qt6. Abas: Início, Central (QWebEngineView), Rede neural (QtCharts), IA adversária, Configuração, Registros e Manual. Também a bandeja e a cópia única. A opção `--captura PASTA` grava uma imagem de cada página. |
| `servicos.py` | Vigia e Central como `QProcess`: sem console, com registro capturado, religando sozinhos se caírem. |
| `verificar.py` | Verificações sem Qt: Python, jogo (versão), Sider, Lua, módulo, pesXdecrypter (impressão digital), saves, foto da memória e Gemini. Também instala o módulo no Sider e restaura o decrypter. |
| `diagnostico.py` | Relatório da instalação: ambiente, save e memória (bytes do simulador, tabela de jogadores, blocos táticos), só leitura. |
| `atualizar.py` | Atualização automática pelos releases do GitHub (leve ou completa), com SHA-256 e backup. |
| `sistema.py` | Processos do Windows por ctypes e abertura do jogo. |
| `base.py` | Pastas do Painel no desenvolvimento e no pacote, e a versão. |

## 6. Empacotamento (`empacotar/`)

`montar.py` monta o pacote:
- Python oficial embutido, mais PySide6 e Pillow;
- Qt enxugado das partes que o Painel não usa;
- o código, sem dados pessoais (o script aborta se encontrar algum segredo);
- o pesXdecrypter 6.0.0 conferido por SHA-256, com a licença em `terceiros/`;
- o modelo inicial da rede.

Gera a versão portátil (`.zip`) e o instalador (`MercadoIA.iss`, Inno Setup), que instala por usuário, sem pedir administrador. Detalhes em [EMPACOTAR.md](EMPACOTAR.md).

## 7. Arquivos de dados (`cerebro/historico/`, nunca publicados)

| Arquivo | Conteúdo |
|---|---|
| `vestiario_estado.json` | estado de cada carreira |
| `central_*.json` | dados da página |
| `imprensa.db` | matérias e legado |
| `ia_adversaria.json` | planos, registro e aprendizado |
| `escalacao_ia.json` | escalações escritas |
| `duelo.json`, `rede_*.json` | placar e pesos das redes |
| `vigia_erros.txt` | erros do vigia |
| `central_rede.json` | PIN (segredo) |

A chave do Gemini fica no `.env` da pasta da ferramenta, criptografada pelo Windows (`segredos.py`). **Nunca compartilhe esse arquivo.** O `cerebro/ia.json` guarda só o modelo e o liga/desliga.

## 8. Regras do projeto

1. **Sem "IA roubada".** Nada de atributos alterados: a IA vence com tática e escalação.
2. **O empurrão do diretor de campeonato nunca vale contra o usuário**, e a escalação do usuário nunca é tocada.
3. **Backup e conferência de ida e volta** antes de trocar qualquer save.
4. **Toda escrita na memória confere o valor antes e depois.**
5. **Textos só afirmam o que os dados mostram.** A IA de texto é opcional e só reescreve o estilo.

## 9. Descobertas de engenharia reversa (resumo)

- O simulador (função `0x141332010`) chama o técnico da IA em `0x1414FF0E0` com o modo 3 fixo, em `0x1413321FC`. O modo 1 respeita a escalação guardada.
- Nos jogos IA × IA, o placar depende quase só da força do XI: cerca de +0,13 gol de saldo por ponto de nota, sem vantagem de mando. A forma (seta) quase não pesa.
- Os planos de jogo e as instruções avançadas (códigos 1 a 16) foram mapeados num save por vez, junto com o usuário.
- A tabela oficial do jogo é mais confiável do que as súmulas, que às vezes perdem um jogo.

Mais detalhes em [ARQUITETURA.md](ARQUITETURA.md) e em `pesquisa/simulador_escalacao.md`.
