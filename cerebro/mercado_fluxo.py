# Mercado IA — autor: William (https://github.com/WilliamProgramadorBR)
"""FLUXO DO MERCADO (19/10/2026): o que a IA de transferências está fazendo, para a tela "Mercado IA" do Painel.

Pedido do usuário: "quero ver o fluxo dela funcionando, e alertar quando for necessário fechar a liga e voltar para o
save; quero ver os relatórios e as movimentações". Peças:
  eventos        historico/mercado_fluxo.jsonl — uma linha por etapa do vigia (save novo, foto, mercado na/fora da
                 janela, esperando o intervalo, negócios gravados, vestiário, resultado), com hora e nível;
  rodadas        historico/mercado_rodadas.json — cada rodada que gravou negócios no save, com os jogadores
                 (registro/id, clube de origem e destino) para a conferência abaixo;
  recarga        historico/recarga_pendente.json — existe enquanto o save tem mudanças que o jogo ainda não carregou
                 (o jogo só enxerga as transferências depois de voltar ao menu e carregar a carreira; se ele salvar
                 antes, grava por cima). O Painel avisa (faixa vermelha + bandeja) até ela sumir;
  conferência    no save seguinte, ANTES de qualquer coisa, o vigia confere se os jogadores da última rodada estão nos
                 clubes novos: sim = recarregou certo (alerta some); não = o jogo gravou por cima — os negócios são
                 devolvidos ao limite da janela e o mercado roda de novo nesse mesmo save.
Só leitura do jogo; o que muda são arquivos do próprio Mercado IA.
"""
import datetime as dt
import glob
import json
import os
import time

HERE = os.path.dirname(os.path.abspath(__file__))
HIST = os.path.join(HERE, 'historico')
ARQ_EVENTOS = os.path.join(HIST, 'mercado_fluxo.jsonl')
ARQ_RODADAS = os.path.join(HIST, 'mercado_rodadas.json')
ARQ_RECARGA = os.path.join(HIST, 'recarga_pendente.json')
MAX_EVENTOS = 400


