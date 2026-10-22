Mercado IA 0.9.7: a rede neural agora estuda por que errou.

**O que muda para você**
- **Autópsia de cada jogo.** Depois de cada partida, o Mercado IA cruza os números do jogo (chutes e chutes no gol dos dois lados, posse, passes, como e quando saíram os gols) com as notas dos jogadores e calcula o **placar merecido** pelas chances. Assim ele separa o que foi **azar** (o goleiro pegou tudo, a bola não entrou) do que foi **leitura errada** do jogo. Aparece no Painel (aba Rede neural) e na aba Análise da Central.
- **Julgamento da rede.** A rede passa a se avaliar: nos últimos jogos, quantas vezes a correção dela ajudou e quantas vezes ela "pesou a mão" em relação à estatística.
- **Aprendizado mais esperto.** O placar merecido de cada jogo fica guardado para o treino, e a rede testa sozinha, a cada 100 jogos, se aprender com ele melhora os palpites. Só passa a usar quando ganhar.

**Bom saber**
- Como os outros números do jogo, a autópsia completa só existe para partidas **jogadas** (as simuladas não têm estatística).
- Depois de atualizar, feche e abra o Painel.
- **Windows Defender:** ele pode acusar o `encrypter21.exe` (pesXdecrypter oficial) como `Trojan:Win32/Pomal!rfn`. É falso positivo. Permita o arquivo em Segurança do Windows → Proteção contra vírus e ameaças → Histórico de proteção → Ações → **Permitir no dispositivo**; depois, no Painel, Configuração → Verificar de novo (ou Restaurar a versão oficial).
