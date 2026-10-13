# Mercado IA — autor: William (https://github.com/WilliamProgramadorBR)
"""DIAGNÓSTICO DA INSTALAÇÃO (13/10/2026): o relatório que o testador manda quando algo não funciona.

Responde a pergunta "isto roda no meu PC?" em três camadas:
  ambiente  versões (Mercado IA, Python, Qt, PES2021.exe + impressão digital, Sider), patch e módulos do Sider;
  save      tabela de times, onde começam as seleções (regra nova x nome), time do usuário, plano tático, súmulas;
  memória   (com o jogo aberto numa carreira) os bytes do simulador que o técnico da IA corrige, a tabela de fichas
            dos jogadores e os blocos táticos dos clubes — os três pontos que dependem da versão do executável.
Grava em <ferramenta>\\diagnostico\\diagnostico_<data>.txt. Nada é escrito no jogo nem no save (só leitura).
"""
import datetime as dt
import glob
import hashlib
import os
import platform
import re
import struct
import sys
import tempfile
import time

from painel import base, verificar

OK, AVISO, ERRO = '✔', '!', '✖'


def _sha(caminho):
    h = hashlib.sha256()
    with open(caminho, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def _save_mais_novo():
    decs = glob.glob(os.path.join(base.TOOLS, 'save_work', 'vestiario_*', 'dec', 'data.dat'))
    return max(decs, key=os.path.getmtime) if decs else None


def rodar(log=print):
    import caminhos
    linhas, resumo = [], []

    def item(estado, titulo, detalhe=''):
        linhas.append(f'  {estado} {titulo}' + (f': {detalhe}' if detalhe else ''))
        if estado != OK:
            resumo.append(f'{estado} {titulo}' + (f' — {detalhe}' if detalhe else ''))

    jogo = caminhos.config().get('jogo') or caminhos.GAME_DIR
    linhas.append(f'Mercado IA {base.VERSAO} · diagnóstico de {dt.datetime.now():%d/%m/%Y %H:%M}')
    linhas.append(f'Windows {platform.version()} · Python {platform.python_version()} · PySide6 '
                  + (__import__('PySide6').__version__ if 'PySide6' in sys.modules or True else '?'))
    # ---------------------------------------------------------------- ambiente
    linhas.append('\n[AMBIENTE]')
    exe = os.path.join(jogo, 'PES2021.exe')
    if os.path.isfile(exe):
        ver = verificar.versao_arquivo(exe)
        item(OK if ver == verificar.EXE_VALIDADO else AVISO, 'PES2021.exe', f'versão {ver} · {os.path.getsize(exe):,} bytes'.replace(',', '.'))
        linhas.append(f'      sha256 {_sha(exe)}')
    else:
        item(ERRO, 'PES2021.exe', f'não encontrado em {jogo}')
    dll = os.path.join(jogo, 'sider.dll')
    item(OK if os.path.isfile(dll) else ERRO, 'Sider', f'versão {verificar.versao_arquivo(dll)}' if os.path.isfile(dll) else 'sider.dll não encontrado')
    txt = verificar.ler_sider(jogo) or ''
    mods = re.findall(r'^\s*lua\.module\s*=\s*"([^"]+)"', txt, flags=re.M)
    linhas.append(f'      módulos do Sider ({len(mods)}): ' + ', '.join(mods[:30]))
    item(OK if 'MercadoIA.lua' in mods else ERRO, 'MercadoIA.lua no sider.ini')
    patch = [n for n in os.listdir(jogo) if n.upper() in ('GOGOSZ', 'PES UNIVERSE', 'EVOWEB', 'SMOKEPATCH', 'SMOKE PATCH', 'PTE', 'EFOOTBALL PATCH')] if os.path.isdir(jogo) else []
    linhas.append(f'      patch (pastas reconhecidas): {", ".join(patch) or "não identificado"}')
    # ---------------------------------------------------------------- save
    linhas.append('\n[SAVE]')
    dec = _save_mais_novo()
    d = s = None
    if not dec:
        item(AVISO, 'Save descriptografado', 'ainda não há reunião: jogue e salve uma vez com o vigia ligado')
    else:
        from save_ml import SaveML
        d = open(dec, 'rb').read()
        linhas.append(f'      cópia da última reunião: {dec} ({dt.datetime.fromtimestamp(os.path.getmtime(dec)):%d/%m %H:%M})')
        try:
            s = SaveML.__new__(SaveML)
            s.path, s.d, s.base = None, bytearray(d), d.index(b'ARSENAL' + bytes([0]))
            n = 0
            while n < 900 and s.name(n):
                n += 1
            item(OK, 'Tabela de times', f'{n} times')
        except ValueError:
            item(ERRO, 'Tabela de times', 'o time ARSENAL não foi achado: banco de dados muito diferente do esperado')
            s = None
        if s is not None:
            import selecoes
            p = selecoes.primeira(s)
            pelo_nome = next((x for x in (s.find_team(nm) for nm in selecoes.NOMES) if x is not None), None)
            item(OK if p is not None else ERRO, 'Começo das seleções', f'time {p} ({s.name(p).strip() if p is not None else "?"}) · pelo nome: {pelo_nome}')
            try:
                import carreira
                ti, nome = carreira.time_do_usuario(d)
                item(OK if ti is not None else ERRO, 'Seu time na carreira', f'{nome} (índice {ti})')
            except Exception as e:  # noqa: BLE001
                item(ERRO, 'Seu time na carreira', str(e))
            try:
                import tatica_save as T
                o = T.bloco_usuario(d)
                item(OK if o is not None else AVISO, 'Plano tático do seu time', f'bloco em 0x{o:X}' if o is not None else 'não achado (a IA adversária fica sem olheiro)')
            except Exception as e:  # noqa: BLE001
                item(AVISO, 'Plano tático do seu time', str(e))
            try:
                import partidas_save as ps
                todas, ag = ps.todas(d, *ps.FAIXA), ps.agenda(d)
                item(OK if todas else AVISO, 'Súmulas e calendário', f'{len(todas)} partidas jogadas · {len(ag)} agendadas')
            except Exception as e:  # noqa: BLE001
                item(ERRO, 'Súmulas e calendário', str(e))
    # ---------------------------------------------------------------- memória (jogo aberto)
    linhas.append('\n[MEMÓRIA DO JOGO]')
    import memoria as M
    pid = M.pid_do_jogo()
    if not pid:
        item(AVISO, 'Jogo aberto', 'abra o PES numa carreira e rode o diagnóstico de novo para testar a memória')
    else:
        h = M.k32.OpenProcess(M.PROCESS_QUERY_INFORMATION | M.PROCESS_VM_READ, False, pid)
        try:
            import escalacao_ia as EI
            b = M.ler(h, EI.ALVO, len(EI.ORIGINAL)) if h else None
            if b == EI.ORIGINAL:
                item(OK, 'Simulador (técnico da IA)', 'bytes originais encontrados no endereço esperado (patch ainda não aplicado nesta sessão)')
            elif b and b[:6] == EI.ORIGINAL[:6] and b[7:] == EI.ORIGINAL[7:] and b[6] == 1:
                item(OK, 'Simulador (técnico da IA)', 'patch ativo (modo 1)')
            else:
                item(ERRO, 'Simulador (técnico da IA)', f'bytes diferentes ({b.hex() if b else "ilegível"}): executável diferente; o técnico da IA não vai escrever nada (seguro)')
            t0 = time.time()
            tmp = os.path.join(tempfile.gettempdir(), 'MercadoIA_diag_snap.bin')
            try:
                nf, addr = M.foto(tmp, log=lambda *a: None)
                item(OK if nf >= 15000 else AVISO, 'Tabela de jogadores', f'{nf} fichas em 0x{addr:X} ({time.time() - t0:.0f} s)')
            except Exception as e:  # noqa: BLE001
                item(ERRO, 'Tabela de jogadores', str(e))
            finally:
                try:
                    os.remove(tmp)
                except OSError:
                    pass
            if d is not None:
                t0 = time.time()
                try:
                    import ia_adversaria as IA
                    e = IA._ler_estado()
                    b0 = IA._base_memoria(h, d, e, lambda *a: None)
                    item(OK if b0 else ERRO, 'Blocos táticos dos clubes', f'em 0x{b0:X} ({time.time() - t0:.0f} s)' if b0 else 'não achados: a IA adversária não consegue escrever planos')
                except Exception as ex:  # noqa: BLE001
                    item(ERRO, 'Blocos táticos dos clubes', str(ex))
        finally:
            if h:
                M.k32.CloseHandle(h)
    # ---------------------------------------------------------------- veredito
    linhas.append('\n[RESUMO]')
    linhas += ['  ' + r for r in resumo] or ['  ✔ tudo certo: esta instalação roda o Mercado IA completo']
    texto = '\n'.join(linhas)
    pasta = os.path.join(base.TOOLS, 'diagnostico')
    os.makedirs(pasta, exist_ok=True)
    arq = os.path.join(pasta, f'diagnostico_{dt.datetime.now():%Y%m%d_%H%M%S}.txt')
    with open(arq, 'w', encoding='utf-8') as f:
        f.write(texto + '\n')
    return texto, arq
