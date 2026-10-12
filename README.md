# Mercado IA para PES 2021

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
- funciona em qualquer carreira (liga e calendário detectados sozinhos: temporada europeia "2026/27" ou anual "2027");
- pode ser aberta no celular pela rede local, protegida por PIN.

Algumas reações são escritas na memória do jogo enquanto ele está aberto (setas de condição, mensagens, apelidos, orçamento), com conferência antes e depois de cada escrita.

Para iniciar: `JOGAR_COM_MERCADO_IA.bat` (vigia + Central + jogo) ou `ABRIR_CENTRAL.bat` (só a Central). A chave da IA vai em `cerebro/ia.json` (modelo em `cerebro/ia.json.exemplo`) e **nunca deve ser publicada**.

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

Mais detalhes em [Arquitetura](docs/ARQUITETURA.md).

## Requisitos

- Windows;
- eFootball PES 2021 para PC;
- Python 3.10 ou superior — testado com Python 3.14;
- Sider compatível com o executável utilizado;
- `decrypter21.exe` e `encrypter21.exe` do projeto [pesXdecrypter](https://github.com/the4chancup/pesXdecrypter/releases).

O código Python utiliza apenas a biblioteca padrão; o Pillow é opcional (fotos dos jogadores na Central). Consulte [Dependências](docs/DEPENDENCIAS.md) e [Instalação](docs/INSTALACAO.md).

## Uso resumido

1. Inicie o vigia e o jogo pelo lançador configurado.
2. Entre em uma janela de transferências da Master Liga.
3. Abra o overlay do Sider no módulo Mercado IA e pressione `8`.
4. Salve a carreira e aguarde a mensagem de conclusão.
5. Recarregue a carreira sem salvar novamente.

O time do usuário e os limites ficam em `cerebro/mercado_config.json`. Comece copiando [mercado_config.example.json](mercado_config.example.json).

## Estrutura

```text
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
- binários do `pesXdecrypter`;
- patches, bancos de dados, saves, snapshots ou dados de jogadores;
- garantia de compatibilidade com qualquer versão do `PES2021.exe`.

Os endereços de memória foram descobertos e testados em uma instalação específica. Outras versões podem exigir um novo mapeamento.

## Segurança

O módulo Lua de produção não escreve na memória do jogo. As transferências são feitas numa cópia descriptografada do save, instalada só depois das verificações. A Central escreve na memória apenas campos mapeados (setas, mensagens, apelidos, orçamento), conferindo o valor antes e depois; dá para desligar em `cerebro/automacao.json` (`"ao_vivo": false`). Ainda assim, mantenha backups fora da pasta do jogo.

Nunca envie em uma issue pública um save pessoal completo sem entender o conteúdo que ele pode carregar.

## Licença e marcas

O código autoral deste repositório está sob a [licença MIT](LICENSE). Dependências e trechos adaptados mantêm suas próprias licenças, documentadas em [Avisos de terceiros](THIRD_PARTY_NOTICES.md).

PES, eFootball e KONAMI são marcas de seus respectivos proprietários. Este projeto comunitário não é afiliado, aprovado ou patrocinado pela KONAMI.
