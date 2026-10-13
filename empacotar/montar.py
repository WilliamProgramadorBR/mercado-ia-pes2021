# Mercado IA — autor: William (https://github.com/WilliamProgramadorBR)
"""MONTA O PACOTE DO MERCADO IA (12/10/2026).

  python empacotar\\montar.py            -> dist\\MercadoIA\\ (pronto para rodar) + MercadoIA-portatil-<versão>.zip
                                           + MercadoIA-Setup-<versão>.exe (se o Inno Setup 6 estiver instalado)

O pacote leva o Python OFICIAL embutido (python.org, "embeddable package"): o jogador não instala Python, nada vai para
o registro do Windows e os executáveis são os assinados pela Python Software Foundation (um .exe gerado por
PyInstaller costuma ser barrado pelo antivírus — pior ainda num mod que escreve na memória do jogo).

dist\\MercadoIA\\
  runtime\\        Python embutido + PySide6 (Qt6) + Pillow
  app\\painel\\     o Painel (Qt6)
  app\\cerebro\\    o motor e a Central (sem dados pessoais: historico/, ia.json, saves ficam de fora)
  app\\sider\\      MercadoIA.lua (o Painel instala no Sider do jogador)
  app\\docs\\       manual
  Mercado IA.cmd  atalho da versão portátil
"""
import fnmatch
import os
import re
import shutil
import subprocess
import sys
import urllib.request
import zipfile

AQUI = os.path.dirname(os.path.abspath(__file__))
FERRAMENTAS = os.path.normpath(os.path.join(AQUI, '..'))
# rodando de dentro do repositório (sider/ e docs/ ao lado) ou da pasta Ferramentas do desenvolvimento
REPO = FERRAMENTAS if os.path.isdir(os.path.join(FERRAMENTAS, 'sider')) else os.path.normpath(
    os.path.join(FERRAMENTAS, '..', 'eFootball PES 2021', 'mercado-ia-pes2021'))
DIST = os.path.join(FERRAMENTAS, 'dist')
PACOTE = os.path.join(DIST, 'MercadoIA')
PY_VER = '.'.join(map(str, sys.version_info[:3]))          # o mesmo Python do desenvolvimento
PY_TAG = f'{sys.version_info[0]}{sys.version_info[1]}'
PYSIDE = '6.12.0'
CACHE = os.path.join(AQUI, '_cache')

# nada pessoal nem gerado vai no pacote
FORA_CEREBRO = ['historico', '__pycache__', 'ia.json', 'automacao.json', 'mercado_config.json', 'central_rede.json',
                '*.db', '*.jsonl', '*.bin', 'teste_*.py', 'tmp_*', '*.tmp', 'fotos']
# partes do Qt que o Painel não usa (encolhe ~40%)
QT_FORA = ['Qt63D*', 'Qt6Quick3D*', 'Qt6Designer*', 'Qt6Bluetooth*', 'Qt6Nfc*', 'Qt6Sensors*', 'Qt6SerialPort*',
           'Qt6Location*', 'Qt6Multimedia*', 'Qt6SpatialAudio*', 'Qt6TextToSpeech*', 'Qt6Graphs*', 'Qt6DataVisualization*',
           'Qt6RemoteObjects*', 'Qt6Scxml*', 'Qt6StateMachine*', 'Qt6HttpServer*', 'Qt6VirtualKeyboard*', 'Qt6Help*',
           'Qt6Pdf*', 'Qt6ShaderTools*', 'Qt6Test*', 'Qt6UiTools*', 'designer.exe', 'linguist.exe', 'assistant.exe',
           'lupdate.exe', 'lrelease.exe', 'qmllint.exe', 'qmlls.exe', 'qmlformat.exe', 'balsam*.exe', 'qsb.exe',
           'Qt3D*', 'QtQuick3D*', 'QtDesigner*', 'QtBluetooth*', 'QtNfc*', 'QtSensors*', 'QtSerialPort*', 'QtLocation*',
           'QtMultimedia*', 'QtSpatialAudio*', 'QtTextToSpeech*', 'QtGraphs*', 'QtDataVisualization*', 'QtRemoteObjects*',
           'QtScxml*', 'QtStateMachine*', 'QtHttpServer*', 'QtHelp*', 'QtPdf*', 'QtTest*', 'QtUiTools*']


