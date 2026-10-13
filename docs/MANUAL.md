# Manual do Mercado IA

O Mercado IA deixa a **Master League do PES 2021** mais viva. Clubes da IA contratam e vendem com lógica. O vestiário, a imprensa e a torcida reagem aos seus resultados. Cada adversário estuda o seu time e monta um plano tático contra você. E uma rede neural disputa com a estatística quem entende melhor o seu jogo.

Tudo é controlado pelo **Painel**, um aplicativo para Windows. A Central do Técnico abre dentro dele.

> Projeto experimental de engenharia reversa, feito pela comunidade. **Faça backup dos seus saves.** Use por sua conta e risco.

---

## 1. Requisitos mínimos

| Item | O que precisa |
|---|---|
| Sistema | Windows 10 ou 11, 64 bits |
| Jogo | eFootball PES 2021 Season Update para PC, com o `PES2021.exe` na versão **1.1.0.0** (os endereços de memória foram mapeados nela) |
| **Sider** | **Obrigatório.** Testado com o Sider **7.3.3**. É o Sider que carrega o módulo do Mercado IA dentro do jogo. |
| Patch | Qualquer patch que use o Sider. Desenvolvido com o GOGOSZ; outros devem funcionar, porque o que importa é o Sider. |
| Disco | cerca de 600 MB para o programa, mais espaço para backups dos saves |
| Memória | a mesma que o PES pede; o Painel usa pouco além do jogo |
| Internet | Só é necessária para a IA de texto do Google Gemini (opcional). Todo o resto já vem no pacote. |

Você **não precisa instalar o Python**: ele já vem dentro do pacote.

## 2. Antes de instalar

1. **Instale o Sider** no seu PES 2021, se ainda não tiver. Muitos patches já trazem o Sider instalado. Na pasta do jogo devem existir o `sider.exe`, o `sider.dll` e o `sider.ini`.
2. **Faça backup dos saves.** Copie para outro lugar a pasta `Documentos\KONAMI\eFootball PES 2021 SEASON UPDATE`. Se o seu Documentos estiver no OneDrive, ela fica dentro do OneDrive.

## 3. Instalação

Há duas formas. Escolha uma.

- **Instalador** (`MercadoIA-Setup-<versão>.exe`): dê dois cliques e avance. Ele instala na sua pasta de usuário, sem pedir administrador, e cria o atalho **Mercado IA**.
- **Versão portátil** (`MercadoIA-portatil-<versão>.zip`): extraia numa pasta e abra `Mercado IA.cmd`. Evite `Arquivos de Programas`: o Mercado IA precisa gravar na própria pasta.

## 4. Primeira configuração

Na primeira vez, o Painel abre na aba **Configuração**:

1. **Pasta do PES 2021**: clique em **Detectar**. Se ele não achar, use **Procurar...** e escolha a pasta onde está o `PES2021.exe`.
2. **Pasta dos saves**: em geral, **Detectar** basta.
3. **pesXdecrypter**: já vem no pacote. É a ferramenta, de domínio público, que abre e fecha a criptografia do save. A verificação confere se os arquivos são os oficiais. Se eles sumirem, use **Restaurar a versão oficial**.
4. Clique em **Verificar de novo**. Corrija o que aparecer em vermelho: dê duplo clique no item, ou selecione-o e clique em **Corrigir o item selecionado**. O mais comum é **Módulo MercadoIA.lua**. O Painel copia o módulo para a pasta `modules` do jogo e acrescenta esta linha ao `sider.ini`, guardando um backup antes:
   ```ini
   lua.module = "MercadoIA.lua"
   ```
   Ele também garante que exista `lua.enabled = 1`.
5. **IA de texto (opcional)**: veja a seção 8.
6. Clique em **Salvar configuração**.

Quando tudo estiver em verde, o Painel liga os serviços sozinho.

## 5. Como jogar

1. Abra o **Mercado IA** pelo atalho.
2. Clique em **▶ Jogar**. O Painel liga os serviços e abre o jogo pelo lançador configurado (padrão: `WORLD LAUNCHER.exe`, `sider.exe` ou `PES2021.exe`).
3. Entre na sua Master League e jogue normalmente. A cada vez que o jogo **salvar**, o Mercado IA faz a "reunião": lê o save, atualiza o vestiário, a imprensa, o momento do time e o duelo.

Teclas dentro do jogo (pelo overlay do Sider):

| Tecla | O que faz |
|---|---|
| **8** | Pede uma rodada do mercado (na janela de transferências) |
| **9** | Pede a reunião do vestiário na hora (depois de um jogo) |
| **1 / 2 / 3** | Responde a um jogador que pediu para conversar com você |

## 6. O Painel, aba por aba

