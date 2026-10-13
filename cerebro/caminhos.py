# Mercado IA — autor: William (https://github.com/WilliamProgramadorBR)
"""CAMINHOS DO MERCADO IA (12/10/2026): fonte única das pastas do jogo, dos saves e das ferramentas.

Antes, cada arquivo montava o caminho do seu jeito ("..\\..\\eFootball PES 2021", OneDrive\\Documentos...), o que só
funcionava no PC de desenvolvimento. Para o pacote da comunidade, a ordem de prioridade é:
  1. variável de ambiente (PES2021_GAME_DIR, PES2021_SAVE_DIR, PES2021_DECRYPTER, PES2021_ENCRYPTER, MERCADO_IA_TOOLS_DIR);
  2. config.json na pasta de ferramentas (gravado pelo assistente do Painel);
  3. o padrão antigo (pasta do jogo ao lado da pasta Ferramentas) e a detecção automática dos saves.
"""
import glob
import json
import os

PAINEL = os.environ.get('MERCADO_IA_PAINEL') == '1'      # rodando dentro do Painel (ele cuida dos processos)
if os.environ.get('MERCADO_IA_SEM_JANELA') == '1' and os.name == 'nt':
    # dentro do Painel não há console: sem isto, cada programa auxiliar (decrypter, tasklist, reunião) abriria uma
    # janela piscando por cima do jogo
    import subprocess as _sp
    if not getattr(_sp.Popen, '_sem_janela', False):
        _init = _sp.Popen.__init__

        def _sem_janela(self, *a, **k):
            fl = k.get('creationflags', 0) or 0
            if not fl & 0x00000010:          # CREATE_NEW_CONSOLE pedido de propósito: respeita
                k['creationflags'] = fl | 0x08000000
            _init(self, *a, **k)
        _sp.Popen.__init__ = _sem_janela
        _sp.Popen._sem_janela = True

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.normpath(os.environ.get('MERCADO_IA_TOOLS_DIR') or os.path.join(HERE, '..'))
ARQ_CONFIG = os.path.join(TOOLS, 'config.json')
HIST = os.path.join(HERE, 'historico')


def config():
    try:
        with open(ARQ_CONFIG, encoding='utf-8') as f:
            return json.load(f) or {}
    except (OSError, ValueError):
        return {}


def gravar_config(novo):
    c = config()
    c.update(novo)
    tmp = ARQ_CONFIG + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(c, f, ensure_ascii=False, indent=2)
    os.replace(tmp, ARQ_CONFIG)
    return c


_C = config()


def _p(env, chave, padrao):
    v = os.environ.get(env) or _C.get(chave) or padrao
    return os.path.normpath(os.path.expandvars(v))


GAME_DIR = _p('PES2021_GAME_DIR', 'jogo', os.path.join(TOOLS, '..', 'eFootball PES 2021'))
DECRYPT = _p('PES2021_DECRYPTER', 'decrypter', os.path.join(TOOLS, 'pesXdecrypter', 'decrypter21.exe'))
ENCRYPT = _p('PES2021_ENCRYPTER', 'encrypter', os.path.join(TOOLS, 'pesXdecrypter', 'encrypter21.exe'))
SNAP = os.path.join(GAME_DIR, 'mercado_snap.bin')
STATUS_VIGIA = os.path.join(GAME_DIR, 'mercado_status.txt')
BACKUPS = os.path.join(TOOLS, 'Backups')
SAVE_WORK = os.path.join(TOOLS, 'save_work')


# ---------------------------------------------------------------- saves
def _documentos():
    """Pastas 'Documentos' possíveis (a pasta real do Windows, mesmo redirecionada para o OneDrive)."""
    out = []
    try:
        import ctypes
        from ctypes import wintypes
        buf = ctypes.c_wchar_p()
        fid = ctypes.c_byte * 16
        # FOLDERID_Documents {FDD39AD0-238F-46AF-ADB4-6C85480369C7}
        g = fid(*bytes.fromhex('d09ad3fd8f23af46adb46c85480369c7'))
        if ctypes.windll.shell32.SHGetKnownFolderPath(ctypes.byref(g), 0, None, ctypes.byref(buf)) == 0:
            out.append(buf.value)
            ctypes.windll.ole32.CoTaskMemFree(buf)
    except Exception:  # noqa: BLE001 - fora do Windows / sem ctypes
        pass
    perfil = os.environ.get('USERPROFILE', '')
    for sub in (r'OneDrive\Documentos', r'OneDrive\Documents', 'Documentos', 'Documents'):
        out.append(os.path.join(perfil, sub))
    vistos, res = set(), []
    for p in out:
        k = os.path.normcase(os.path.normpath(p))
        if p and k not in vistos:
            vistos.add(k)
            res.append(p)
    return res


