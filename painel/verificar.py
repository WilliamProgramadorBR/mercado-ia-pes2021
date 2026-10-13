# Mercado IA — autor: William (https://github.com/WilliamProgramadorBR)
"""Verificações do ambiente e instalação no Sider (sem Qt: dá para testar e usar no instalador).

Cada verificação devolve um Item(id, titulo, estado, detalhe, acao): estado 'ok', 'aviso' ou 'erro'; acao = o nome de
uma correção que o Painel sabe fazer ('instalar_modulo', 'ligar_lua', 'baixar_decrypter', 'escolher_jogo'...).
O Sider é obrigatório: é ele que carrega o MercadoIA.lua dentro do jogo (foto da memória, overlay, teclas).
"""
import datetime as dt
import glob
import json
import os
import re
import shutil
import sys
import urllib.request
import zipfile
from dataclasses import dataclass

from painel import base

EXE_VALIDADO = '1.1.0.0'       # versão do PES2021.exe em que os endereços de memória foram mapeados
SIDER_VALIDADO = '7.3.3'
GEMINI_CHAVES = 'https://aistudio.google.com/apikey'
DECRYPTER_API = 'https://api.github.com/repos/the4chancup/pesXdecrypter/releases/latest'
DECRYPTER_PAGINA = 'https://github.com/the4chancup/pesXdecrypter/releases'
# pesXdecrypter 6.0.0 (PES 2021), domínio público + aviso MT19937: vem DENTRO do pacote (se o link mudar, o mod segue
# funcionando); a impressão digital confirma que são os executáveis oficiais
DECRYPTER_SHA256 = {'decrypter21.exe': '47402eb555b51fd93ef3de447e5c97873392962f1873027596c5bd27424a6114',
                    'encrypter21.exe': '54bea5430ad3e818bf58f68c56454a8d839f19a17d867ba718d38aa97da2e3ea'}
DECRYPTER_7Z = ('https://github.com/the4chancup/pesXdecrypter/releases/download/6.0.0/pesXdecrypter_2021.7z',
                '201800b731a8c90109b30afeef26fb0cdcd552d2910b322bbc253b000d6aa3a6')


def sha256(caminho):
    import hashlib
    h = hashlib.sha256()
    with open(caminho, 'rb') as f:
        for b in iter(lambda: f.read(1 << 16), b''):
            h.update(b)
    return h.hexdigest()


def decrypter_oficial(pasta):
    """True se os dois executáveis da pasta são os oficiais (impressão digital confere)."""
    try:
        return all(sha256(os.path.join(pasta, n)) == h for n, h in DECRYPTER_SHA256.items())
    except OSError:
        return False
SIDER_PAGINA = 'https://github.com/juce/sider/releases'


@dataclass
class Item:
    id: str
    titulo: str
    estado: str
    detalhe: str = ''
    acao: str = ''


def versao_arquivo(caminho):
    """FileVersion de um .exe/.dll (sem bibliotecas externas)."""
    try:
        import ctypes
        from ctypes import wintypes
        v = ctypes.windll.version
        n = v.GetFileVersionInfoSizeW(caminho, None)
        if not n:
            return None
        buf = ctypes.create_string_buffer(n)
        v.GetFileVersionInfoW(caminho, 0, n, buf)
        ptr, tam = ctypes.c_void_p(), wintypes.UINT()
        v.VerQueryValueW(buf, '\\', ctypes.byref(ptr), ctypes.byref(tam))
        ms, ls = ctypes.cast(ptr, ctypes.POINTER(wintypes.DWORD * 13)).contents[2:4]
        return f'{ms >> 16}.{ms & 0xFFFF}.{ls >> 16}.{ls & 0xFFFF}'
    except Exception:  # noqa: BLE001
        return None


# ---------------------------------------------------------------- Sider
def sider_ini(jogo):
    return os.path.join(jogo, 'sider.ini')


def ler_sider(jogo):
    try:
        with open(sider_ini(jogo), encoding='utf-8', errors='replace') as f:
            return f.read()
    except OSError:
        return None


