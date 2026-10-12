"""Vigia do Mercado IA / Vestiário IA: roda em segundo plano junto com o jogo. Encerra sozinho quando o jogo fecha.

MODO AUTOMÁTICO (padrão; liga/desliga em cerebro/automacao.json):
  a cada save NOVO que o jogo grava (o automático depois das partidas), o vigia espera o arquivo estabilizar e roda:
    1. foto da memória (de fora do jogo, sem risco);
    2. Mercado IA (aplicar.py) — só dentro da janela de transferências e no máximo 1 vez a cada
       `mercado_intervalo_dias` dias do calendário do jogo;
    3. Vestiário IA (aplicar_vestiario.py) — moral, setas, notícias, pedidos, diretoria, mensagens, apelidos
       (ele mesmo só age quando há rodada nova).
  MODO HÍBRIDO (fase 4, chave "ao_vivo"): se o mercado não mexeu no save, o vestiário escreve setas, orçamento,
  mensagens e apelido direto na MEMÓRIA do jogo (o próprio jogo grava no próximo save) -> sem recarregar.
  Se algo foi gravado no SAVE (mercado), o overlay pede para CARREGAR a carreira.
LABORATÓRIO (10/10/2026): só as carreiras em "saves_automaticos" (padrão: ML00000000, a do Man Utd) são processadas.
  Saves de outras carreiras (ex.: liga de teste para estudar a demissão) são só COPIADOS, a cada gravação, para
  cerebro/historico/laboratorio/<arquivo>/<data_hora> — nada é alterado neles. Se o jogo salvar de novo enquanto processamos, nada é
  gravado (troca_save confere byte a byte) e o próximo save é processado.
MODO MANUAL (continua valendo): tecla 8 (mercado_pedido.txt) e tecla 9 (vestiario_pedido.txt) no overlay.
Comunicação com o overlay: mercado_status.txt (pasta do jogo). Erros: cerebro/historico/vigia_erros.txt.
"""
import datetime as dt
import glob
import json
import os
import subprocess
import sys
import time
import traceback

import janela
import memoria

HERE = os.path.dirname(os.path.abspath(__file__))
GAME_DIR = os.path.normpath(os.environ.get(
    'PES2021_GAME_DIR', os.path.join(HERE, '..', '..', 'eFootball PES 2021')))
REQUEST = os.path.join(GAME_DIR, 'mercado_pedido.txt')
REQUEST_VEST = os.path.join(GAME_DIR, 'vestiario_pedido.txt')   # tecla 9: vestiário (moral -> setas + notícias)
SNAP = os.path.join(GAME_DIR, 'mercado_snap.bin')
STATUS = os.path.join(GAME_DIR, 'mercado_status.txt')
CONFIG = os.path.join(HERE, 'automacao.json')
ESTADO_AUTO = os.path.join(HERE, 'historico', 'automacao_estado.json')
ERROS = os.path.join(HERE, 'historico', 'vigia_erros.txt')
PADRAO = {'automatico': True, 'mercado': True, 'vestiario': True, 'mercado_intervalo_dias': 7,
          'espera_segundos': 20, 'ao_vivo': True, 'saves_automaticos': '*'}
LAB = os.path.join(HERE, 'historico', 'laboratorio')   # cópias dos saves das carreiras de TESTE (sem processar)
SAVE_GLOBS = [
    os.path.expandvars(r'%USERPROFILE%\OneDrive\Documentos\KONAMI\eFootball PES 2021 SEASON UPDATE\*\save'),
    os.path.expandvars(r'%USERPROFILE%\OneDrive\Documents\KONAMI\eFootball PES 2021 SEASON UPDATE\*\save'),
    os.path.expandvars(r'%USERPROFILE%\Documents\KONAMI\eFootball PES 2021 SEASON UPDATE\*\save'),
]


VIVO = os.path.join(HERE, 'historico', 'vigia_vivo.txt')   # batimento: a Central avisa se o vigia parar


def sem_quickedit():
    """11/10/2026: um clique na janela do vigia liga a SELEÇÃO do console (QuickEdit) e o Windows congela o print até
    alguém apertar Esc -> o vigia ficou parado 50 min e a imprensa não saiu. Desliga a seleção nesta janela."""
    try:
        import ctypes
        k = ctypes.windll.kernel32
        h = k.GetStdHandle(-10)                       # STD_INPUT_HANDLE
        modo = ctypes.c_uint32()
        if k.GetConsoleMode(h, ctypes.byref(modo)):
            k.SetConsoleMode(h, (modo.value & ~0x40) | 0x80)   # sem ENABLE_QUICK_EDIT_MODE, com ENABLE_EXTENDED_FLAGS
    except Exception:  # noqa: BLE001 - sem console (pythonw) ou outro sistema: nada a fazer
        pass


