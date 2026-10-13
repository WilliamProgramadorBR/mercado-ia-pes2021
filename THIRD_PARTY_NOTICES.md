# Avisos de terceiros

## 4ccEditor

O arquivo `edit21.py` adapta para Python rotinas de leitura de dados do [4ccEditor](https://github.com/the4chancup/4ccEditor). A versão deste repositório foi alterada e não deve ser confundida com o software original.

```text
Copyright (c) 2020 The 4chan Cup (http://implyingrigged.info)

This software is provided 'as-is', without any express or implied warranty. In no event will the authors be held liable for any damages arising from the use of this software.

Permission is granted to anyone to use this software for any purpose, including commercial applications, and to alter it and redistribute it freely, subject to the following restrictions:

1. The origin of this software must not be misrepresented; you must not claim that you wrote the original software. If you use this software in a product, an acknowledgement in the product documentation would be appreciated but is not required.
2. Altered source versions must be plainly marked as such, and must not be misrepresented as being the original software.
3. This notice may not be removed or altered from any source distribution.
```

## Componentes incluídos no pacote do Painel (instalador e versão portátil)

O pacote para Windows redistribui, sem modificações, os componentes abaixo. O código-fonte de cada um está disponível nos endereços indicados.

- **Python** (pacote *embeddable* oficial do python.org): Python Software Foundation License. A licença completa vai junto, em `runtime\LICENSE.txt`. https://www.python.org
- **PySide6 / Qt for Python e Qt 6** (incluindo o Qt WebEngine): GNU Lesser General Public License v3 (LGPLv3). As bibliotecas são usadas por ligação dinâmica, sem alterações, e podem ser substituídas por outra versão compatível na pasta `runtime\Lib\site-packages`. Os textos de licença vão junto, nas pastas `*.dist-info` dos pacotes. Código-fonte: https://code.qt.io e https://download.qt.io/official_releases/QtForPython/ . O Qt WebEngine inclui o Chromium, com as licenças dos seus componentes listadas pelo próprio Qt.
- **Pillow**: licença MIT-CMU (HPND). https://python-pillow.org

## pesXdecrypter

O pacote do Painel (instalador e versão portátil) inclui, sem modificações, o `decrypter21.exe` e o `encrypter21.exe` da versão 6.0.0 do [pesXdecrypter](https://github.com/the4chancup/pesXdecrypter), na pasta `app\pesXdecrypter`, junto com a licença original (`LICENSE_pesXdecrypter.txt`). O Painel confere a impressão digital (SHA-256) dos dois executáveis. O código-fonte deste repositório não inclui os binários; o script de empacotamento os embute.

O pesXdecrypter foi dedicado ao domínio público pelos seus autores. Ele usa o código do Mersenne Twister (`mt19937ar.c`), que não é de domínio público. A licença desse trecho permite redistribuir o programa compilado, desde que este aviso acompanhe a documentação:

```text
A C-program for MT19937, with initialization improved 2002/1/26.
Coded by Takuji Nishimura and Makoto Matsumoto.

Copyright (C) 1997 - 2002, Makoto Matsumoto and Takuji Nishimura,
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions
are met:

  1. Redistributions of source code must retain the above copyright
     notice, this list of conditions and the following disclaimer.

  2. Redistributions in binary form must reproduce the above copyright
     notice, this list of conditions and the following disclaimer in the
     documentation and/or other materials provided with the distribution.

  3. The names of its contributors may not be used to endorse or promote
     products derived from this software without specific prior written
     permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
"AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
A PARTICULAR PURPOSE ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR
CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
```

## PES 2021, eFootball e KONAMI

PES, eFootball e KONAMI são marcas de seus respectivos proprietários. Nenhum arquivo do jogo é distribuído neste repositório.