def _ativo(linha):
    return not linha.lstrip().startswith(';')


def lua_ligado(txt):
    return any(_ativo(l) and re.match(r'\s*lua\.enabled\s*=\s*1\b', l) for l in txt.splitlines())


def modulo_listado(txt, nome='MercadoIA.lua'):
    return any(_ativo(l) and re.match(r'\s*lua\.module\s*=\s*"' + re.escape(nome) + '"', l) for l in txt.splitlines())


def _backup(caminho):
    if os.path.exists(caminho):
        destino = os.path.join(base.TOOLS, 'Backups', 'sider')
        os.makedirs(destino, exist_ok=True)
        shutil.copy2(caminho, os.path.join(destino, f'{os.path.basename(caminho)}.{dt.datetime.now():%Y%m%d_%H%M%S}'))


def instalar_modulo(jogo):
    """Copia o MercadoIA.lua para <jogo>\\modules e acrescenta a linha no sider.ini (com backup). Devolve o que fez."""
    feito = []
    origem = base.MODULO_LUA
    if not os.path.isfile(origem):
        raise FileNotFoundError(f'MercadoIA.lua não encontrado no pacote ({origem})')
    mods = os.path.join(jogo, 'modules')
    os.makedirs(mods, exist_ok=True)
    destino = os.path.join(mods, 'MercadoIA.lua')
    if not os.path.isfile(destino) or open(destino, 'rb').read() != open(origem, 'rb').read():
        _backup(destino)
        shutil.copy2(origem, destino)
        feito.append('MercadoIA.lua copiado para modules')
    txt = ler_sider(jogo)
    if txt is None:
        raise FileNotFoundError('sider.ini não encontrado na pasta do jogo: instale o Sider primeiro')
    novo = txt
    if not lua_ligado(novo):
        if re.search(r'^\s*;?\s*lua\.enabled\s*=.*$', novo, flags=re.M):
            novo = re.sub(r'^\s*;?\s*lua\.enabled\s*=.*$', 'lua.enabled = 1', novo, count=1, flags=re.M)
        else:
            novo += '\nlua.enabled = 1\n'
        feito.append('lua.enabled = 1')
    if not modulo_listado(novo):
        linhas = novo.splitlines()
        ult = max((i for i, l in enumerate(linhas) if re.match(r'\s*lua\.module\s*=', l)), default=None)
        nova = 'lua.module = "MercadoIA.lua"'
        if ult is None:
            linhas.append(nova)
        else:
            linhas.insert(ult + 1, nova)
        novo = '\n'.join(linhas) + '\n'
        feito.append('lua.module = "MercadoIA.lua" no sider.ini')
    if novo != txt:
        _backup(sider_ini(jogo))
        with open(sider_ini(jogo), 'w', encoding='utf-8', newline='\r\n') as f:
            f.write(novo.replace('\r\n', '\n'))
    return feito or ['já estava tudo instalado']