def log(*a):
    print(*a, flush=True)


def versao():
    txt = open(os.path.join(FERRAMENTAS, 'painel', 'base.py'), encoding='utf-8').read()
    return re.search(r"VERSAO = '([^']+)'", txt).group(1)


def baixar(url, destino):
    if os.path.isfile(destino):
        return destino
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    log('baixando', url)
    with urllib.request.urlopen(url, timeout=300) as r, open(destino + '.part', 'wb') as f:
        shutil.copyfileobj(r, f)
    os.replace(destino + '.part', destino)
    return destino


def runtime():
    rt = os.path.join(PACOTE, 'runtime')
    z = baixar(f'https://www.python.org/ftp/python/{PY_VER}/python-{PY_VER}-embed-amd64.zip',
               os.path.join(CACHE, f'python-{PY_VER}-embed-amd64.zip'))
    with zipfile.ZipFile(z) as f:
        f.extractall(rt)
    # o ._pth define o sys.path do Python embutido: o pacote (app) e os módulos instalados
    pth = os.path.join(rt, f'python{PY_TAG}._pth')
    with open(pth, 'w', encoding='utf-8') as f:
        f.write(f'python{PY_TAG}.zip\n.\nLib\\site-packages\n..\\app\n..\\app\\cerebro\n\nimport site\n')
    sp = os.path.join(rt, 'Lib', 'site-packages')
    os.makedirs(sp, exist_ok=True)
    log(f'instalando PySide6 {PYSIDE} e Pillow para o Python {PY_VER} embutido...')
    subprocess.run([sys.executable, '-m', 'pip', 'install', '--quiet', '--no-warn-script-location', '--target', sp,
                    '--only-binary=:all:', '--platform', 'win_amd64', '--python-version', PY_TAG, '--implementation', 'cp',
                    f'PySide6-Essentials=={PYSIDE}', f'PySide6-Addons=={PYSIDE}', f'shiboken6=={PYSIDE}', 'Pillow'],
                   check=True)
    removidos = 0
    for raiz, pastas, arqs in os.walk(sp, topdown=True):
        for nome in list(pastas) + arqs:
            if any(fnmatch.fnmatch(nome, p) for p in QT_FORA):
                c = os.path.join(raiz, nome)
                shutil.rmtree(c, ignore_errors=True) if os.path.isdir(c) else os.remove(c)
                removidos += 1
        pastas[:] = [p for p in pastas if os.path.isdir(os.path.join(raiz, p))]
    for sub in ('PySide6\\examples', 'PySide6\\include', 'PySide6\\glue', 'PySide6\\typesystems', 'PySide6\\qml'):
        shutil.rmtree(os.path.join(sp, sub), ignore_errors=True)
    tr = os.path.join(sp, 'PySide6', 'translations')
    if os.path.isdir(tr):   # só português
        for n in os.listdir(tr):
            if os.path.isfile(os.path.join(tr, n)) and not re.search(r'_pt(_BR)?\.qm$', n) and n != 'qtwebengine_locales':
                os.remove(os.path.join(tr, n))
        loc = os.path.join(tr, 'qtwebengine_locales')
        if os.path.isdir(loc):
            for n in os.listdir(loc):
                if not n.startswith(('pt-BR', 'en-US')):
                    os.remove(os.path.join(loc, n))
    log(f'Qt enxugado: {removidos} itens fora')