def batimento():
    try:
        with open(VIVO, 'w', encoding='utf-8') as f:
            f.write(str(time.time()))
    except OSError:
        pass


def status(msg):
    with open(STATUS, 'w', encoding='utf-8') as f:
        f.write(msg + '\n')
    print(time.strftime('%H:%M:%S'), msg, flush=True)


def erro(contexto, texto=''):
    os.makedirs(os.path.dirname(ERROS), exist_ok=True)
    with open(ERROS, 'a', encoding='utf-8') as f:
        f.write(f'{time.strftime("%Y-%m-%d %H:%M:%S")} [{contexto}]\n{texto or traceback.format_exc()}\n')


def config():
    cfg = dict(PADRAO)
    try:
        with open(CONFIG, encoding='utf-8') as f:
            cfg.update(json.load(f))
    except (OSError, ValueError):
        with open(CONFIG, 'w', encoding='utf-8') as f:
            json.dump(PADRAO, f, ensure_ascii=False, indent=2)
    return cfg


def save_dirs():
    configured = os.environ.get('PES2021_SAVE_DIR')
    if configured:
        return [os.path.normpath(configured)] if os.path.isdir(configured) else []
    out = []
    for g in SAVE_GLOBS:
        out += glob.glob(g)
    return out


def ml_files():
    return [f for d in save_dirs() for f in glob.glob(os.path.join(d, 'ML0000000?'))]


def assinatura(path):
    try:
        return (os.path.getsize(path), os.path.getmtime(path))
    except OSError:
        return None


def game_running():
    r = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq PES2021.exe'], capture_output=True, text=True)
    return 'PES2021.exe' in r.stdout


def wait_stable(path, secs=3):
    last = None
    while True:
        cur = assinatura(path)
        if cur == last:
            return
        last = cur
        time.sleep(secs)


def tirar_foto():
    try:
        n, _ = memoria.foto(SNAP, log=lambda m: print(m, flush=True))
        return n
    except Exception:  # noqa: BLE001
        erro('foto da memória')
        return None


def rodar(script, ml, *extra):
    with subprocess.Popen([sys.executable, os.path.join(HERE, script), ml, SNAP, *extra], stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, text=True, cwd=HERE, encoding='utf-8', errors='replace') as p:
        while True:   # batimento durante a reunião (pode levar minutos): a Central não acusa vigia parado
            try:
                out, err = p.communicate(timeout=5)
                break
            except subprocess.TimeoutExpired:
                batimento()
    return subprocess.CompletedProcess(p.args, p.returncode, out, err)


