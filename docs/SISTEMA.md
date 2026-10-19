# Documentação do sistema: Mercado IA

**Autor:** William ([github.com/WilliamProgramadorBR](https://github.com/WilliamProgramadorBR)), com Claude (Anthropic) como par de programação.

Este documento explica **como o sistema funciona por dentro**: os processos, os fluxos de dados, a API, os arquivos, a memória do jogo, o front-end, o Painel e a atualização automática. Também mostra como depurar e como estender. Ele foi pensado para quem programa em C# e conhece Qt6 e Django: há uma tabela de equivalências no final.

Documentos irmãos:
- [MANUAL.md](MANUAL.md): uso, para o jogador;
- [CODIGO.md](CODIGO.md): o que faz cada módulo;
- [EMPACOTAR.md](EMPACOTAR.md): gerar e publicar versões;
- [ARQUITETURA.md](ARQUITETURA.md): o mercado em detalhe.

---

## 1. Visão geral em uma figura

```text
                         ┌───────────────────────── PC do jogador ─────────────────────────┐
  PES2021.exe ◄─ Sider ─ MercadoIA.lua                                                      │
      │  memória            │ grava mercado_snap.bin (foto da memória), lê teclas 8/9/1/2/3 │
      │                     ▼                                                                │
      │              pasta do jogo (arquivos de troca: *_pedido.txt, *_resposta.txt)         │
      │                                                                                      │
      │ salva ML0000000X (criptografado)                                                     │
      ▼                                                                                      │
  Documentos\KONAMI\...\save                                                                 │
      │                                                                                      │
 ┌────┴────────────── Painel (PySide6, pythonw -m painel) ───────────────────────────────┐  │
 │  QProcess ──► vigia.py      percebe o save → reunião (aplicar_vestiario.py)           │  │
 │  QProcess ──► central.py    servidor HTTP 127.0.0.1:8765 + 4 threads de fundo         │  │
 │  QWebEngineView ──► http://127.0.0.1:8765  (a Central, dentro do app)                  │  │
 │  bandeja, verificação do ambiente, gráficos da rede, atualização OTA                   │  │
 └────────────────────────────────────────────────────────────────────────────────────────┘  │
      ▲  navegador do PC / celular (Wi-Fi + PIN) também abrem a Central                      │
      └──────────────────────────────────────────────────────────────────────────────────────┘
```

Três "fontes de verdade":

| Fonte | O que traz | Quando chega |
|---|---|---|
| **save** (`ML0000000X`) | elencos, súmulas, calendário, tática, finanças | depois que o jogo salva |
| **memória do jogo** (PES2021.exe, sem ASLR, base `0x140000000`) | o estado ao vivo, incluindo o que ainda não foi salvo | a qualquer momento |
| **historico/** | o que o jogo não guarda: vestiário, imprensa, legado, aprendizado das IAs | é o próprio Mercado IA que grava |

---

## 2. Processos e threads

| Processo | Como nasce | O que faz | Onde ver o log |
|---|---|---|---|
| **Painel** | `runtime\pythonw.exe -s -m painel` (atalho) | Janela Qt, supervisor dos serviços, atualização | é a própria janela |
| **vigia.py** | `QProcess` do Painel (ou o `.bat` antigo) | Loop: percebe o save estável e roda o mercado e a reunião como **subprocessos** | Painel → Registros → Vigia; `historico/vigia_erros.txt` |
| **aplicar_vestiario.py** | subprocesso do vigia, um por save | A reunião: vestiário, imprensa, momento, análise, Central | sai dentro do log do vigia |
| **aplicar.py** | subprocesso do vigia (janela de transferências) | O mercado | log do vigia; `historico/log_*.txt` |
| **central.py** | `QProcess` do Painel | Servidor HTTP (`ThreadingHTTPServer`) e as threads abaixo | Painel → Registros → Central |

As threads da Central (`central.py`, perto da linha 670):

| Thread | Ritmo | Função |
|---|---|---|
| `_pulso_thread` | poucos segundos | Lê a memória do jogo (resultados, tabela, próximo jogo) e grava `historico/pulso_*.json` |
| `_imprensa_viva_thread` | quando o pulso vê um jogo novo | Faz a matéria pós-jogo e o Bola na Mesa ao vivo; prepara a IA adversária (`_preparar_adversario`) |
| `_tecnico_ia_thread` | quando a data do jogo muda, ou a cada 10 min | Aplica o patch do simulador (modo 3 → 1), escreve as escalações dos clubes da IA e roda o ciclo do duelo |
| `_guarda_vigia_thread` | a cada 30 s | Se o vigia parar com o jogo aberto, fecha o travado. Fora do Painel, abre outro; dentro, o Painel religa. |

Uma ação feita na página (responder a coletiva, decidir um caso) roda numa thread curta: `_efeito_em_fundo`.

**Cópia única:** `unica.py` (mutex nomeado) garante um vigia e uma Central por vez; o Painel usa `QLocalServer`. **Variáveis que o Painel passa aos serviços:** `MERCADO_IA_TOOLS_DIR`, `MERCADO_IA_PAINEL=1`, `MERCADO_IA_SEM_JANELA=1` e `PYTHONNOUSERSITE=1`.

---

## 3. Fluxo 1: do save à reunião

1. O jogo salva o `ML0000000X`. O `vigia.py` vê a assinatura (tamanho e data) mudar e espera o arquivo estabilizar (`espera_segundos`).
2. O vigia chama `aplicar_vestiario.py <save> <snap> --ao-vivo`.
3. A reunião faz, em ordem:
   1. backup;
   2. descriptografa uma cópia (`decrypter21.exe`) em `save_work/vestiario_*/dec/data.dat`;
   3. `vestiario.analisar(d, snap)` monta `r`, com elenco (`J`), súmulas (`jogos`, `todas_partidas`), capitão e conflitos;
   4. moral → seta de condição (escrita no save e, ao vivo, na memória);
   5. disciplina, calendário e casos;
   6. cobertura da liga, próximos 3 jogos (`proximo_jogo.proximos`), corrida (`disputa`) e **momento** (`momento.calcular`);
   7. destaques do mundo, história, rodada e mês, Data FIFA, **lesões**, **análise pós-jogo**, celular, rumores e vitoriosos;
   8. imprensa (`imprensa.rodada`: matérias, Bola na Mesa e redes, com o redator Gemini opcional);
   9. grava `historico/vestiario_estado.json` (o estado de cada carreira) e exporta para a Central (`central_dados.exportar` → `historico/central_<slot>.json`);
   10. se mexeu no save: recriptografa, confere byte a byte e troca (`troca_save.substituir`).
4. A Central percebe a versão nova do JSON e manda pelo SSE para as páginas abertas.

O objeto `car` (um dicionário) é o estado persistente da carreira: tudo que a reunião calcula e quer lembrar fica nele (`car['momento']`, `car['corrida']`, `car['lesao_ultima']`...). O `r` é o retrato **desta** reunião.

## 4. Fluxo 2: ao vivo (sem esperar o save)

O `pulso.py` lê a memória a cada poucos segundos. A Central junta o JSON da última reunião com o pulso (`estado_projetado`): placar e súmula do jogo que acabou de terminar, tabela atual e próximo jogo. Isso alimenta a coletiva ao vivo, o Bola na Mesa pós-jogo e a IA adversária antes do próximo jogo.

## 5. Fluxo 3: uma decisão do usuário

```text
página: post('/api/acao', {tipo:'caso', caso, opcao})
  → central._acao → acoes.ACOES[tipo](corpo, estado)    grava UMA linha no diário historico/central_acoes.jsonl
  → thread _efeito_em_fundo → acoes.efeitos_ao_vivo       escreve no jogo na hora (setas, condição, orçamento)
  → SSE devolve o estado com o evento → a página mostra o aviso "Escrito no jogo"
  → na próxima reunião, aplicar_vestiario consome o diário (acoes.consumir) e consolida no save
```

O diário funciona como *event sourcing* simples: cada ação vira um evento numerado (`n`) e a reunião reaplica.

## 6. Fluxo 4: IA adversária e técnico da IA

- **IA adversária** (`ia_adversaria.preparar`). Roda quando o pulso mostra um próximo jogo novo:
  1. o `olheiro.perfil` estuda você;
  2. monta os candidatos de plano dentro da identidade do clube;
  3. escolhe um, por amostragem de Thompson ou pela rede neural, conforme o duelo;
  4. escreve os bytes do plano na **memória** (blocos de 600 B a partir de `0x133C50`, plano em +120/+280/+440);
  5. registra tudo em `historico/ia_adversaria.json`;
  6. depois do jogo, `aprender` recompensa as características do plano (saldo do adversário menos o esperado);
  7. no jogo seguinte, o clube anterior volta aos planos originais, byte a byte.
- **Técnico da IA** (`escalacao_ia.preparar`). Um patch **só na memória** troca o modo do simulador (byte `0x141332202`: 3 → 1); assim o jogo respeita a escalação guardada. Para cada clube da IA com jogo nos próximos 4 dias, ele escreve a escalação: o melhor XI na formação do clube, com rodízio conforme a importância do jogo e a pressão da liga (`disputa.py`). Nunca mexe no seu time.

## 7. Fluxo 5: o duelo estatística × rede neural

- **Palpites:** antes de cada jogo, os dois modelos dão um placar. Nos jogos da IA, isso acontece em `escalacao_ia._palpites`; nos seus, em `ia_adversaria._palpite_usuario`. Tudo vai para `historico/duelo.json` (`pend`).
- **Pontuação:** `duelo.ciclo(jogos)`, na thread do técnico da IA, pontua o que já tem resultado (bolão 3/2/1), passa para `hist` e treina a rede com os jogos novos, misturados a uma amostra do buffer (`rede_*_dados.json`), para ela não esquecer o que já aprendeu.
- **Troca de comando:** depois de 100 jogos pontuados numa arena, quem somar mais nos últimos 100 assume:
  - nos simulados, o rodízio (`_rodizio_pelo_lider`);
  - contra você, o plano (`_escolher_pela_rede`).
- **A rede dos jogos da IA** (`rede.py`): MLP em Python puro, 15 entradas → 10 tanh → 2 saídas softplus (gols esperados), perda de Poisson, Adam. O palpite é o resultado mais provável e, dentro dele, o placar mais provável.
- **A rede dos seus jogos (v3, `rede_v3.py`, desde 19/10/2026).** Com ~90 jogos, uma MLP comum decora: no teste andando no tempo, a NLL dela foi 3,81 contra 3,23 da estatística. A v3 funciona assim:
  - **comitê de 5 redes residuais** (4 tanh, L2 0,1): λ_nós = λ_est·e^δ e λ_eles = λ_est·e^−δ, com δ limitado a ±1. Ela corrige o saldo da estatística e mantém o total de gols;
  - **51 entradas:** as 28 da v2 + 23 de jogador por jogador, calculadas por `ficha_jogo.jogadores` e `contexto_jogo`;
  - **colunas sem variação** no treino ficam neutras;
  - **resultado no estudo** (45 jogos): bolão 57 × 49 e vencedor 34 × 32;
  - **treino:** do zero a cada jogo, em processo separado (`python rede_v3.py treinar 51`), para não travar a Central;
  - **"por quê":** neutraliza grupos de entradas e mede o efeito no saldo;
  - **placar:** traz também a calibração (`duelo.calibracao`: NLL e RPS).
- **Ficha do jogo** (`ficha_jogo.py`, desde a 0.9.3). Antes de cada jogo seu, `central._preparar_adversario` monta, para os dois lados:
  - o XI provável (o seu vem do bloco 730; o do rival, da escalação do técnico da IA) e a nota média;
  - a condição física (registro de 156 B, +120) e quantos titulares estão abaixo de 75;
  - a carga de minutos em 14 dias e quantos titulares passaram de 250 minutos (súmulas);
  - os dias de descanso e os desfalques por lesão;
  - do seu lado, também o espírito de equipe (`0xB629BC`) e a moral média.

  O save não guarda a condição de cada jogo, então a ficha é gravada junto com o palpite e com o registro da IA adversária.
- **Arena do usuário v2:**
  - **Estatística:** uma regressão *ridge* do saldo (`duelo.ajustar_est`). Ela parte de valores medidos (`PRIOR`), dá mais peso aos jogos recentes e se reajusta a cada jogo pontuado.
  - **Média de gols:** acompanha os jogos recentes.
  - **Você:** a constante da regressão mede o quanto você supera a força dos elencos; o "momento" é a média rápida menos a média lenta desse excedente.
  - **Por quê:** `porque_est` e `porque_rede` dizem quanto cada grupo (força, mando, forma, cansaço, desfalques, vestiário, você, plano do rival) mexe no saldo previsto. O Painel e a Central mostram.
  - **Pré-treino:** `python pretreinar_rede.py --so-usuario` refaz a carga e o descanso dos jogos antigos a partir das súmulas.
- **Físico na IA adversária** (`postura`):
  - se você chega no limite e o rival está inteiro, ele joga com ritmo alto, pressão na frente e pressão ofensiva;
  - se é o rival que chega cansado, ele guarda energia, com pressão tradicional e bloco mais baixo e compacto.

---

## 8. API HTTP da Central (`central.py`)

| Método e rota | O que faz |
|---|---|
| `GET /` | a página (`central/index.html`); na rede sem PIN, a tela do PIN |
| `GET /api/estado[?carreira=ML0000000X]` | o estado projetado (JSON grande: jogadores, imprensa, momento, duelo...) |
| `GET /api/eventos` | **SSE** (Server-Sent Events): manda `event: estado` quando a versão muda e um comentário a cada 15 s |
| `GET /api/rede` | URL e PIN para o celular (só no próprio PC) |
| `GET /escudo/<time>` · `GET /foto/<pid>` | escudo e foto do jogador, convertidos dos DDS do patch para PNG (com cache) |
| `GET /fundo/<aba>` | foto de fundo opcional (`central/fundos/<aba>.jpg/png/webp`) |
| `GET /sw.js` | service worker das notificações do navegador |
| `POST /api/acao` | ação genérica (`tipo`: `coletiva`, `caso`, `treino`...). Exige o cabeçalho `X-Central: 1` |
| `POST /api/responder` | resposta a um pedido de jogador ou à reunião com a diretoria |
| `POST /api/pin` | login da rede local (cookie `cpin`, `HttpOnly`, `SameSite=Strict`, bloqueio após 5 erros) |

**Segurança:** a Central escuta `0.0.0.0` só se a rede estiver ligada. O próprio PC entra direto; outros aparelhos precisam do PIN. Os POSTs exigem `X-Central`, e o CORS não é liberado: um site qualquer aberto no navegador não consegue mandar ações.

---

## 9. Arquivos de dados (`cerebro/historico/`)

| Arquivo | Formato | Conteúdo |
|---|---|---|
| `vestiario_estado.json` | `{"carreiras": {"ML0000000X\|TIME": car}}` | o estado persistente de cada carreira |
| `central_<slot>.json` | dicionário | o que a página mostra (gerado no fim da reunião) |
| `pulso_<slot>.json` | dicionário | a leitura ao vivo da memória |
| `central_acoes.jsonl` | uma linha JSON por ação | o diário de decisões |
| `imprensa.db` | SQLite (`imprensa_db.py`) | matérias, edições do Bola na Mesa e redes, legado e história |
| `ia_adversaria.json` | `{originais, originais_cru, registro, aprendizado, resumo, ativo, base}` | a IA adversária |
| `escalacao_ia.json` | `{feitos, titulares, ultima}` | o técnico da IA |
| `duelo.json` | `{arenas: {simulados, usuario}: {lider, pend, hist, trocas}, base_gols, ...}` | o duelo |
| `rede_simulados.json`, `rede_usuario.json` | pesos, estado do Adam, `extra.perdas` | as redes |
| `vigia_vivo.txt`, `vigia_erros.txt` | texto | batimento e erros do vigia |
| `central_rede.json` | `{rede, pin, segredo}` | **segredo**: nunca publicar |

A chave do Gemini fica no `.env` da pasta da ferramenta (`app/.env` no pacote), criptografada pelo Windows (DPAPI, `cerebro/segredos.py`): **segredo**. O `cerebro/ia.json` guarda só o modelo e o liga/desliga.

Na pasta da ferramenta (`app/` no pacote) ficam o `config.json` (pastas e opções do Painel), `Backups/`, `save_work/` e `_backup/` (versões anteriores do código, da atualização).

---

## 10. Save e memória (o essencial)

| Onde | O quê | Módulo |
|---|---|---|
| save, `0x133C50` + 600 B por bloco | registro de cada clube: técnico, 3 planos (+120/+280/+440), instruções avançadas (plano+108); a escalação fica em bloco+600 | `tatica_save.py` |
| save, registros de 156 B | jogadores da carreira (+116 = contador de lesão) | `jogadores_save.py` |
| save, faixa das súmulas | partidas (11 que terminaram em campo, notas, gols) e o calendário | `partidas_save.py` |
| memória, `0x141332202` | modo do técnico da IA no simulador (patch 3 → 1) | `escalacao_ia.patch` |
| memória, blocos de carreira | seta de condição e condição física (+282) | `ao_vivo.py` |
| `mercado_snap.bin` | a foto da memória gravada pelo `MercadoIA.lua` (cerca de 24 mil fichas) | `dados.py` |

O formato do save tem cabeçalho `20 11 09 12` e blocos zlib. A escrita usa `comprimir_exato` (o tamanho do stream precisa bater) e toda troca de save confere a ida e a volta.

---

## 11. Front-end (`cerebro/central/index.html`)

É um único arquivo (HTML, CSS e JS), **sem framework e sem build**. A arquitetura é simples:

- **estado global** `dados`, que chega pelo `EventSource('/api/eventos')` → `aplicar(d)` → `render()`;
- `render()` chama os `renderX(d)` de cada parte. Cada um preenche elementos por `id` (`$('id').innerHTML = ...`) e religa os eventos dos botões que criou;
- **ações** usam `post('/api/acao', corpo)`. O retorno chega pelo próprio SSE (estado novo), que dispara `render()` de novo;
- **confirmação em dois passos** (`confirmandoCaso`, `confirmandoCol`...): o primeiro clique marca, o segundo envia;
- **telas:** `irPara(aba)` troca a `.tela` ativa, aplica o fundo (`aplicarFundo`, SVG gerado em `FUNDOS` ou foto de `/fundo/<aba>`) e o título;
- **carrosséis do Resumo:** `iniciarCarrossel`, `irSlide` e `avancar` trocam a cada 9 s; a troca manual pausa por 2 min (`pausaAte`, guardado em `localStorage`). `atualizarCarrosseis()` roda a cada render e tira da roda as telas vazias;
- **notificações:**
  - `renderPendencias` monta `PEND` (o que espera decisão) → o sininho mostra e `notificarNovos()` avisa só do que for novo (`localStorage`);
  - no navegador, `ServiceWorker.showNotification` com botões `op:<id>`, e o `sw.js` devolve `{tipo:'decidir'}` → `decidirCaso`;
  - no Painel, `new Notification(...)` vira aviso da bandeja;
- **WhatsApp:** `waConversas(d)` junta o histórico (`d.celular`) e os casos abertos por contato; quais conversas já foram abertas fica em `localStorage` (`waLidas`);
- **gráficos:** `grafLinha()` gera SVG, com dica ao passar o mouse e tabela alternativa.

Para mexer no visual, as cores e fontes estão em variáveis no bloco "TEMA PES 21" (`--azul`, `--gold`, `--f-score`...).

## 12. O Painel (`painel/`)

| Classe ou função | Papel |
|---|---|
| `app.Janela` (QMainWindow) | menu lateral, `QStackedWidget` com as páginas, `QTimer` de 4 s (`tique`), bandeja |
| `PaginaInicio`, `PaginaCentral`, `PaginaRede`, `PaginaIA`, `PaginaConfig`, `PaginaRegistros`, `PaginaManual` | as abas. Cada uma tem `atualizar()`; a Central usa `QWebEngineView` |
| `servicos.Servico` | `QProcess` com ambiente próprio, registro capturado (`Signal linha`) e religamento (no máximo 5 quedas em 10 min) |
| `verificar.tudo()` | lista de `Item(id, titulo, estado, detalhe, acao)`, sem Qt; `instalar_modulo`, `baixar_decrypter`, `testar_gemini` |
| `atualizar` | OTA (próxima seção) |
| `Sinais` (QObject) | ponte das threads de fundo para a interface (`achou`, `progresso`, `baixou`, `erro`): o mesmo padrão de signals/slots que você usa em Qt6 |

Para depurar: `python -m painel --captura PASTA` grava uma imagem de cada página e sai. `--sem-servicos` abre sem ligar o vigia e a Central; `--minimizado` abre direto na bandeja.

## 13. Atualização automática (OTA)

```text
Painel (ao abrir e a cada 6 h) ──► GitHub API: /repos/WilliamProgramadorBR/mercado-ia-pes2021/releases/latest
   └─ baixa atualizacao.json  {versao, notas, runtime, pyside, arquivos: {nome: sha256}}
       ├─ versão maior e mesmo Python/Qt → LEVE: MercadoIA-app-<v>.zip (<1 MB)
       │     confere SHA-256 → backup em app/_backup/<versão>_<data>/ → troca painel/, cerebro/, sider/, docs/, pesXdecrypter/
       │     (NUNCA: .env, cerebro/historico/, ia.json, automacao.json, mercado_config.json, config.json) → reinicia o Painel
       └─ mudou Python ou Qt → COMPLETA: MercadoIA-Setup-<v>.exe → confere → .cmd roda o instalador silencioso e reabre
```

Para publicar: suba `VERSAO` em `painel/base.py`, escreva `empacotar/NOTAS.md` e rode `python empacotar/publicar.py`. O detalhe está em [EMPACOTAR.md](EMPACOTAR.md).

---

## 14. Como depurar

| Situação | Ferramenta |
|---|---|
| A reunião deu erro | Painel → Registros → Vigia; `historico/vigia_erros.txt` (traz o traceback) |
| Testar o mercado sem mexer no save | `python cerebro/aplicar.py <copia_do_save> <snap> --ensaio` |
| Testar a reunião numa carreira de teste | `laboratorio.py` (lista e compara saves copiados pelo vigia) |
| Ver o que a página recebe | `curl http://127.0.0.1:8765/api/estado` |
| Ver erros de JavaScript | F12 no navegador; no Painel, "Abrir no navegador" |
| Algo não funciona no PC de outra pessoa | Painel → Configuração → **Diagnóstico da instalação** (`painel/diagnostico.py`): ambiente, save e memória num relatório para copiar |
| Conferir o ambiente | Painel → Configuração → Verificar de novo (ou `python -c "from painel import verificar as v; print(v.tudo())"`) |
| Atualização sem publicar | `MERCADO_IA_ATUALIZACAO_URL=http://127.0.0.1:8000/atualizacao.json` + `python -m http.server` |
| Re-treinar a rede | `python cerebro/pretreinar_rede.py` (ou o botão na aba Rede neural) |

## 15. Como estender (receitas)

- **Nova pergunta de coletiva:** crie uma função com o decorador `@cen` em `coletiva_momento.py` (ou num lote novo importado no fim de `coletiva_cenarios.py`). Ela recebe `(X, rnd)` e devolve `None` quando o contexto não sustenta a pergunta, ou `(peso, alvo, pergunta, [op(texto, efeitos, manchete, linha_fina), ...])`. Efeitos: `G(delta, motivo)` para o grupo e `E('reg:pid', delta, rodadas, motivo)` para um jogador.
- **Nova pauta do Bola na Mesa:** use `@pauta` em `pautas_momento.py`. Devolva `{'id', 'cat', 'peso', 'titulo', 'falas': [(quem, texto)], 'enquete'?, 'posts'?}`.
- **Novo post nas redes:** acrescente uma tupla `(categoria, autor, texto, tom)` em `redes_vivas.MODELOS`. Os campos `{assim}` precisam existir no contexto (`redes_vivas.contexto` cria categorias e campos).
- **Novo item na verificação do Painel:** acrescente um `Item(...)` em `verificar.tudo()`. Se ele puder ser corrigido, coloque uma `acao` e trate em `PaginaConfig.corrigir`.
- **Nova aba no Painel:** crie uma classe `PaginaX(QWidget)` com `atualizar()` e registre em `Janela.PAGINAS`.
- **Nova tela na Central:** acrescente um `<div class="tela" id="t-x">` e um botão `data-aba="x"`, escreva o `renderX(d)` e chame dentro de `render()`. Para o fundo e o título, use `FUNDOS.x` e `TITULOS.x`.

---

## 16. Python para quem vem do C#

| C# | Python, neste projeto |
|---|---|
| `class Foo { }` com propriedades | `class Foo:` ou um **dict** simples (o projeto usa muito `dict`, como `car`, `r` e `X`) |
| `record` / DTO | `@dataclass` (ex.: `verificar.Item`) ou dict |
| `Dictionary<K,V>` / `List<T>` | `dict` / `list`; `collections.Counter` e `defaultdict` para contagens |
| LINQ `Where/Select/OrderBy` | *list comprehension* `[f(x) for x in xs if c(x)]`, `sorted(xs, key=...)`, `max(xs, key=...)` |
| `FirstOrDefault` | `next((x for x in xs if c(x)), None)` |
| `using (var f = ...)` | `with open(...) as f:` |
| `IEnumerable` com `yield return` | gerador com `yield` |
| atributos (`[HttpGet]`) | **decoradores** (`@cen`, `@pauta`): uma função que recebe a função e a registra numa lista |
| `Task.Run` / `Thread` | `threading.Thread(target=f, daemon=True).start()` (o GIL deixa só uma thread rodando Python por vez: bom para E/S e espera, ruim para CPU pesada) |
| `Process.Start` | `subprocess.run(...)` (espera) ou `subprocess.Popen(...)` (não espera); no Qt, `QProcess` |
| `[DllImport]` / P/Invoke | `ctypes` (ex.: `ReadProcessMemory` em `memoria.py`, `SHGetKnownFolderPath` em `caminhos.py`) |
| `BitConverter` / `BinaryReader` | `struct.unpack_from('<IHH', buf, offset)` (`<` = little-endian, `I` = uint32, `H` = uint16) |
| `System.Text.Json` | `json.load` / `json.dump` (com `ensure_ascii=False` para acentos) |
| `string.Format` / `$"..."` | f-string `f'{nome} tem {gols} gols'` |
| `namespace` / `using` | o módulo é o arquivo; `import x` / `from x import y` |
| `null` | `None`; e `a or b` funciona como `a ?? b` para valores "vazios" (`0`, `''`, `[]`, `None`) |
| eventos / `delegate` | funções passadas como valor (ex.: `log=print`); no Qt, `Signal`/`Slot` como você já conhece |
| Django `views` | aqui é `http.server` puro: `Handler.do_GET` e `do_POST` decidem pela rota (`central.py`) |

Convenções do código:
- nomes em português;
- comentários com a data e o porquê da decisão;
- `try/except Exception` nas fronteiras ("nunca derruba a reunião"), com aviso no log;
- escrita de arquivo atômica (`.tmp` + `os.replace`).