# ---------------------------------------------------------------- pesXdecrypter
def baixar_decrypter(log=print):
    """Baixa o pesXdecrypter oficial do PES 2021 (GitHub, the4chancup) e extrai decrypter21.exe/encrypter21.exe (e a
    licença) para a pasta padrão. O pacote do PES 21 é um .7z: o Windows 10/11 abre com o tar.exe que já vem nele."""
    import subprocess
    import tempfile
    rel = {'tag_name': '6.0.0'}
    ativo = {'name': 'pesXdecrypter_2021.7z', 'browser_download_url': DECRYPTER_7Z[0]}
    destino = os.path.join(base.TOOLS, 'pesXdecrypter')
    os.makedirs(destino, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        arq = os.path.join(tmp, ativo['name'])
        log(f'baixando {ativo["name"]} ({rel.get("tag_name")})...')
        with urllib.request.urlopen(urllib.request.Request(ativo['browser_download_url'], headers={'User-Agent': 'MercadoIA-Painel'}), timeout=120) as r, \
                open(arq, 'wb') as f:
            shutil.copyfileobj(r, f)
        if sha256(arq) != DECRYPTER_7Z[1]:
            raise RuntimeError('o arquivo baixado não é o pacote oficial (impressão digital diferente): não vou usar')
        if arq.lower().endswith('.zip'):
            with zipfile.ZipFile(arq) as z:
                z.extractall(tmp)
        else:
            tar = os.path.join(os.environ.get('SystemRoot', r'C:\Windows'), 'System32', 'tar.exe')
            subprocess.run([tar, '-xf', arq, '-C', tmp], check=True, capture_output=True, creationflags=0x08000000)
        achados = []
        for raiz, _, arqs in os.walk(tmp):
            for n in arqs:
                if n.lower() in ('decrypter21.exe', 'encrypter21.exe', 'license.txt'):
                    shutil.copy2(os.path.join(raiz, n), os.path.join(destino, n if not n.lower() == 'license.txt' else 'LICENSE_pesXdecrypter.txt'))
                    achados.append(n.lower())
    if not {'decrypter21.exe', 'encrypter21.exe'} <= set(achados):
        raise RuntimeError(f'o pacote não trazia os dois executáveis (achei: {achados or "nenhum"})')
    if not decrypter_oficial(destino):
        raise RuntimeError('os executáveis extraídos não conferem com a versão oficial')
    return destino


# ---------------------------------------------------------------- IA (Gemini)
def ia_config():
    try:
        with open(base.ARQ_IA, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return {'provedor': 'gemini', 'modelo': 'gemini-2.5-flash', 'chave': '', 'ligado': False}


def gravar_ia(chave=None, ligado=None, modelo=None):
    c = ia_config()
    if chave is not None:
        c['chave'] = chave.strip()
    if ligado is not None:
        c['ligado'] = bool(ligado)
    if modelo:
        c['modelo'] = modelo
    c['provedor'] = 'gemini'
    with open(base.ARQ_IA, 'w', encoding='utf-8') as f:
        json.dump(c, f, ensure_ascii=False)
    return c


def testar_gemini(chave, modelo):
    """Faz uma chamada mínima ao Gemini. Devolve (ok, mensagem). A chave só vai para o Google."""
    url = f'https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent?key={chave}'
    corpo = json.dumps({'contents': [{'parts': [{'text': 'Responda só: ok'}]}]}).encode()
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, data=corpo, headers={'Content-Type': 'application/json'}), timeout=30)
        json.load(r)
        return True, 'Gemini respondeu: a chave funciona.'
    except urllib.error.HTTPError as e:
        try:
            msg = json.load(e).get('error', {}).get('message', '')
        except Exception:  # noqa: BLE001
            msg = ''
        return False, f'O Google recusou ({e.code}). {msg[:160]}'
    except Exception as e:  # noqa: BLE001
        return False, f'Sem resposta do Google: {e}'