# ---------------------------------------------------------------- modo automático
def _estado_auto():
    try:
        with open(ESTADO_AUTO, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _gravar_estado_auto(e):
    os.makedirs(os.path.dirname(ESTADO_AUTO), exist_ok=True)
    with open(ESTADO_AUTO, 'w', encoding='utf-8') as f:
        json.dump(e, f, ensure_ascii=False, indent=1)


def mercado_na_vez(cfg, ml, data_jogo):
    """Dentro da janela e com intervalo mínimo (dias do calendário do jogo) desde a última rodada automática."""
    if not cfg.get('mercado') or not data_jogo:
        return False
    _, tipo = janela.window_of(data_jogo)
    if tipo == 'fora':
        return False
    ult = _estado_auto().get('mercado', {}).get(os.path.basename(ml))
    if not ult:
        return True
    dias = (dt.date(*data_jogo) - dt.date(*ult)).days
    return dias >= cfg.get('mercado_intervalo_dias', 7) or dias < 0


def permitido(cfg, ml):
    lista = cfg.get('saves_automaticos', PADRAO['saves_automaticos'])
    return lista == '*' or '*' in lista or os.path.basename(ml) in lista


def guardar_laboratorio(ml):
    import troca_save
    wait_stable(ml)
    pasta = os.path.join(LAB, os.path.basename(ml))
    os.makedirs(pasta, exist_ok=True)
    destino = os.path.join(pasta, time.strftime('%Y%m%d_%H%M%S'))
    troca_save.copiar_compartilhado(ml, destino)
    n = len(os.listdir(pasta))
    # a Central mostra a carreira de teste também, em modo só leitura (nada é escrito no jogo)
    if tirar_foto() is not None:
        r = rodar('aplicar_vestiario.py', ml, '--so-central')
        if r.returncode != 0:
            erro('laboratório (Central)', r.stdout + r.stderr)
    status(f'Laboratório: save da carreira de teste guardado ({os.path.basename(ml)}, {n} cópia(s)). Nada foi alterado.')


def processar_automatico(cfg, ml):
    status('Novo save: atualizando o mundo (foto da memória, mercado, vestiário)...')
    wait_stable(ml)
    alterou, avisos = False, []
    n = tirar_foto()
    if n is None:
        avisos.append('foto da memória falhou (mercado pulado)')
    data_jogo = janela.career_date(SNAP) if n else None
    if n and mercado_na_vez(cfg, ml, data_jogo):
        status('Mercado IA: clubes negociando (1-3 minutos)...')
        r = rodar('aplicar.py', ml)
        if r.returncode == 0:
            e = _estado_auto()
            e.setdefault('mercado', {})[os.path.basename(ml)] = list(data_jogo)
            _gravar_estado_auto(e)
            alterou |= 'SAVE ATUALIZADO' in r.stdout
        elif 'SaveMudou' in r.stderr or 'o save mudou' in r.stderr:
            avisos.append('o jogo salvou de novo durante o mercado; tenta de novo no próximo save')
        else:
            erro('mercado automático', r.stdout + r.stderr)
            avisos.append('mercado com erro (save não alterado)')
    vivo = False
    if cfg.get('vestiario'):
        # modo híbrido (fase 4): se o mercado NÃO mexeu no save, a reunião escreve direto na memória do jogo.
        # Se mexeu, o jogador vai recarregar de qualquer jeito -> a reunião vai para o save junto (senão se perderia).
        ao_vivo = cfg.get('ao_vivo') and not alterou
        status('Vestiário: reunião automática' + (' ao vivo' if ao_vivo else '') + ' (1-2 minutos)...')
        r = rodar('aplicar_vestiario.py', ml, *(['--ao-vivo'] if ao_vivo else []))
        if r.returncode == 0:
            alterou |= 'SAVE ATUALIZADO' in r.stdout
            vivo = 'MEMÓRIA ATUALIZADA AO VIVO' in r.stdout
            if ao_vivo and 'aviso:' in r.stdout:
                erro('vestiário ao vivo (avisos)', '\n'.join(l for l in r.stdout.splitlines() if 'aviso:' in l))
        elif 'SaveMudou' in r.stderr or 'o save mudou' in r.stderr:
            avisos.append('o jogo salvou de novo durante a reunião; será refeita no próximo save')
        else:
            erro('vestiário automático', r.stdout + r.stderr)
            avisos.append('vestiário com erro (save não alterado)')
    extra = (' | ' + '; '.join(avisos)) if avisos else ''
    if alterou:
        status('PRONTO! Volte ao menu e CARREGUE a carreira (Continuar) para valer.' + extra)
    elif vivo:
        status('Vestiário atualizado AO VIVO: setas/mensagens já no jogo, não precisa recarregar.' + extra)
    else:
        status('Mundo atualizado: nada a recarregar.' + extra)
    return alterou


# ---------------------------------------------------------------- modo manual (teclas 8 e 9)
_fotos = {}


def garantir_foto(req):
    """Tira a foto da memória uma vez por pedido. False = falhou (pedido cancelado)."""
    t = os.path.getmtime(req)
    if _fotos.get(req) == t:
        return True
    status('Lendo os jogadores na memória do jogo...')
    n = tirar_foto()
    if n is None:
        status('ERRO ao ler a memória. Pedido cancelado; aperte a tecla de novo.')
        os.remove(req)
        return False
    _fotos[req] = t
    status(f'Foto tirada ({n} jogadores). Agora SALVE a carreira.')
    return True


def pedido_manual(req, script, rotulo):
    if not (os.path.exists(req) and garantir_foto(req)):
        return None
    t_req = os.path.getmtime(req)
    newer = [f for f in ml_files() if os.path.getmtime(f) > t_req + 1 and permitido(config(), f)]
    if not newer:
        return None
    ml = max(newer, key=os.path.getmtime)
    status(f'Save detectado. {rotulo} (pode levar 1-3 minutos)...')
    wait_stable(ml)
    os.remove(req)
    r = rodar(script, ml)
    if r.returncode == 0 and 'SAVE ATUALIZADO' in r.stdout:
        status('PRONTO! Volte ao menu e CARREGUE a carreira (sem salvar antes).')
    elif r.returncode == 0:
        status(f'{rotulo}: nada a gravar (não precisa recarregar).')
    else:
        erro(rotulo, r.stdout + r.stderr)
        status(f'ERRO ({rotulo}); save não alterado. Veja cerebro\\historico\\vigia_erros.txt.')
    return ml


def atrasado(ml):
    """O save é mais novo que a última reunião desta carreira (o vigia estava fechado ou travado quando o jogo salvou)."""
    painel = os.path.join(HERE, 'historico', f'central_{os.path.basename(ml)}.json')
    try:
        return os.path.getmtime(ml) > os.path.getmtime(painel) + 60
    except OSError:
        return False


def main():
    sem_quickedit()
    batimento()
    cfg = config()
    print('Vigia iniciado. Pastas de save:', save_dirs() or 'NENHUMA ENCONTRADA',
          '| modo automático:', 'LIGADO' if cfg['automatico'] else 'desligado', flush=True)
    if os.path.exists(STATUS):
        os.remove(STATUS)
    # saves que já existiam ao abrir não são processados (só o que o jogo gravar daqui para frente)
    vistos = {f: assinatura(f) for f in ml_files()}
    # ... exceto o save mais recente se ele ficou SEM reunião (vigia fechado/travado quando o jogo salvou): recupera
    recente = max(vistos, key=lambda f: (vistos[f] or (0, 0))[1], default=None)
    if recente and permitido(cfg, recente) and atrasado(recente):
        print('save sem reunião encontrado, recuperando:', os.path.basename(recente), flush=True)
        vistos.pop(recente)
    seen_game = False
    idle_since = time.time()
    if cfg['automatico']:
        status('Modo automático ligado: depois de cada jogo salvo, o mundo se atualiza sozinho.')
    while True:
        batimento()
        running = game_running()
        if running:
            seen_game, idle_since = True, time.time()
        elif seen_game or time.time() - idle_since > 600:
            print('jogo fechado: vigia encerrado', flush=True)
            return
        for req, script, rotulo in ((REQUEST, 'aplicar.py', 'Mercado'),
                                    (REQUEST_VEST, 'aplicar_vestiario.py', 'Vestiário')):
            ml = pedido_manual(req, script, rotulo)
            if ml:
                vistos[ml] = assinatura(ml)
        cfg = config()
        if cfg['automatico'] and running and not os.path.exists(REQUEST) and not os.path.exists(REQUEST_VEST):
            # só a carreira ABERTA no jogo: o save gravado por último. Os outros slots que mudaram (ex.: o jogador
            # passou por outra carreira) são só marcados como vistos (10/10/2026: o vigia ficava preso processando
            # um slot que não estava carregado, e a Central do slot atual ficava parada).
            mudados = [ml for ml in ml_files() if assinatura(ml) and assinatura(ml) != vistos.get(ml)]
            atual = max(mudados, key=lambda f: assinatura(f)[1]) if mudados else None
            for ml in mudados:
                if ml != atual:
                    vistos[ml] = assinatura(ml)
            for ml in [atual] if atual else []:
                sig = assinatura(ml)
                if sig and sig != vistos.get(ml) and time.time() - sig[1] >= cfg.get('espera_segundos', 20):
                    if not permitido(cfg, ml):
                        try:
                            guardar_laboratorio(ml)
                        except Exception:  # noqa: BLE001
                            erro('laboratório')
                        vistos[ml] = assinatura(ml)
                        continue
                    try:
                        processar_automatico(cfg, ml)
                    except Exception:  # noqa: BLE001 - o vigia nunca cai
                        erro('modo automático')
                        status('ERRO no modo automático (save não alterado). Veja cerebro\\historico\\vigia_erros.txt.')
                    vistos[ml] = assinatura(ml)   # inclui o que nós mesmos gravamos
        time.sleep(3)


if __name__ == '__main__':
    import unica
    unica.garantir('vigia')   # só uma cópia rodando (o .bat aberto duas vezes duplicava tudo)
    main()
