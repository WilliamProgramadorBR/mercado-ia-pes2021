# Mercado IA — autor: William (https://github.com/WilliamProgramadorBR)
"""PUBLICA UMA VERSÃO NO GITHUB RELEASES (13/10/2026) — a outra ponta da atualização automática do Painel.

  1. suba a versão em painel\\base.py (VERSAO = '0.9.1');
  2. escreva o que mudou em empacotar\\NOTAS.md (vai para o release e para a faixa "Nova versão" do Painel);
  3. python empacotar\\publicar.py            (monta o pacote, gera o manifesto e publica o release v0.9.1)
     python empacotar\\publicar.py --ensaio   (faz tudo menos publicar: confere arquivos e manifesto)

Arquivos do release: o instalador, a versão portátil, o zip leve do código e o atualizacao.json com as impressões
digitais (SHA-256) — o Painel só aplica o que conferir. Precisa do GitHub CLI (gh) logado na conta do repositório.
"""
import datetime as dt
import hashlib
import json
import os
import subprocess
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import montar  # noqa: E402

REPO = 'WilliamProgramadorBR/mercado-ia-pes2021'


def sha256(c):
    h = hashlib.sha256()
    with open(c, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def ultima_publicada():
    r = subprocess.run(['gh', 'release', 'view', '--repo', REPO, '--json', 'tagName', '-q', '.tagName'], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


def main():
    ensaio = '--ensaio' in sys.argv
    v = montar.versao()
    ult = ultima_publicada()
    sys.path.insert(0, montar.FERRAMENTAS)
    from painel import atualizar as A
    if ult and A.tupla(ult) >= A.tupla(v):
        raise SystemExit(f'a versão {v} não é maior que a última publicada ({ult}): suba VERSAO em painel\\base.py')
    notas_arq = os.path.join(AQUI, 'NOTAS.md')
    notas = open(notas_arq, encoding='utf-8').read().strip() if os.path.isfile(notas_arq) else f'Mercado IA {v}'
    if '--sem-montar' not in sys.argv:
        montar.main()
    arqs = [os.path.join(montar.DIST, n) for n in (f'MercadoIA-Setup-{v}.exe', f'MercadoIA-portatil-{v}.zip', f'MercadoIA-app-{v}.zip')]
    faltam = [a for a in arqs if not os.path.isfile(a)]
    if faltam:
        raise SystemExit(f'faltam arquivos (o Inno Setup está instalado?): {faltam}')
    import PySide6
    man = {'versao': v, 'data': dt.date.today().isoformat(), 'notas': notas,
           'runtime': montar.PY_VER, 'pyside': PySide6.__version__,
           'arquivos': {os.path.basename(a): sha256(a) for a in arqs}}
    manifesto = os.path.join(montar.DIST, 'atualizacao.json')
    with open(manifesto, 'w', encoding='utf-8') as f:
        json.dump(man, f, ensure_ascii=False, indent=2)
    for a in arqs:
        print(f'  {os.path.basename(a)}  {os.path.getsize(a) / 1e6:.1f} MB  {man["arquivos"][os.path.basename(a)][:16]}…')
    if ensaio:
        print(f'ENSAIO: manifesto em {manifesto}; nada foi publicado.')
        return
    subprocess.run(['gh', 'release', 'create', f'v{v}', *arqs, manifesto, '--repo', REPO, '--title', f'Mercado IA {v}',
                    '--notes', notas], check=True)
    print(f'publicado: https://github.com/{REPO}/releases/tag/v{v}')


if __name__ == '__main__':
    main()
