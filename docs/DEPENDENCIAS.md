# Dependências

## Obrigatórias

### Python

- versão mínima recomendada: Python 3.10;
- versão testada durante o desenvolvimento: Python 3.14;
- pacotes de terceiros: nenhum;
- instalação: marque a opção para disponibilizar `python` no `PATH`.

O arquivo `requirements.txt` permanece sem bibliotecas porque todo o motor usa apenas a biblioteca padrão.

### Sider

O módulo `sider/MercadoIA.lua` depende da API de memória e do overlay do Sider. Adicione ao `sider.ini`:

```ini
lua.module = "MercadoIA.lua"
```

O Sider e seus binários não são redistribuídos aqui. A compatibilidade depende da versão do executável do jogo.

### pesXdecrypter

São necessários:

```text
pesXdecrypter/decrypter21.exe
pesXdecrypter/encrypter21.exe
```

Baixe-os nos [releases oficiais do pesXdecrypter](https://github.com/the4chancup/pesXdecrypter/releases). O projeto é distribuído principalmente em domínio público; o código MT19937 incluído pelo projeto possui sua própria licença permissiva. Consulte o repositório original antes de redistribuir seus binários.

O Mercado IA chama os executáveis como processos separados. Nenhum código do `pesXdecrypter` foi copiado para este repositório.

### 4ccEditor

O leitor opcional `edit21.py` é uma adaptação em Python das rotinas de leitura do projeto [4ccEditor](https://github.com/the4chancup/4ccEditor), publicado sob a licença zlib. A adaptação está identificada no próprio arquivo e o aviso original foi preservado em `THIRD_PARTY_NOTICES.md`.

## Opcionais

### EDIT descriptografado

`potencial.py` pode comparar a idade atual da carreira com um `data.dat` do EDIT para diferenciar jogadores normais, regens e jogadores gerados.

Defina a variável:

```bat
set "PES2021_EDIT_DATA=C:\caminho\para\EDIT_descriptografado\data.dat"
```

Sem esse arquivo, jogadores com o bit interno de geração continuam sendo identificados; os demais são tratados com segurança como jogadores normais.

## Variáveis de ambiente

| Variável | Finalidade |
|---|---|
| `PES2021_GAME_DIR` | pasta que contém o jogo e os arquivos `mercado_*.txt/bin` |
| `PES2021_SAVE_DIR` | pasta exata que contém `ML00000000`, `ML00000001` etc. |
| `MERCADO_IA_TOOLS_DIR` | pasta de ferramentas, backups e `pesXdecrypter` |
| `PES2021_DECRYPTER` | caminho completo alternativo para `decrypter21.exe` |
| `PES2021_ENCRYPTER` | caminho completo alternativo para `encrypter21.exe` |
| `PES2021_EDIT_DATA` | caminho opcional para o `data.dat` do EDIT descriptografado |

Quando nenhuma variável é definida, o projeto usa a estrutura de pastas descrita no guia de instalação.
