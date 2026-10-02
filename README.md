# Mercado IA para PES 2021

[![Licença MIT](https://img.shields.io/badge/licen%C3%A7a-MIT-blue.svg)](LICENSE)

Motor externo de transferências para a Master Liga do eFootball PES 2021. O projeto lê o estado atual da carreira, identifica a formação e as necessidades de cada elenco e simula dirigentes com identidade esportiva e memória econômica entre temporadas.

Trata-se de uma **IA simbólica baseada em regras**. Não utiliza rede neural, serviço em nuvem ou modelo generativo.

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

O código Python utiliza apenas a biblioteca padrão. Consulte [Dependências](docs/DEPENDENCIAS.md) e [Instalação](docs/INSTALACAO.md).

## Uso resumido

1. Inicie o vigia e o jogo pelo lançador configurado.
2. Entre em uma janela de transferências da Master Liga.
3. Abra o overlay do Sider no módulo Mercado IA e pressione `8`.
4. Salve a carreira e aguarde a mensagem de conclusão.
5. Recarregue a carreira sem salvar novamente.

O time do usuário e os limites ficam em `cerebro/mercado_config.json`. Comece copiando [mercado_config.example.json](mercado_config.example.json).

## Estrutura

```text
cerebro/                  motor Python e integração com o save
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

O módulo Lua de produção não escreve na memória do jogo. A alteração permanente ocorre em uma cópia descriptografada do save e só é instalada depois das verificações. Ainda assim, mantenha backups fora da pasta do jogo.

Nunca envie em uma issue pública um save pessoal completo sem entender o conteúdo que ele pode carregar.

## Licença e marcas

O código autoral deste repositório está sob a [licença MIT](LICENSE). Dependências e trechos adaptados mantêm suas próprias licenças, documentadas em [Avisos de terceiros](THIRD_PARTY_NOTICES.md).

PES, eFootball e KONAMI são marcas de seus respectivos proprietários. Este projeto comunitário não é afiliado, aprovado ou patrocinado pela KONAMI.