# ---------------------------------------------------------------- a lista de verificações
def tudo(cfg=None):
    import caminhos as C
    cfg = cfg or C.config()
    jogo = cfg.get('jogo') or C.GAME_DIR
    out = []
    v = sys.version_info
    out.append(Item('python', 'Python', 'ok' if v >= (3, 10) else 'erro', f'{v.major}.{v.minor}.{v.micro} ({sys.executable})'))
    exe = os.path.join(jogo, 'PES2021.exe')
    if not os.path.isfile(exe):
        out.append(Item('jogo', 'Pasta do PES 2021', 'erro', f'PES2021.exe não encontrado em {jogo}', 'escolher_jogo'))
        return out
    ver = versao_arquivo(exe)
    out.append(Item('jogo', 'Pasta do PES 2021', 'ok' if ver in (None, EXE_VALIDADO) else 'aviso',
                    f'{jogo} — PES2021.exe {ver or "?"}' + ('' if ver in (None, EXE_VALIDADO) else
                                                         f' (os endereços de memória foram mapeados no {EXE_VALIDADO})')))
    dll = os.path.join(jogo, 'sider.dll')
    txt = ler_sider(jogo)
    if not os.path.isfile(dll) or txt is None:
        out.append(Item('sider', 'Sider (obrigatório)', 'erro', f'sider.dll/sider.ini não encontrados. Instale o Sider ({SIDER_PAGINA}).', 'abrir_sider'))
    else:
        vs = versao_arquivo(dll) or '?'
        out.append(Item('sider', 'Sider (obrigatório)', 'ok' if vs.startswith(SIDER_VALIDADO) else 'aviso',
                        f'versão {vs}' + ('' if vs.startswith(SIDER_VALIDADO) else f' (testado com {SIDER_VALIDADO})')))
        out.append(Item('lua', 'Lua ligado no Sider', 'ok' if lua_ligado(txt) else 'erro',
                        'lua.enabled = 1' if lua_ligado(txt) else 'falta "lua.enabled = 1" no sider.ini', '' if lua_ligado(txt) else 'instalar_modulo'))
        mod = os.path.join(jogo, 'modules', 'MercadoIA.lua')
        igual = os.path.isfile(mod) and os.path.isfile(base.MODULO_LUA) and open(mod, 'rb').read() == open(base.MODULO_LUA, 'rb').read()
        listado = modulo_listado(txt)
        estado = 'ok' if os.path.isfile(mod) and listado else 'erro'
        if estado == 'ok' and not igual:
            estado = 'aviso'
        out.append(Item('modulo', 'Módulo MercadoIA.lua', estado,
                        'instalado e listado no sider.ini' + ('' if igual or estado == 'erro' else ' (versão diferente da do pacote)')
                        if estado != 'erro' else ('arquivo ausente em modules' if not os.path.isfile(mod) else 'falta a linha no sider.ini'),
                        '' if estado == 'ok' else 'instalar_modulo'))
    dec = cfg.get('decrypter') or C.DECRYPT
    enc = cfg.get('encrypter') or C.ENCRYPT
    ok_d = os.path.isfile(dec) and os.path.isfile(enc)
    oficial = ok_d and decrypter_oficial(os.path.dirname(dec)) and os.path.dirname(dec) == os.path.dirname(enc)
    out.append(Item('decrypter', 'pesXdecrypter', 'ok' if oficial else 'aviso' if ok_d else 'erro',
                    (f'{os.path.dirname(dec)} — versão oficial 6.0.0 (impressão digital conferida)' if oficial else
                     f'{os.path.dirname(dec)} — executáveis diferentes da versão oficial' if ok_d else
                     'decrypter21.exe / encrypter21.exe não encontrados'), '' if oficial else 'baixar_decrypter'))
    saves = C.pastas_save()
    mls = [f for d in saves for f in glob.glob(os.path.join(d, 'ML0000000?'))]
    out.append(Item('saves', 'Saves da Master League', 'ok' if mls else 'aviso',
                    f'{len(mls)} carreira(s) em {saves[0]}' if mls else f'nenhuma carreira encontrada em {C.raiz_saves()}', '' if mls else 'escolher_saves'))
    snap = os.path.join(jogo, 'mercado_snap.bin')
    out.append(Item('snap', 'Foto da memória (gerada pelo jogo)', 'ok' if os.path.isfile(snap) else 'aviso',
                    f'última: {dt.datetime.fromtimestamp(os.path.getmtime(snap)):%d/%m %H:%M}' if os.path.isfile(snap)
                    else 'ainda não existe: abra uma carreira com o Sider ligado'))
    ia = ia_config()
    tem = bool(ia.get('chave')) and ia.get('chave') != 'COLE_SUA_CHAVE_AQUI'
    out.append(Item('ia', 'IA de texto (Google Gemini, opcional)', 'ok' if (tem and ia.get('ligado')) or not ia.get('ligado') else 'aviso',
                    ('ligada' if ia.get('ligado') else 'desligada (textos prontos)') + (' · chave configurada' if tem else ' · sem chave')))
    return out