- **Início**: o estado de tudo. Mostra se o jogo está aberto, o vigia (que lê os saves), a Central, a última reunião, o técnico da IA e o duelo. É também onde ficam os botões **Jogar** e **Ligar/Desligar serviços**.
- **Central**: a Central do Técnico. Tem vestiário, imprensa (jornais, coletivas, Bola na Mesa, redes sociais), análise do próximo jogo, diretoria, calendário, celular e história.
- **Rede neural**: o duelo estatística × rede (seção 9), com o placar, a evolução, a curva de aprendizado e os palpites dos seus jogos.
- **IA adversária**: o que o técnico do computador aprendeu contra você e o plano que usou em cada jogo.
- **Configuração**: pastas, verificação do Sider, IA de texto e automações. Cada automação pode ser ligada ou desligada.
- **Registros**: o que o vigia e a Central estão fazendo, ao vivo. Use esta aba se algo parecer parado.
- **Manual**: este texto.

Pode fechar a janela à vontade: o Painel continua na **bandeja**, perto do relógio, e os serviços seguem rodando. Para sair de verdade, clique com o botão direito no ícone da bandeja e escolha **Sair**.

## 7. A Central no celular

Em **Configuração**, marque **Abrir a Central no celular pela rede Wi-Fi**. A aba **Central** mostra o endereço, algo como `http://192.168.x.x:8765`. Abra esse endereço no celular, conectado à mesma rede Wi-Fi, e digite o PIN que aparece na página da Central no PC.

## 8. IA de texto: Google Gemini (opcional)

O Mercado IA pode usar o **Google Gemini** para reescrever os textos da imprensa (jornais, Bola na Mesa, redes sociais) no estilo de cada veículo.

1. Pegue uma chave gratuita no **Google AI Studio**: https://aistudio.google.com/apikey
2. Em **Configuração → IA de texto**, cole a chave, clique em **Testar a chave**, marque **Usar a IA do Google Gemini** e salve.

A chave fica **só no seu PC**, no arquivo `app\cerebro\ia.json`, e só é enviada ao Google. **Nunca compartilhe esse arquivo.** Sem chave, tudo funciona com os textos prontos.

## 9. O duelo: estatística × rede neural

Antes de cada jogo, dois "cérebros" dão um palpite de placar:

- **Estatística**: o modelo medido no próprio jogo, com a força dos elencos e o que a IA adversária aprendeu.
- **Rede neural**: uma rede pequena, que roda no seu PC sem precisar de internet, e aprende com cada jogo.

A pontuação é de bolão: **placar exato vale 3**, **saldo certo vale 2**, **vencedor certo vale 1**. São duas arenas, cada uma com o seu placar:

| Arena | Quem lidera decide | Quanto demora |
|---|---|---|
| Jogos da IA (simulados) | quantos titulares cada clube da IA poupa | poucos dias de jogo |
| Seus jogos | qual plano tático o adversário usa contra você | cerca de 1,5 temporada |

A estatística começa no comando. Depois de **100 jogos** pontuados numa arena, quem somar mais nos últimos 100 assume. A estatística nunca é apagada: se voltar a ser melhor, volta a mandar.

## 10. Seus dados

Fica tudo no seu PC:

| O quê | Onde |
|---|---|
| dados da carreira | `app\cerebro\historico` |
| configuração | `app\config.json` |
| chave da IA | `app\cerebro\ia.json` |
| backups dos saves | `app\Backups` |

Atualizar o Mercado IA (reinstalar uma versão nova) **não apaga** esses dados. Só são enviados para fora do PC os textos que o Gemini reescreve, e só se você ligar a IA de texto.

## 11. Problemas comuns

| Sintoma | O que fazer |
|---|---|
| "Foto da memória: ainda não existe" | Abra o jogo pelo Sider e entre numa carreira. O módulo grava `mercado_snap.bin` na pasta do jogo. Se não aparecer, confira em **Configuração** se o módulo está listado no `sider.ini` e se `lua.enabled = 1`. |
| A imprensa não atualiza depois do jogo | Veja **Registros → Vigia**. A reunião acontece quando o jogo **salva**; com o salvamento automático desligado, salve manualmente. |
| A Central não abre dentro do Painel | Use **Abrir no navegador** (aba Central). Na aba **Registros**, veja se a Central está rodando e clique em **Reiniciar Central**. |
| Antivírus reclamou | O Mercado IA lê e escreve na memória do PES (é assim que ele mexe nas setas, mensagens e táticas). Libere a pasta do Mercado IA. O Python que vem no pacote é o oficial, assinado pela Python Software Foundation. |
| Versão do jogo diferente de 1.1.0.0 | A verificação mostra um aviso. As partes que leem e escrevem na memória podem não funcionar em outra versão do executável. |
| Quero voltar o `sider.ini` ao que era | O Painel guarda os backups em `app\Backups\sider`. |

## 12. Desinstalar

- **Instalador**: Painel de Controle → Programas → **Mercado IA** → Desinstalar.
- **Versão portátil**: apague a pasta.

Em qualquer caso, tire a linha `lua.module = "MercadoIA.lua"` do `sider.ini` (ou restaure o backup).