def raiz_saves():
    """...\\KONAMI\\eFootball PES 2021 SEASON UPDATE (contém uma pasta por conta, cada uma com \\save)."""
    fixo = os.environ.get('PES2021_SAVE_DIR') or _C.get('saves')
    if fixo:
        fixo = os.path.normpath(os.path.expandvars(fixo))
        # aceita tanto a pasta \\save quanto a raiz KONAMI\\...\\SEASON UPDATE
        return os.path.dirname(os.path.dirname(fixo)) if os.path.basename(fixo).lower() == 'save' else fixo
    for doc in _documentos():
        p = os.path.join(doc, 'KONAMI', 'eFootball PES 2021 SEASON UPDATE')
        if os.path.isdir(p):
            return p
    return os.path.join(_documentos()[0] if _documentos() else '', 'KONAMI', 'eFootball PES 2021 SEASON UPDATE')


def pastas_save():
    """Todas as pastas \\save com carreiras (ML00000000...)."""
    fixo = os.environ.get('PES2021_SAVE_DIR') or _C.get('saves')
    if fixo and os.path.basename(os.path.normpath(fixo)).lower() == 'save':
        return [os.path.normpath(os.path.expandvars(fixo))]
    return [p for p in glob.glob(os.path.join(raiz_saves(), '*', 'save')) if os.path.isdir(p)]


def globs_save():
    """Padrões de busca das pastas de save (formato antigo do vigia)."""
    fixo = os.environ.get('PES2021_SAVE_DIR') or _C.get('saves')
    if fixo and os.path.basename(os.path.normpath(fixo)).lower() == 'save':
        return [os.path.normpath(os.path.expandvars(fixo))]
    return [os.path.join(raiz_saves(), '*', 'save')]


# ---------------------------------------------------------------- detecção da pasta do jogo
def _bibliotecas_steam():
    libs = []
    try:
        import winreg
        for raiz, chave in ((winreg.HKEY_CURRENT_USER, r'Software\Valve\Steam'),
                            (winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\WOW6432Node\Valve\Steam')):
            try:
                with winreg.OpenKey(raiz, chave) as k:
                    for nome in ('SteamPath', 'InstallPath'):
                        try:
                            libs.append(os.path.normpath(winreg.QueryValueEx(k, nome)[0]))
                        except OSError:
                            pass
            except OSError:
                pass
    except ImportError:
        pass
    for s in list(libs):
        vdf = os.path.join(s, 'steamapps', 'libraryfolders.vdf')
        try:
            import re
            for m in re.finditer(r'"path"\s+"([^"]+)"', open(vdf, encoding='utf-8', errors='replace').read()):
                libs.append(os.path.normpath(m.group(1).replace('\\\\', '\\')))
        except OSError:
            pass
    return list(dict.fromkeys(libs))


def detectar_jogo():
    """Pastas candidatas que contêm PES2021.exe (Steam e locais comuns)."""
    cands = [os.path.join(lib, 'steamapps', 'common', n) for lib in _bibliotecas_steam()
             for n in ('eFootball PES 2021', 'eFootball PES 2021 SEASON UPDATE', 'PES2021')]
    for drive in 'CDEFGH':
        for sub in (r'Program Files (x86)\Steam\steamapps\common\eFootball PES 2021', r'Games\eFootball PES 2021',
                    r'eFootball PES 2021', r'Pro Evolution Soccer 2021', r'Pro Evolution Soccer 2026\eFootball PES 2021'):
            cands.append(f'{drive}:\\{sub}')
    cands.append(os.path.join(TOOLS, '..', 'eFootball PES 2021'))
    out = []
    for c in cands:
        c = os.path.normpath(c)
        if os.path.isfile(os.path.join(c, 'PES2021.exe')) and c not in out:
            out.append(c)
    return out