def _ler(arq, padrao):
    try:
        with open(arq, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return padrao


def _gravar(arq, dados):
    os.makedirs(HIST, exist_ok=True)
    tmp = arq + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(dados, f, ensure_ascii=False, indent=1)
    for _ in range(40):   # no Windows, outro processo lendo o arquivo impede a troca por um instante
        try:
            os.replace(tmp, arq)
            return
        except PermissionError:
            time.sleep(0.05)
    with open(arq, 'w', encoding='utf-8') as f:
        json.dump(dados, f, ensure_ascii=False, indent=1)


# ---------------------------------------------------------------- eventos
def evento(etapa, texto, nivel='info', **extra):
    """nivel: info | ok | aviso | erro | recarga."""
    try:
        os.makedirs(HIST, exist_ok=True)
        with open(ARQ_EVENTOS, 'a', encoding='utf-8') as f:
            f.write(json.dumps({'quando': time.strftime('%Y-%m-%d %H:%M:%S'), 'etapa': etapa, 'nivel': nivel,
                                'texto': texto, **extra}, ensure_ascii=False) + '\n')
        if os.path.getsize(ARQ_EVENTOS) > 400_000:   # guarda só o fim
            linhas = open(ARQ_EVENTOS, encoding='utf-8').read().splitlines()[-MAX_EVENTOS:]
            with open(ARQ_EVENTOS, 'w', encoding='utf-8') as f:
                f.write('\n'.join(linhas) + '\n')
    except OSError:
        pass


def eventos(n=80):
    try:
        linhas = open(ARQ_EVENTOS, encoding='utf-8').read().splitlines()[-n:]
    except OSError:
        return []
    out = []
    for l in reversed(linhas):
        try:
            out.append(json.loads(l))
        except ValueError:
            pass
    return out


# ---------------------------------------------------------------- rodadas (aplicar.py)
def registrar_rodada(r):
    """r = {stamp, save, data_jogo, janela, uso, limite, negocios: [{jogador, reg, pid, de, para, src, dst, valor, ...}]}"""
    rs = _ler(ARQ_RODADAS, [])
    rs.append(r)
    _gravar(ARQ_RODADAS, rs[-120:])


def rodadas():
    """Rodadas com negócios: as registradas aqui + as antigas (janela_*.csv, antes desta tela existir)."""
    rs = [dict(x, fonte='fluxo') for x in _ler(ARQ_RODADAS, [])]
    vistos = {x.get('stamp') for x in rs}
    import csv
    for arq in glob.glob(os.path.join(HIST, 'janela_*.csv')):
        stamp = os.path.basename(arq)[len('janela_'):-len('.csv')]
        if stamp in vistos:
            continue
        try:
            with open(arq, encoding='utf-8-sig') as f:
                linhas = list(csv.DictReader(f, delimiter=';'))
        except OSError:
            continue
        if not linhas:
            continue
        rs.append({'stamp': stamp, 'fonte': 'csv', 'negocios': [
            {'jogador': x.get('jogador'), 'idade': x.get('idade'), 'pos': x.get('posição'), 'estilo': x.get('estilo'),
             'nota': x.get('nota_estimada'), 'de': x.get('de'), 'para': x.get('para'), 'valor': x.get('valor_milhoes'),
             'motivo': x.get('motivo'), 'perfil': x.get('perfil_comprador')} for x in linhas]})
    return sorted(rs, key=lambda x: x.get('stamp') or '', reverse=True)


# ---------------------------------------------------------------- recarga
def marcar_recarga(save, motivo, n_negocios=0, stamp=None, data_jogo=None):
    _gravar(ARQ_RECARGA, {'save': os.path.basename(save), 'motivo': motivo, 'negocios': n_negocios, 'stamp': stamp,
                          'data_jogo': list(data_jogo) if data_jogo else None, 'quando': time.strftime('%Y-%m-%d %H:%M:%S'),
                          'ts': time.time()})
    evento('recarga', f'Volte ao menu e CARREGUE a carreira ({motivo}).', 'recarga', save=os.path.basename(save))


def recarga():
    return _ler(ARQ_RECARGA, None)


def limpar_recarga(motivo, nivel='ok'):
    if os.path.exists(ARQ_RECARGA):
        try:
            os.remove(ARQ_RECARGA)
        except OSError:
            return
        evento('recarga', motivo, nivel)


def conferir(ml_path, decriptar, log=print):
    """Chamado pelo vigia ANTES de processar um save novo. Se havia recarga pendente deste save, confere se os
    jogadores da última rodada estão nos clubes novos. decriptar(ml) -> bytes do data.dat. Devolve 'ok', 'perdida' ou
    None (nada a conferir)."""
    rc = recarga()
    if not rc or rc.get('save') != os.path.basename(ml_path):
        return None
    rod = next((x for x in reversed(_ler(ARQ_RODADAS, [])) if x.get('stamp') == rc.get('stamp')), None)
    if not rod or not rod.get('negocios'):
        limpar_recarga('Save novo depois da atualização: considerando a carreira recarregada.', 'ok')
        return 'ok'
    from save_ml import SaveML
    d = decriptar(ml_path)
    s = SaveML.__new__(SaveML)
    s.path, s.d, s.base = None, bytearray(d), d.index(b'ARSENAL' + bytes(1))
    no_destino = no_origem = 0
    for m in rod['negocios']:
        k = (m['reg'], m['pid'])
        if m.get('dst') is not None and k in {tuple(x) for x in s.squad(m['dst'])}:
            no_destino += 1
        elif m.get('src') is not None and m['src'] >= 0 and k in {tuple(x) for x in s.squad(m['src'])}:
            no_origem += 1
    n = len(rod['negocios'])
    if no_destino >= max(1, n // 2):
        limpar_recarga(f'Carreira recarregada certinho: {no_destino} de {n} transferências confirmadas no save.', 'ok')
        return 'ok'
    if no_origem >= max(1, n // 2):
        _devolver(rod, log)
        limpar_recarga(f'O jogo salvou ANTES de recarregar a carreira: as {n} transferências da rodada se perderam. '
                       'Elas voltaram para o limite da janela e o mercado roda de novo agora.', 'erro')
        return 'perdida'
    limpar_recarga(f'Conferência inconclusiva ({no_destino} no destino, {no_origem} na origem, de {n}).', 'aviso')
    return None


def _devolver(rod, log):
    """Tira do controle da janela os negócios que não ficaram no save e libera o mercado para rodar de novo."""
    import janela
    try:
        led = janela.load()
        e = led.get(rod.get('carreira') or '', {}).get(rod.get('janela') or '')
        if e:
            for m in rod['negocios']:
                e['total'] = max(0, e['total'] - 1)
                for lado, clube in (('chegadas', m['para']), ('saidas', m['de'])):
                    if e[lado].get(clube):
                        e[lado][clube] -= 1
                        if not e[lado][clube]:
                            e[lado].pop(clube)
            e['rodadas'] = max(0, e['rodadas'] - 1)
            janela.save(led)
        auto = _ler(os.path.join(HIST, 'automacao_estado.json'), {})
        (auto.get('mercado') or {}).pop(rod.get('save'), None)
        _gravar(os.path.join(HIST, 'automacao_estado.json'), auto)
        try:   # a imprensa não pode noticiar negócio que não aconteceu
            import imprensa_db
            with imprensa_db.conectar() as c:
                for m in rod['negocios']:
                    c.execute('DELETE FROM negocios WHERE carreira = ? AND jogador = ? AND para = ? AND materia_id IS NULL',
                              (rod.get('carreira'), m['jogador'], m['para']))
        except Exception as ex:  # noqa: BLE001
            log(f'aviso: negócios perdidos ainda na fila da imprensa: {ex}')
    except Exception as ex:  # noqa: BLE001
        log(f'aviso: não consegui devolver os negócios perdidos ao limite da janela: {ex}')


# ---------------------------------------------------------------- resumo para o Painel
def _proxima_janela(data):
    y, m, _ = data
    if 3 <= m <= 5:
        return (y, 6, 1), 'verão'
    if 10 <= m <= 11:
        return (y, 12, 1), 'inverno'
    return None, None


def estado():
    import caminhos
    import janela
    cfg = _ler(os.path.join(HERE, 'automacao.json'), {})
    mcfg = _ler(os.path.join(HERE, 'mercado_config.json'), {})
    saves = glob.glob(os.path.join(HIST, 'central_ML*.json'))
    central = max(saves, key=os.path.getmtime) if saves else None
    cd = _ler(central, {}) if central else {}
    slot = os.path.basename(central)[len('central_'):-len('.json')] if central else None
    pulso = _ler(os.path.join(HIST, f'pulso_{slot}.json'), {}) if slot else {}
    data = tuple(pulso.get('data_jogo') or cd.get('data_jogo') or ()) or None
    out = {'slot': slot, 'time': cd.get('time'), 'data_jogo': list(data) if data else None,
           'automatico': cfg.get('automatico', True), 'ligado': cfg.get('mercado', True),
           'intervalo': cfg.get('mercado_intervalo_dias', 7), 'recarga': recarga(), 'eventos': eventos(),
           'rodadas': rodadas()}
    if data:
        chave, tipo = janela.window_of(data)
        out['janela'] = {'chave': chave, 'tipo': tipo}
        if tipo != 'fora':
            lim = mcfg.get(f'limite_janela_{tipo}', 40 if tipo == 'verao' else 20)
            ent = (janela.load().get(f'{slot}|{cd.get("time")}') or {}).get(chave) or {}
            out['janela'].update(limite=lim, total=ent.get('total', 0), rodadas=ent.get('rodadas', 0))
        else:
            prox, nome = _proxima_janela(data)
            out['janela'].update(proxima=list(prox) if prox else None, proxima_nome=nome)
        ult = (_ler(os.path.join(HIST, 'automacao_estado.json'), {}).get('mercado') or {}).get(slot)
        out['ultima'] = ult
        if ult:
            out['proxima_rodada'] = list((dt.date(*ult) + dt.timedelta(days=out['intervalo'])).timetuple()[:3])
    try:
        out['vigia_seg'] = time.time() - os.path.getmtime(os.path.join(HIST, 'vigia_vivo.txt'))
    except OSError:
        out['vigia_seg'] = None
    try:
        arq = os.path.join(caminhos.GAME_DIR, 'mercado_status.txt')
        out['status'] = {'texto': open(arq, encoding='utf-8').read().strip(), 'quando': os.path.getmtime(arq)}
    except OSError:
        out['status'] = None
    try:
        import imprensa_db
        with imprensa_db.conectar() as c:
            out['negocios'] = [dict(r) for r in c.execute(
                'SELECT data, janela, jogador, idade, pos, estilo, nota, de, para, valor, motivo, perfil FROM negocios '
                'WHERE carreira = ? ORDER BY id DESC LIMIT 600', (f'{slot}|{cd.get("time")}',))]
    except Exception:  # noqa: BLE001
        out['negocios'] = []
    return out
