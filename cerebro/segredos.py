# Mercado IA — autor: William (https://github.com/WilliamProgramadorBR)
"""SEGREDOS (13/10/2026): a chave do Google Gemini mora num arquivo .env, fora do código e do git.

  <pasta da ferramenta>\\.env        (no pacote: app\\.env; no desenvolvimento: Ferramentas\\.env)
      GEMINI_API_KEY=dpapi:AQAAANCMnd8B...      <- gravada pelo Painel, criptografada pelo Windows (DPAPI)
      GEMINI_API_KEY=AIza...                    <- também aceita a chave em texto, se você editar à mão

Ordem de leitura: variável de ambiente GEMINI_API_KEY -> .env -> "chave" antiga do ia.json (compatibilidade).
DPAPI (CryptProtectData) amarra a criptografia à conta do Windows de quem gravou: o arquivo copiado para outro PC ou
outro usuário não abre. O .env nunca vai para o git (.gitignore), nem para o pacote, nem é trocado pela atualização.
"""
import base64
import ctypes
import os
from ctypes import wintypes

import caminhos

ARQ_ENV = os.path.join(caminhos.TOOLS, '.env')
VAR = 'GEMINI_API_KEY'


class _Blob(ctypes.Structure):
    _fields_ = [('cbData', wintypes.DWORD), ('pbData', ctypes.POINTER(ctypes.c_char))]


def _blob(b):
    buf = ctypes.create_string_buffer(b, len(b))
    return _Blob(len(b), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char))), buf


def _dpapi(dados, proteger):
    entrada, _buf = _blob(dados)
    saida = _Blob()
    f = ctypes.windll.crypt32.CryptProtectData if proteger else ctypes.windll.crypt32.CryptUnprotectData
    ok = (f(ctypes.byref(entrada), 'Mercado IA' if proteger else None, None, None, None, 0, ctypes.byref(saida)) if proteger
          else f(ctypes.byref(entrada), None, None, None, None, 0, ctypes.byref(saida)))
    if not ok:
        raise OSError('DPAPI recusou (o .env foi gravado por outro usuário do Windows?)')
    try:
        return ctypes.string_at(saida.pbData, saida.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(saida.pbData)


def _ler_env():
    out = {}
    try:
        with open(ARQ_ENV, encoding='utf-8') as f:
            for linha in f:
                linha = linha.strip()
                if linha and not linha.startswith('#') and '=' in linha:
                    k, v = linha.split('=', 1)
                    out[k.strip()] = v.strip().strip('"').strip("'")
    except OSError:
        pass
    return out


def chave_gemini():
    """A chave do Gemini, ou '' se não houver."""
    v = os.environ.get(VAR) or _ler_env().get(VAR) or ''
    if v.startswith('dpapi:'):
        try:
            v = _dpapi(base64.b64decode(v[6:]), False).decode('utf-8')
        except Exception:  # noqa: BLE001
            return ''
    if not v:   # compatibilidade: chave antiga dentro do ia.json
        try:
            import json
            v = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ia.json'), encoding='utf-8')).get('chave') or ''
        except (OSError, ValueError):
            v = ''
    return '' if v == 'COLE_SUA_CHAVE_AQUI' else v.strip()


def gravar_chave_gemini(valor):
    """Grava a chave no .env, criptografada pela conta do Windows (DPAPI). Valor vazio apaga a linha."""
    env = _ler_env()
    valor = (valor or '').strip()
    if valor:
        try:
            env[VAR] = 'dpapi:' + base64.b64encode(_dpapi(valor.encode('utf-8'), True)).decode('ascii')
        except Exception:  # noqa: BLE001 - sem DPAPI (fora do Windows): grava em texto
            env[VAR] = valor
    else:
        env.pop(VAR, None)
    tmp = ARQ_ENV + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        f.write('# Mercado IA — segredos locais. NÃO compartilhe este arquivo. Gravado pelo Painel.\n')
        for k, v in env.items():
            f.write(f'{k}={v}\n')
    os.replace(tmp, ARQ_ENV)
    return ARQ_ENV
