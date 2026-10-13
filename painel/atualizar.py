# Mercado IA — autor: William (https://github.com/WilliamProgramadorBR)
"""ATUALIZAÇÃO AUTOMÁTICA (OTA) pelo GitHub Releases (13/10/2026). Sem Qt: dá para testar e chamar de qualquer lugar.

Como funciona (o mesmo raciocínio do electron-updater):
  1. o Painel pergunta à API do GitHub qual é o último release do repositório;
  2. o release traz o manifesto `atualizacao.json`:
       {"versao": "0.9.1", "data": "...", "notas": "...", "runtime": "3.14.3", "pyside": "6.12.0",
        "arquivos": {"MercadoIA-app-0.9.1.zip": "<sha256>", "MercadoIA-Setup-0.9.1.exe": "<sha256>"}}
  3. se a versão for maior que a instalada, o Painel oferece a atualização:
       LEVE      (o Python embutido e o Qt são os mesmos): baixa o zip do código (~2 MB), confere o SHA-256, guarda um
                 backup do código atual e troca painel/, cerebro/, sider/, docs/ e pesXdecrypter/ — sem tocar nos dados
                 (cerebro/historico, ia.json, automacao.json, config.json). Reinicia o Painel.
       COMPLETA  (mudou o Python ou o Qt): baixa o instalador, confere o SHA-256 e roda em modo silencioso; o instalador
                 também preserva os dados. Um .cmd espera o instalador terminar e abre o Painel de novo.
  4. se algo falhar no meio da leve, o backup volta sozinho.

No desenvolvimento (rodando da pasta Ferramentas, sem runtime\\) a atualização fica desligada: o código vem do git.
Para testar sem publicar: MERCADO_IA_ATUALIZACAO_URL=http://127.0.0.1:8000/atualizacao.json (manifesto local; os
arquivos são procurados na mesma pasta do manifesto).
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile

from painel import base

REPO = 'WilliamProgramadorBR/mercado-ia-pes2021'
API = f'https://api.github.com/repos/{REPO}/releases/latest'
UA = {'User-Agent': 'MercadoIA-Painel', 'Accept': 'application/vnd.github+json'}
PASTAS_CODIGO = ('painel', 'cerebro', 'sider', 'docs', 'pesXdecrypter')
NUNCA_TROCAR = ('.env', 'cerebro/historico/', 'cerebro/ia.json', 'cerebro/automacao.json', 'cerebro/mercado_config.json', 'config.json')
SEM_JANELA = 0x08000000


def empacotado():
    """True quando roda do pacote (runtime\\ ao lado de app\\)."""
    return os.path.isfile(os.path.join(base.TOOLS, '..', 'runtime', 'pythonw.exe'))


def tupla(v):
    out = []
    for p in str(v).lstrip('vV').split('.'):
        num = ''.join(ch for ch in p if ch.isdigit())
        out.append(int(num) if num else 0)
    return tuple(out + [0] * (3 - len(out)))


def _get(url, timeout=20):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout)


def pyside_versao():
    try:
        import PySide6
        return PySide6.__version__
    except Exception:  # noqa: BLE001
        return None


def verificar():
    """None se está em dia; senão {'versao', 'notas', 'tipo': 'leve'|'completa', 'urls': {nome: url}, 'sha': {nome: sha}}."""
    local = os.environ.get('MERCADO_IA_ATUALIZACAO_URL')
    if local:
        man = json.load(_get(local))
        pasta = local.rsplit('/', 1)[0]
        urls = {n: f'{pasta}/{n}' for n in man.get('arquivos', {})}
    else:
        rel = json.load(_get(API))
        ativos = {a['name']: a['browser_download_url'] for a in rel.get('assets') or []}
        if 'atualizacao.json' not in ativos:
            return None
        man = json.load(_get(ativos['atualizacao.json']))
        urls = {n: ativos[n] for n in man.get('arquivos', {}) if n in ativos}
    if tupla(man['versao']) <= tupla(base.VERSAO):
        return None
    mesmo_python = man.get('runtime') == '.'.join(map(str, sys.version_info[:3]))
    mesmo_qt = man.get('pyside') in (None, pyside_versao())
    zipn = next((n for n in urls if n.endswith('.zip') and '-app-' in n), None)
    setup = next((n for n in urls if n.endswith('.exe')), None)
    tipo = 'leve' if (mesmo_python and mesmo_qt and zipn) else 'completa'
    if tipo == 'completa' and not setup:
        return None
    return {'versao': man['versao'], 'notas': man.get('notas', ''), 'data': man.get('data'), 'tipo': tipo,
            'arquivo': zipn if tipo == 'leve' else setup, 'urls': urls, 'sha': man.get('arquivos', {})}


def baixar(info, progresso=None):
    """Baixa o arquivo da atualização e confere o SHA-256. Devolve o caminho local."""
    nome = info['arquivo']
    destino = os.path.join(tempfile.gettempdir(), 'MercadoIA_atualizacao', nome)
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    h = hashlib.sha256()
    with _get(info['urls'][nome], timeout=60) as r, open(destino + '.part', 'wb') as f:
        total = int(r.headers.get('Content-Length') or 0)
        feito = 0
        while True:
            b = r.read(1 << 16)
            if not b:
                break
            f.write(b)
            h.update(b)
            feito += len(b)
            if progresso:
                progresso(feito, total)
    if h.hexdigest() != (info['sha'].get(nome) or '').lower():
        os.remove(destino + '.part')
        raise RuntimeError('o arquivo baixado não confere com a impressão digital do release: atualização cancelada')
    os.replace(destino + '.part', destino)
    return destino


def _protegido(rel):
    rel = rel.replace('\\', '/')
    return any(rel == p or rel.startswith(p) for p in NUNCA_TROCAR)


def aplicar_leve(zip_path, log=print):
    """Troca o código do app pelo do zip, com backup; volta o backup se algo falhar. Devolve a pasta do backup."""
    app = base.TOOLS
    backup = os.path.join(app, '_backup', f'{base.VERSAO}_{time.strftime("%Y%m%d_%H%M%S")}')
    with zipfile.ZipFile(zip_path) as z:
        nomes = [n for n in z.namelist() if not n.endswith('/') and n.split('/')[0] in PASTAS_CODIGO and not _protegido(n)]
        if not any(n.startswith('painel/') for n in nomes):
            raise RuntimeError('o pacote de atualização não traz o Painel: atualização cancelada')
        for n in nomes:   # backup só do que vai ser trocado
            atual = os.path.join(app, n)
            if os.path.isfile(atual):
                os.makedirs(os.path.dirname(os.path.join(backup, n)), exist_ok=True)
                shutil.copy2(atual, os.path.join(backup, n))
        try:
            for n in nomes:
                destino = os.path.join(app, n)
                os.makedirs(os.path.dirname(destino), exist_ok=True)
                with z.open(n) as src, open(destino + '.novo', 'wb') as dst:
                    shutil.copyfileobj(src, dst)
                os.replace(destino + '.novo', destino)
        except Exception:
            log('falhou no meio: voltando o backup')
            restaurar(backup)
            raise
    for raiz, pastas, _ in os.walk(app):   # cache antigo do Python não confunde a versão nova
        for p in list(pastas):
            if p == '__pycache__':
                shutil.rmtree(os.path.join(raiz, p), ignore_errors=True)
                pastas.remove(p)
    return backup


def restaurar(backup):
    for raiz, _, arqs in os.walk(backup):
        for a in arqs:
            origem = os.path.join(raiz, a)
            destino = os.path.join(base.TOOLS, os.path.relpath(origem, backup))
            os.makedirs(os.path.dirname(destino), exist_ok=True)
            shutil.copy2(origem, destino)


def reiniciar_painel():
    """Abre um Painel novo daqui a 3 s (a cópia única deixa o atual sair antes)."""
    pyw = os.path.join(os.path.dirname(sys.executable), 'pythonw.exe')
    cmd = f'ping -n 4 127.0.0.1 >nul & start "" "{pyw}" -s -m painel'
    subprocess.Popen(['cmd', '/c', cmd], cwd=base.TOOLS, creationflags=SEM_JANELA)


def aplicar_completa(setup_path):
    """Roda o instalador em modo silencioso depois que o Painel fechar e abre o Painel de novo."""
    raiz = os.path.normpath(os.path.join(base.TOOLS, '..'))
    pyw = os.path.join(raiz, 'runtime', 'pythonw.exe')
    script = os.path.join(tempfile.gettempdir(), 'MercadoIA_atualizacao', 'atualizar.cmd')
    with open(script, 'w', encoding='utf-8') as f:
        f.write('@echo off\r\nping -n 4 127.0.0.1 >nul\r\n'
                f'"{setup_path}" /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /CLOSEAPPLICATIONS /DIR="{raiz}"\r\n'
                f'cd /d "{base.TOOLS}"\r\nstart "" "{pyw}" -s -m painel\r\n')
    subprocess.Popen(['cmd', '/c', script], creationflags=SEM_JANELA)


def limpar_backups(manter=3):
    pasta = os.path.join(base.TOOLS, '_backup')
    if os.path.isdir(pasta):
        for velho in sorted(os.listdir(pasta))[:-manter]:
            shutil.rmtree(os.path.join(pasta, velho), ignore_errors=True)