def copiar_app():
    app = os.path.join(PACOTE, 'app')
    ig_cerebro = shutil.ignore_patterns(*FORA_CEREBRO)
    shutil.copytree(os.path.join(FERRAMENTAS, 'cerebro'), os.path.join(app, 'cerebro'), ignore=ig_cerebro)
    shutil.copytree(os.path.join(FERRAMENTAS, 'painel'), os.path.join(app, 'painel'), ignore=shutil.ignore_patterns('__pycache__'))
    os.makedirs(os.path.join(app, 'sider'), exist_ok=True)
    shutil.copy2(os.path.join(REPO, 'sider', 'MercadoIA.lua'), os.path.join(app, 'sider', 'MercadoIA.lua'))
    shutil.copytree(os.path.join(REPO, 'docs'), os.path.join(app, 'docs'))
    for n in ('LICENSE', 'THIRD_PARTY_NOTICES.md', 'README.md'):
        if os.path.isfile(os.path.join(REPO, n)):
            shutil.copy2(os.path.join(REPO, n), os.path.join(app, n))
    shutil.copy2(os.path.join(FERRAMENTAS, 'cerebro', 'ia.json.exemplo'), os.path.join(app, 'cerebro', 'ia.json.exemplo'))
    # modelo inicial da rede dos jogos simulados (não tem nada pessoal: notas, forma e placares de jogos da IA)
    mod = os.path.join(FERRAMENTAS, 'cerebro', 'historico', 'rede_simulados.json')
    if os.path.isfile(mod):
        os.makedirs(os.path.join(app, 'cerebro', 'modelos'), exist_ok=True)
        shutil.copy2(mod, os.path.join(app, 'cerebro', 'modelos', 'rede_simulados.json'))
    os.makedirs(os.path.join(app, 'cerebro', 'historico'), exist_ok=True)
    # conferência: nada de segredo no pacote
    for raiz, _, arqs in os.walk(app):
        for n in arqs:
            if n in ('ia.json', 'central_rede.json') or n.endswith(('.db', '.jsonl')):
                raise SystemExit(f'ARQUIVO PESSOAL NO PACOTE: {os.path.join(raiz, n)}')
            if n.endswith(('.py', '.json', '.md', '.html', '.lua')):
                t = open(os.path.join(raiz, n), encoding='utf-8', errors='replace').read()
                if re.search(r'AIza[0-9A-Za-z_\-]{30,}', t):
                    raise SystemExit(f'CHAVE DE API NO PACOTE: {os.path.join(raiz, n)}')


def pesxdecrypter():
    """Embute o pesXdecrypter 6.0.0 (domínio público; o aviso do MT19937 vai junto, como a licença pede). Usa a cópia
    local se a impressão digital conferir; senão baixa o pacote oficial uma vez (cache) e confere."""
    sys.path.insert(0, FERRAMENTAS)
    from painel import verificar as V
    destino = os.path.join(PACOTE, 'app', 'pesXdecrypter')
    os.makedirs(destino, exist_ok=True)
    local = os.path.join(FERRAMENTAS, 'pesXdecrypter')
    if not V.decrypter_oficial(local):
        z = baixar(V.DECRYPTER_7Z[0], os.path.join(CACHE, 'pesXdecrypter_2021.7z'))
        if V.sha256(z) != V.DECRYPTER_7Z[1]:
            raise SystemExit('pesXdecrypter baixado não confere com a versão oficial')
        local = os.path.join(CACHE, 'pesXdecrypter')
        os.makedirs(local, exist_ok=True)
        subprocess.run([os.path.join(os.environ.get('SystemRoot', r'C:\Windows'), 'System32', 'tar.exe'), '-xf', z, '-C', local], check=True)
    for n in V.DECRYPTER_SHA256:
        shutil.copy2(os.path.join(local, n), os.path.join(destino, n))
    shutil.copy2(os.path.join(AQUI, 'terceiros', 'pesXdecrypter_LICENSE.txt'), os.path.join(destino, 'LICENSE_pesXdecrypter.txt'))
    if not V.decrypter_oficial(destino):
        raise SystemExit('pesXdecrypter no pacote não confere com a versão oficial')
    log('pesXdecrypter 6.0.0 embutido (impressão digital conferida)')


