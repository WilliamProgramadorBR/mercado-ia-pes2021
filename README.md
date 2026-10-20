# Mercado IA para PES 2021

**Autor:** William — [github.com/WilliamProgramadorBR](https://github.com/WilliamProgramadorBR)

[![Licença MIT](https://img.shields.io/badge/licen%C3%A7a-MIT-blue.svg)](LICENSE)

Motor externo de transferências para a Master Liga do eFootball PES 2021. O projeto lê o estado atual da carreira, identifica a formação e as necessidades de cada elenco e simula dirigentes com identidade esportiva e memória econômica entre temporadas.

O mercado é uma **IA simbólica baseada em regras**. A Central do Técnico pode, opcionalmente, usar um modelo generativo (Gemini, com a chave do próprio usuário) só para reescrever os textos da imprensa; sem chave, tudo funciona com os textos prontos.

> Projeto experimental de engenharia reversa. Faça backup dos saves. Use por sua conta e risco.

## Principais recursos

- leitura de aproximadamente 24 mil fichas de jogadores diretamente da memória;
- formação real de cada clube, em vez de um esquema fixo para todos;
- diagnóstico de força, encaixe, profundidade e ciclo etário;
- perfis persistentes: elite, formador, vendedor, reconstrução, modesto e equilibrado;
- livro-caixa próprio, receitas anuais e consequências econômicas entre temporadas;
- proteção do clube do usuário, seleções e jogadores com funções especiais;
- limites por clube e por janela;
- backup automático antes de qualquer alteração;
- criptografia seguida de nova descriptografia e comparação byte a byte;
- modo `--ensaio`, que gera relatórios sem substituir o save.

## Central do Técnico (vida de técnico)

Uma página local (`cerebro/central.py`, http://127.0.0.1:8765) que transforma a carreira num "simulador de vida futebolística", lendo o save e a memória do jogo:

- vestiário: moral, status, funções, conflitos, pedidos dos jogadores (braçadeira, pênalti, camisa 10), vida pessoal e disciplina;
- imprensa: três jornais com tons diferentes, coletivas com perguntas e consequências, programa de TV *Bola na Mesa* (com voz), redes sociais e matérias sobre a liga e o mundo;
- diretoria: metas, confiança, orçamento, patrocínio e espelho da diretoria nativa do jogo;
- temporada e mundo: prévia do próximo jogo, seleção da rodada, time do mês, Data FIFA, rumores, prêmios, livro dos recordes e gráficos;
- celular do técnico, arquibancada e painel de pendências antes do próximo jogo;
- IA adversária que estuda o usuário: um olheiro lê o plano de jogo, os artilheiros e a velocidade do ataque do usuário; o técnico do computador monta o plano do adversário (estilo, pressão, linha, compactação e instruções avançadas como marcação individual e pressão ofensiva) e aprende com cada resultado qual tática funciona contra aquele jogador — sem tocar em atributos;
- técnico da IA nos jogos simulados: corrige o rodízio quase aleatório do jogo (os clubes passam a escalar os melhores, com descanso realista em jogos menores) — detalhes em [pesquisa/simulador_escalacao.md](pesquisa/simulador_escalacao.md);
- diretor de campeonato: times em disputa de título, vaga ou rebaixamento jogam com força máxima conforme a liga aperta (pressão dinâmica pelo momento da temporada e pela distância de pontos), times sem objetivo rodam o elenco, e o técnico da IA poupa titulares antes de jogos mais importantes; a imprensa acompanha a corrida;
- mercado com elencos de tamanho real (até 28) e contratações que respeitam o plano de jogo de cada clube;
- entrosamento do elenco com o plano de jogo, pelos números do próprio jogo;
- funciona em qualquer carreira (liga e calendário detectados sozinhos: temporada europeia "2026/27" ou anual "2027");
- pode ser aberta no celular pela rede local, protegida por PIN.

Algumas reações são escritas na memória do jogo enquanto ele está aberto (setas de condição, mensagens, apelidos, orçamento), com conferência antes e depois de cada escrita.

## Painel (aplicativo)

Tudo é controlado pelo **Painel**, um aplicativo Qt6 (PySide6) para Windows:

- **Início:** o estado do jogo, do vigia, da Central, do técnico da IA e do duelo, com o botão **Jogar**;
- **Central:** a Central do Técnico dentro do app (no celular continua pelo navegador, com PIN);
- **Rede neural:** o duelo estatística × rede neural, com placar, evolução, curva de aprendizado e palpites;
- **IA adversária:** o que o técnico do computador aprendeu contra você;
- **Configuração:** pastas detectadas sozinhas, verificação do Sider (com instalação do módulo), download do pesXdecrypter, chave do Google Gemini e automações;
- **Registros** e **Manual**.

O pacote leva o Python oficial embutido: o jogador **não instala Python**. Baixe o instalador (`MercadoIA-Setup-<versão>.exe`) ou a versão portátil (`.zip`) na página de releases e siga o [Manual](docs/MANUAL.md).

> **Windows Defender:** ele pode acusar o `encrypter21.exe` do pesXdecrypter (ex.: `Trojan:Win32/Pomal!rfn`). É falso positivo: é o arquivo oficial, de domínio público, e o Painel confere o SHA-256 dele. **Permita o arquivo** em Segurança do Windows → Proteção contra vírus e ameaças → Histórico de proteção → Ações → **Permitir no dispositivo**. Sem ele, as transferências não são gravadas no save. Passo a passo no [Manual](docs/MANUAL.md#2-antes-de-instalar).

Para desenvolver: `python -m painel` na pasta que contém `painel/` e `cerebro/` (requer `pip install PySide6`). Para ter atalhos numerados com ícones ao lado dos `.bat` (1 = Painel, o app principal), rode `python empacotar\icones.py`. Para gerar o instalador, veja [Empacotar](docs/EMPACOTAR.md). Os `.bat` antigos continuam funcionando. A chave da IA é configurada no Painel e fica no `.env`, criptografada pelo Windows (modelo em `.env.exemplo`); **nunca deve ser publicada**.

## Como funciona

```text
PES 2021 + Sider
      │
      ├─ MercadoIA.lua captura uma foto somente leitura da memória
      │
      ├─ o usuário salva a Master Liga
      │
      └─ vigia.py detecta o save estável
             │
             ├─ descriptografa uma cópia
             ├─ reconstrói jogadores, elencos e formações
             ├─ executa o mercado simbólico
             ├─ edita e recriptografa a cópia
             ├─ confere a ida e volta byte a byte
             └─ substitui o save e mantém o backup
```

Mais detalhes em [Arquitetura](docs/ARQUITETURA.md), no [guia completo do código](docs/CODIGO.md) e na [documentação do sistema](docs/SISTEMA.md) (processos, fluxos, API, dados, atualização automática e Python para quem vem do C#).

## Requisitos

- Windows 10 ou 11, 64 bits;
- eFootball PES 2021 para PC (`PES2021.exe` 1.1.0.0, a versão em que a memória foi mapeada);
- **Sider (obrigatório)**: testado com o 7.3.3. É ele que carrega o `MercadoIA.lua` dentro do jogo;
- `decrypter21.exe` e `encrypter21.exe` do [pesXdecrypter](https://github.com/the4chancup/pesXdecrypter/releases): já vêm no pacote (versão oficial 6.0.0, domínio público; veja os [avisos de terceiros](THIRD_PARTY_NOTICES.md)).

No pacote, o Python já vem embutido. Para rodar direto do código: Python 3.10+ (testado com 3.14), mais PySide6 para o Painel; o motor usa só a biblioteca padrão e o Pillow é opcional. Consulte o [Manual](docs/MANUAL.md), as [Dependências](docs/DEPENDENCIAS.md) e a [Instalação manual](docs/INSTALACAO.md).

## Uso resumido

1. Inicie o vigia e o jogo pelo lançador configurado.
2. Entre em uma janela de transferências da Master Liga.
3. Abra o overlay do Sider no módulo Mercado IA e pressione `8`.
4. Salve a carreira e aguarde a mensagem de conclusão.
5. Recarregue a carreira sem salvar novamente.

O time do usuário e os limites ficam em `cerebro/mercado_config.json`. Comece copiando [mercado_config.example.json](mercado_config.example.json).

## Estrutura

```text
painel/                   aplicativo Qt6 (PySide6): Painel, verificação, serviços
empacotar/                montagem do pacote (Python embutido) e do instalador (Inno Setup)
cerebro/                  motor Python, integração com o save e Central do Técnico
cerebro/central/          página da Central
sider/MercadoIA.lua       interface dentro do Sider
research/ML_Scanner.lua   ferramenta de pesquisa e mapeamento
edit21.py                 leitor opcional do EDIT descriptografado
docs/                     arquitetura, instalação e dependências
tests/                    testes sem save real
```

## O que não está incluído

- o jogo, executáveis ou arquivos da KONAMI;
- Sider;
- binários do `pesXdecrypter` no código-fonte (o pacote do Painel os inclui, na versão oficial conferida);
- patches, bancos de dados, saves, snapshots ou dados de jogadores;
- garantia de compatibilidade com qualquer versão do `PES2021.exe`.

Os endereços de memória foram descobertos e testados em uma instalação específica. Outras versões podem exigir um novo mapeamento.

## Segurança

O módulo Lua de produção não escreve na memória do jogo. As transferências são feitas numa cópia descriptografada do save, instalada só depois das verificações. A Central escreve na memória apenas campos mapeados (setas, mensagens, apelidos, orçamento), conferindo o valor antes e depois; dá para desligar em `cerebro/automacao.json` (`"ao_vivo": false`). Ainda assim, mantenha backups fora da pasta do jogo.

Nunca envie em uma issue pública um save pessoal completo sem entender o conteúdo que ele pode carregar.

## Licença e marcas

O código autoral deste repositório está sob a [licença MIT](LICENSE). Dependências e trechos adaptados mantêm suas próprias licenças, documentadas em [Avisos de terceiros](THIRD_PARTY_NOTICES.md).

PES, eFootball e KONAMI são marcas de seus respectivos proprietários. Este projeto comunitário não é afiliado, aprovado ou patrocinado pela KONAMI.
