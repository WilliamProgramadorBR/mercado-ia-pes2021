# Instalação manual (a partir do código)

> Para jogar, use o instalador ou a versão portátil e siga o [Manual](MANUAL.md): o Painel faz tudo isto sozinho. Este guia é para quem roda direto do código.

## 1. Faça backups

Copie toda a pasta de saves da Master Liga para outro local antes do primeiro teste. O projeto também cria backups automáticos, mas eles não substituem um backup manual.

## 2. Prepare as dependências

Instale Python 3.10+ e Sider. Baixe `decrypter21.exe` e `encrypter21.exe` nos releases oficiais do `pesXdecrypter`.

Uma estrutura compatível com os caminhos padrão é:

```text
Pasta principal/
├─ eFootball PES 2021/
│  ├─ PES2021.exe
│  ├─ sider.ini
│  └─ modules/
│     └─ MercadoIA.lua
└─ Ferramentas/
   ├─ edit21.py
   ├─ cerebro/
   │  ├─ aplicar.py
   │  ├─ vigia.py
   │  └─ ...
   └─ pesXdecrypter/
      ├─ decrypter21.exe
      └─ encrypter21.exe
```

Copie `sider/MercadoIA.lua` para `modules` e o conteúdo de `cerebro` para `Ferramentas/cerebro`. Copie `edit21.py` para `Ferramentas` caso pretenda usar a classificação opcional de potencial.

Se sua estrutura for diferente, use as variáveis descritas em [Dependências](DEPENDENCIAS.md).

## 3. Configure o Sider

Acrescente ao `sider.ini`:

```ini
lua.module = "MercadoIA.lua"
```

O módulo grava `mercado_snap.bin`, `mercado_pedido.txt`, `mercado_status.txt` e `mercado_noticias.txt` na pasta de execução do jogo.

## 4. Configure o mercado

Copie `mercado_config.example.json` como `cerebro/mercado_config.json` e altere `time_do_usuario` para o nome exato exibido internamente pelo jogo.

```json
{
  "time_do_usuario": "MANCHESTER UNITED",
  "compradores": "TODOS",
  "max_transferencias": 25,
  "contratar_livres": false,
  "semente": null,
  "limite_janela_verao": 40,
  "limite_janela_inverno": 20,
  "bloquear_fora_da_janela": true
}
```

## 5. Configure o lançador

Copie `launcher.example.bat` para um nome local, edite os três caminhos e execute-o. O exemplo inicia apenas o vigia; depois abra seu launcher habitual do PES/Sider.

## 6. Primeiro teste

Antes de permitir alterações, use uma cópia do save:

```powershell
python cerebro\aplicar.py "C:\copia\ML00000000" "C:\PES2021\mercado_snap.bin" --ensaio
```

O relatório deve terminar com `modo ensaio: save NÃO foi alterado`.

## Compatibilidade

O snapshot Lua utiliza uma faixa de memória encontrada empiricamente. Se `dados.py` retornar zero jogadores, a versão do executável provavelmente utiliza outros endereços. Não tente aplicar uma janela até refazer e validar o mapeamento.