def icone():
    """app\\painel\\icone.ico desenhado pelo próprio Painel (o mesmo da janela)."""
    destino = os.path.join(PACOTE, 'app', 'painel', 'icone.ico')
    cod = (f"import sys; sys.path.insert(0, r'{FERRAMENTAS}');"
           "from PySide6.QtWidgets import QApplication; a = QApplication([]);"
           "from painel.app import icone_app;"
           f"icone_app().pixmap(256, 256).save(r'{destino}', 'ICO')")
    subprocess.run([sys.executable, '-c', cod], check=True, env=dict(os.environ, QT_QPA_PLATFORM='offscreen'))
    return destino


def atalho_portatil():
    with open(os.path.join(PACOTE, 'Mercado IA.cmd'), 'w', encoding='utf-8') as f:
        f.write('@echo off\r\ncd /d "%~dp0app"\r\nstart "" "%~dp0runtime\\pythonw.exe" -s -m painel\r\n')


def zip_portatil(v):
    destino = os.path.join(DIST, f'MercadoIA-portatil-{v}.zip')
    log('compactando a versão portátil...')
    with zipfile.ZipFile(destino, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for raiz, _, arqs in os.walk(PACOTE):
            for n in arqs:
                c = os.path.join(raiz, n)
                z.write(c, os.path.join('MercadoIA', os.path.relpath(c, PACOTE)))
    return destino


def zip_atualizacao(v):
    """MercadoIA-app-<versão>.zip: só o código (painel, cerebro, sider, docs, pesXdecrypter), para a atualização leve
    do Painel (painel/atualizar.py). Nada de dados: historico/, ia.json, automacao.json e config.json ficam de fora."""
    sys.path.insert(0, FERRAMENTAS)
    from painel import atualizar as A
    app = os.path.join(PACOTE, 'app')
    destino = os.path.join(DIST, f'MercadoIA-app-{v}.zip')
    with zipfile.ZipFile(destino, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for pasta in A.PASTAS_CODIGO:
            for raiz, _, arqs in os.walk(os.path.join(app, pasta)):
                for n in arqs:
                    c = os.path.join(raiz, n)
                    rel = os.path.relpath(c, app).replace(os.sep, '/')
                    if '__pycache__' in rel or A._protegido(rel):
                        continue
                    z.write(c, rel)
    return destino


def iscc():
    for c in (os.path.expandvars(r'%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe'), r'C:\Program Files (x86)\Inno Setup 6\ISCC.exe',
              r'C:\Program Files\Inno Setup 6\ISCC.exe'):
        if os.path.isfile(c):
            return c
    return shutil.which('iscc')


def instalador(v):
    exe = iscc()
    if not exe:
        log('Inno Setup 6 não encontrado: o instalador não foi gerado (a versão portátil está pronta).')
        log('Para gerar o instalador: winget install JRSoftware.InnoSetup  e rode este script de novo.')
        return None
    subprocess.run([exe, f'/DVersao={v}', f'/DPacote={PACOTE}', f'/O{DIST}', os.path.join(AQUI, 'MercadoIA.iss')], check=True)
    return os.path.join(DIST, f'MercadoIA-Setup-{v}.exe')


def tamanho(p):
    t = 0
    for raiz, _, arqs in os.walk(p):
        t += sum(os.path.getsize(os.path.join(raiz, n)) for n in arqs)
    return t / 1e6


def main():
    v = versao()
    log(f'Mercado IA {v} — Python {PY_VER} embutido, PySide6 {PYSIDE}')
    if os.path.isdir(PACOTE):
        shutil.rmtree(PACOTE)
    os.makedirs(PACOTE)
    runtime()
    copiar_app()
    pesxdecrypter()
    icone()
    atalho_portatil()
    log(f'pacote: {PACOTE} ({tamanho(PACOTE):.0f} MB)')
    z = zip_portatil(v)
    log(f'portátil: {z} ({os.path.getsize(z) / 1e6:.0f} MB)')
    za = zip_atualizacao(v)
    log(f'atualização leve: {za} ({os.path.getsize(za) / 1e6:.1f} MB)')
    s = instalador(v)
    if s:
        log(f'instalador: {s} ({os.path.getsize(s) / 1e6:.0f} MB)')


if __name__ == '__main__':
    main()
