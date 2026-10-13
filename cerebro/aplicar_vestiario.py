# Mercado IA — autor: William (https://github.com/WilliamProgramadorBR)
"""Aplica o Vestiário IA num save da Master League: moral -> seta de condição + notícias na mídia.

Uso:  python aplicar_vestiario.py <arquivo ML0000000X> [foto_memoria.bin] [--ensaio]
  --ensaio: calcula tudo e escreve as notícias/relatório, mas NÃO substitui o save nem a memória do vestiário.
  --ao-vivo: (fase 4, modo híbrido do vigia) em vez de regravar o save, escreve setas, orçamento, mensagem e
             apelido direto na MEMÓRIA do jogo aberto (ao_vivo.py) — não precisa recarregar a carreira.

Ciclo (igual ao Mercado IA): salvar -> aplicar -> CARREGAR a carreira.
  1. backup + descriptografa uma cópia
  2. efeitos guardados (polêmicas na mídia ainda "quentes") entram na moral
  3. vestiario.analisar() -> moral, conflitos
  4. notícias: conflitos NOVOS viram matéria (no máximo 4 por rodada); quem sai na mídia perde moral por 3 rodadas
  5. seta de condição de cada jogador do usuário = seta do jogo ajustada pela moral (só 1 vez por rodada)
  6. regrava o bloco comprimido -> criptografa -> confere ida e volta -> substitui o save
Memória do vestiário: historico/vestiario_estado.json (só é gravada depois que o save foi substituído).
"""
import datetime as dt
import json
import os
import random
import shutil
import struct
import subprocess
import sys
import textwrap

import acoes
import apelidos
import calendario
import clube
import compromissos
import crises
import dificuldade
import disciplina
import exigencias
import humor
import patrocinio
import central_dados
import midia
import midia_liga
import proximo_jogo
import financas_save
import mensagens_save
import troca_save
import dados
import decisoes as D
import diretoria
import diretoria_nativa
from save_ml import SaveML
import jogadores_save as js
import vestiario as V

import caminhos

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = caminhos.TOOLS                      # 12/10/2026: caminhos.py (config.json do Painel)
DECRYPT = caminhos.DECRYPT
ENCRYPT = caminhos.ENCRYPT
ESTADO = os.environ.get('VESTIARIO_ESTADO') or os.path.join(HERE, 'historico', 'vestiario_estado.json')
NEWS_FILE = os.path.join(V.GAME_DIR, 'vestiario_noticias.txt')
DECISAO_FILE = os.path.join(V.GAME_DIR, 'vestiario_decisao.txt')     # pedido pendente (mostrado no overlay)
RESPOSTA_FILE = os.path.join(V.GAME_DIR, 'vestiario_resposta.txt')   # 1/2/3 gravado pelo overlay
BACKUPS = os.path.join(TOOLS, 'Backups', 'vestiario')

RODADAS_POLEMICA = 3      # quantas rodadas a matéria pesa na moral
PESO_POLEMICA = -6        # moral dos envolvidos numa matéria negativa
PESO_CLIMA = -2           # todo o elenco, se a rodada tiver 2+ matérias negativas
PESO_ELOGIO = 3
MAX_NOTICIAS = 4
APELIDOS_TORCIDA = True    # a torcida batiza ídolos sem apelido (1 por mês do jogo, sistema nativo de apelidos)
MENSAGENS_NATIVAS = True   # coloca mensagens nativas na caixa do jogo (ex.: "Evolução de X")
MEXER_ORCAMENTO = True     # diretoria pode dar prêmio/corte no orçamento de transferências (etapa 3b)
TETO_POLEMICA = -12      # soma máxima das polêmicas na moral de um jogador


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f'falhou: {cmd} -> {r.stderr or r.stdout}')


def chave(k):
    return f'{k[0]}:{k[1]}'


def carregar_estado():
    try:
        with open(ESTADO, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return {'carreiras': {}}


def gravar_estado(e):
    os.makedirs(os.path.dirname(ESTADO), exist_ok=True)
    tmp = ESTADO + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(e, f, ensure_ascii=False, indent=1)
    # 11/10/2026: no Windows, se a Central (ou outro programa) estiver lendo o arquivo naquele instante, a troca falha
    # com WinError 32 e a reunião inteira se perdia. Tenta de novo por até ~10 s.
    import time
    for i in range(40):
        try:
            os.replace(tmp, ESTADO)
            return
        except PermissionError:
            if i == 39:
                raise
            time.sleep(0.25)


def escolher_evolucao(car, J, hoje):
    """Promessa (até 23 anos, nota >= 75) com menos de 25% dos minutos nos últimos 4+ jogos; o mesmo jogador
    só de novo depois de 45 dias; no máximo 1 por reunião."""
    feitos = {m['jogador'] for m in car.get('msgs_nativas', [])
              if m['tipo'] == 81 and V.dias(tuple(hoje), tuple(m['data'])) < 45}
    cands = [j for j in J if j['idade'] <= 23 and j['ovr'] >= 75 and j['r_jogos_time'] >= 4
             and j['r_min'] < 0.25 * 90 * j['r_jogos_time'] and chave(j['k']) not in feitos]
    if not cands:
        return None
    j = max(cands, key=lambda j: (j['ovr'], -j['idade']))
    return {'jogador': chave(j['k']), 'k': list(j['k']), 'nome': j['nome']}


def efeitos(car):
    """Histórias ainda ativas -> {(reg, id): [(delta, motivo)]}; polêmicas somam no máximo TETO_POLEMICA."""
    extra = {}
    for h in car['historias'].values():
        if h.get('restam', 0) > 0:
            for kk in h['envolvidos']:
                reg, pid = map(int, kk.split(':'))
                extra.setdefault((reg, pid), []).append((h['peso'], h['motivo']))
    for k, lst in extra.items():
        neg = sum(dm for dm, m in lst if dm < 0 and m.startswith('polêmica'))
        if neg < TETO_POLEMICA:
            fator = TETO_POLEMICA / neg
            extra[k] = [(round(dm * fator) if dm < 0 and m.startswith('polêmica') else dm, m) for dm, m in lst]
    return extra


def materia(tipo, env, r, rnd):
    """Texto de jornal para um conflito. env = jogadores envolvidos (dicts do vestiario)."""
    a = env[0]
    if tipo == 'Braçadeira':
        cap = env[1]
        return rnd.choice([
            f'BASTIDORES: {a["nome"]} não engoliu a perda da braçadeira para {cap["nome"]}. Pessoas próximas dizem '
            f'que, depois de {a["anos"]:.0f} anos de clube, ele se sente desrespeitado.',
            f'CLIMA TENSO: a escolha de {cap["nome"]} como capitão dividiu o vestiário. {a["nome"]}, '
            f'{a["status"].lower()} do clube, evitou comentar e deixou o treino calado.',
        ])
    if tipo == 'Posição':
        b = env[1]
        pct = a['r_min'] / max(1, 90 * a['r_jogos_time'])
        return rnd.choice([
            f'{a["nome"]} perde espaço para {b["nome"]} e já não esconde a irritação: só {pct:.0%} dos minutos '
            f'nos últimos {a["r_jogos_time"]} jogos.',
            f'Imprensa questiona: {a["nome"]} virou reserva de luxo? O {a["status"].lower()} jogou {pct:.0%} '
            f'dos minutos recentes enquanto {b["nome"]} se firmou.',
        ])
    if tipo == 'Ego salarial':
        o, vit = env[0], env[1:]
        nomes = ', '.join(v['nome'] for v in vit[:3])
        return (f'VAZOU: {o["nome"]} recebe R$ {o["salario"] * V.SALARIO_X / 1e6:.1f} mi por ano. No vestiário, '
                f'{nomes} questionam por que ganham menos tendo mais futebol.')
    if tipo == 'Insatisfeito':
        motivo = a['motivos'][0] if a['motivos'] else 'situação no clube'
        return rnd.choice([
            f'{a["nome"]} insatisfeito no {clube.C["curto"]}. Motivo, segundo a imprensa: {motivo}.',
            f'Empresário de {a["nome"]} admite conversa com a diretoria: "{motivo}".',
        ])
    return f'{tipo}: ' + ', '.join(x['nome'] for x in env)


def elogio(j, rnd):
    return rnd.choice([
        f'EM ALTA: {j["nome"]} vive grande fase — {j["t_gols"]} gols e {j["t_assist"]} assistências na temporada. '
        f'A torcida já canta o nome dele.',
        f'{j["nome"]} é o nome do momento {clube.C["em_estadio"]}: nota média {j["r_nota"]:.1f} nos últimos jogos.',
    ])


def gravar_ao_vivo(r, d, mudancas, aj, msg_nativa, apelido_novo, car, dire, hoje, out_rel):
    """Fase 4 (modo híbrido): tudo o que a reunião decidiu vai direto para a MEMÓRIA do jogo aberto (ao_vivo.py);
    o save não é tocado — o próprio jogo grava no próximo salvamento. Cada parte é independente: se uma falhar,
    as outras continuam, e o que falhou fica para a próxima reunião (setas e apelido se autocorrigem pelo save).
    True = escreveu alguma coisa."""
    import ao_vivo
    escreveu = False
    # setas: só as que realmente mudam (mudancas também pode ter só o apelido)
    alvos = {k: js.campos(rec)['seta'] for k, rec in mudancas.items()
             if js.campos(rec)['seta'] != js.campos(r['regs'][k])['seta']}
    if alvos:
        try:
            feito = ao_vivo.setas(alvos, r['regs'], escrever_de_verdade=True,
                                  esperado={k: js.campos(r['regs'][k])['seta'] for k in alvos})
            escreveu |= bool(feito)
            print(f'AO VIVO: {len(feito)}/{len(alvos)} seta(s) escritas na memória')
        except Exception as e:  # noqa: BLE001
            print('aviso: setas ao vivo não escritas:', e)
    if aj:
        try:
            antes, novo = ao_vivo.orcamento(None, aj['antes'], escrever_de_verdade=True, delta_reais=aj['delta'])
            escreveu = True
            dire.setdefault('orcamento_hist', []).append({**aj, 'antes': antes, 'depois': novo})
            dire['orcamento_hist'] = dire['orcamento_hist'][-24:]
            dire['orcamento_atual'] = novo
            rel_orc = f'ORÇAMENTO (ao vivo): R$ {antes:,} -> R$ {novo:,} ({aj["motivo"]})'.replace(',', '.')
            print(rel_orc)
            with open(out_rel, 'a', encoding='utf-8') as f:
                f.write('\n' + rel_orc + '\n')
        except Exception as e:  # noqa: BLE001
            print('aviso: orçamento ao vivo não alterado:', e)
    if dire:
        dire['ajuste_pendente'] = None
    vp = (car.get('patrocinio') or {}).get('verba_pendente')
    if vp:
        try:
            antes, depois = ao_vivo.verba_salarios(vp, dire.get('orcamento_atual'), escrever_de_verdade=True)
            car['patrocinio'].pop('verba_pendente', None)
            escreveu = True
            print(f'PATROCÍNIO (ao vivo): verba de salários R$ {antes:,} -> R$ {depois:,}'.replace(',', '.'))
        except Exception as e:  # noqa: BLE001
            print('aviso: patrocínio ainda não entrou na verba:', e)
    if msg_nativa or apelido_novo:
        try:
            mensagens_save.guardar_modelos(d)   # modelos de mensagem vêm do save
        except Exception as e:  # noqa: BLE001
            print('aviso: modelos de mensagem não atualizados:', e)
    if msg_nativa:
        try:
            ao_vivo.mensagem(81, [tuple(msg_nativa['k'])], escrever_de_verdade=True)
            escreveu = True
            car.setdefault('msgs_nativas', []).append({'tipo': 81, 'jogador': msg_nativa['jogador'],
                                                       'nome': msg_nativa['nome'], 'data': list(hoje)})
            car['msgs_nativas'] = car['msgs_nativas'][-40:]
            print(f'MENSAGEM NATIVA (ao vivo): Evolução de {msg_nativa["nome"]}')
        except Exception as e:  # noqa: BLE001 - mensagem é enfeite: nunca derruba a reunião
            print('aviso: mensagem nativa não colocada:', e)
    if apelido_novo:
        k_ap = tuple(apelido_novo['k'])
        try:
            ao_vivo.apelido(k_ap, apelido_novo['codigo'], r['regs'][k_ap], escrever_de_verdade=True)
            escreveu = True
            car['apelido_mes'] = [hoje[0], hoje[1]]
            car.setdefault('apelidos', []).append({**apelido_novo, 'data': list(hoje)})
            car['historias'][f'Apelido|{chave(k_ap)}'] = {
                'data': list(hoje), 'restam': 3, 'peso': 4, 'motivo': f'ganhou o apelido "{apelido_novo["texto"]}"',
                'envolvidos': [chave(k_ap)]}
            print(f'APELIDO (ao vivo): {apelido_novo["nome"]} -> "{apelido_novo["texto"]}" (código {apelido_novo["codigo"]})')
        except Exception as e:  # noqa: BLE001
            print('aviso: apelido ao vivo não escrito (tenta de novo na próxima reunião):', e)
    return escreveu


TETO_CONFIANCA = {'pressao': 35, 'ultimato': 15}   # a nossa diretoria nunca fica mais calma que a do jogo


def espelhar_diretoria_nativa(car, d, hoje):
    """A Central espelha a diretoria do PES (diretoria_nativa.py): estado real (objetivo -> pressão -> ultimato ->
    demissão), teto na nossa confiança, manchetes quando o estado muda e o "termômetro antecipado" (a nossa confiança
    baixa perto da virada do mês avisa que o cargo será avaliado). Devolve notícias da rodada."""
    nat = diretoria_nativa.ler(d, hoje)
    ant = (car.get('diretoria_nativa') or {}).get('estado')
    if ant == 'ultimato' and nat['estado'] in ('sem_objetivo', 'tranquilo') and not nat['objetivo_desde']:
        nat['estado'], nat['texto'] = 'demitido', 'A diretoria rasgou o contrato do técnico.'
    car['diretoria_nativa'] = nat
    dire = car.get('diretoria') or {}
    noticias = []
    teto = TETO_CONFIANCA.get(nat['estado'])
    if teto is not None and dire.get('confianca', 100) > teto:
        dire['confianca'] = teto
        dire.setdefault('avaliacoes', []).append({'data': list(hoje), 'confianca': teto, 'delta': 0,
                                                  'motivos': [f'diretoria do clube em estado de {nat["estado"]}']})
    if nat['estado'] != ant and nat['estado'] != 'sem_objetivo' and ant is not None:
        car.setdefault('ecos', []).append({
            'pressao': {'manchete': 'Diretoria perde a paciência', 'fina': 'Imprensa já especula a saída do técnico.'},
            'ultimato': {'manchete': 'Ultimato: vencer ou cair', 'fina': 'O técnico precisa vencer a próxima partida para continuar no cargo.'},
            'demitido': {'manchete': 'Fim da linha', 'fina': 'A diretoria rasgou o contrato do técnico.'},
            'tranquilo': {'manchete': 'Diretoria define a meta da temporada', 'fina': 'Os resultados de liga serão avaliados mês a mês.'},
        }.get(nat['estado'], {'manchete': 'Bastidores', 'fina': nat['texto']}))
        if nat['estado'] in ('pressao', 'ultimato', 'demitido'):
            noticias.append(nat['texto'])
    # termômetro antecipado: o jogo só decide na virada do mês; a Central avisa antes
    if nat['estado'] in ('tranquilo', 'pressao') and dire.get('confianca', 100) < 35 and hoje[2] >= 20:
        aviso = f'{hoje[0]}-{hoje[1]:02d}'
        if car.get('aviso_virada') != aviso:
            car['aviso_virada'] = aviso
            noticias.append('Bastidores: a diretoria vai avaliar o cargo do técnico na virada do mês. '
                            'Os resultados de liga até lá decidem o futuro.')
    return noticias


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    ml = sys.argv[1]
    snap = next((a for a in sys.argv[2:] if not a.startswith('--')), V.SNAP)
    ensaio = '--ensaio' in sys.argv
    vivo = '--ao-vivo' in sys.argv   # escreve na MEMÓRIA do jogo aberto (o próprio jogo grava no próximo save)
    # --so-central: carreira de LABORATÓRIO (teste). Calcula tudo e atualiza a Central, mas não escreve NADA no jogo
    # (nem no save, nem na memória): o experimento fica intacto.
    so_central = '--so-central' in sys.argv
    laboratorio = so_central   # SÓ o modo explícito trava os botões da Central (11/10/2026: a trava de data marcava a
    #                            carreira real como laboratório quando o usuário simulava rápido e os cliques falhavam)
    global APELIDOS_TORCIDA, MENSAGENS_NATIVAS
    if so_central:
        APELIDOS_TORCIDA = MENSAGENS_NATIVAS = False
    stamp = dt.datetime.now().strftime('%Y%m%d_%H%M%S')
    work = os.path.join(TOOLS, 'save_work', 'vestiario_' + stamp)
    os.makedirs(work)
    os.makedirs(BACKUPS, exist_ok=True)
    troca_save.copiar_compartilhado(ml, os.path.join(BACKUPS, os.path.basename(ml) + '_' + stamp))
    troca_save.copiar_compartilhado(ml, os.path.join(work, 'original'))
    run([DECRYPT, os.path.join(work, 'original'), os.path.join(work, 'dec')])
    dat = os.path.join(work, 'dec', 'data.dat')
    d = open(dat, 'rb').read()

    estado = carregar_estado()
    if vivo and not so_central:
        # escrever ao vivo só se a carreira deste save é a que está CARREGADA no jogo (data da foto da memória)
        try:
            import janela
            dm = janela.career_date(snap)
            ds = V.analisar(d, snap)['hoje'] if dm else None
            # sem data na memória não dá para conferir: segue (as âncoras do ao_vivo já impedem escrever errado).
            # Memória À FRENTE do save (até 60 dias) = o usuário seguiu jogando enquanto a reunião rodava: mesma carreira.
            dif = (dt.date(*dm) - dt.date(*ds)).days if dm and ds else 0
            if dm and ds and not -4 <= dif <= 60:
                print(f'aviso: este save ({ds}) não é a carreira carregada no jogo ({dm}); nada é escrito no jogo nesta rodada')
                so_central, vivo = True, False
        except Exception as e:  # noqa: BLE001
            print('aviso: não deu para conferir a carreira carregada:', e)
    import carreira
    ck = f'{os.path.basename(ml)}|{carreira.time_do_usuario(d, V.TIME_DO_USUARIO)[1]}'
    clube.definir(ck.split('|', 1)[1])   # textos (jornais, notícias) com o nome/estádio do clube desta carreira
    clube.C['tecnico'] = carreira.bloco_usuario(d)[1] or V.TECNICO
    car = estado['carreiras'].setdefault(ck, {'ultima_rodada': None, 'setas': {}, 'historias': {}, 'noticias': []})
    car['ck'] = ck   # a Central do Técnico usa para separar os eventos do diário por carreira
    car['laboratorio'] = laboratorio

    # 1ª passada só para saber a rodada atual
    r0 = V.analisar(d, snap)
    # autocorreção (modo automático): se o último apelido gravado não está no save, o jogador não recarregou a
    # carreira e o jogo salvou por cima -> desfaz o registro para tentar de novo
    for ap in list(car.get('apelidos', []))[-1:]:
        k_ap = tuple(ap['k'])
        if k_ap in r0['regs'] and apelidos.codigo_de(r0['regs'][k_ap]) != ap['codigo']:
            car['apelidos'].remove(ap)
            car.pop('apelido_mes', None)
            car['historias'].pop(f'Apelido|{chave(k_ap)}', None)
            print(f'nota: apelido de {ap["nome"]} não chegou ao jogo (carreira não recarregada); será refeito')
    hoje = list(r0['hoje'])
    nova_rodada = car['ultima_rodada'] != hoje
    if nova_rodada and car['ultima_rodada'] is not None:
        for h in car['historias'].values():
            h['restam'] = max(0, h.get('restam', 0) - 1)
    # ações feitas na Central desde a última reunião (coletiva, setas escritas ao vivo...) entram no estado
    car.setdefault('ecos', []).extend(acoes.consumir(car, r0['J'], hoje))

    # decisões: resposta ao pedido da reunião anterior + cobrança das promessas
    noticias, negativas = [], 0
    resposta_usada = False
    dir_resp_usada = False
    msg_nativa = None
    apelido_novo = None
    if nova_rodada:
        pend = car.get('pedido')
        if pend:
            opcao = None
            try:
                if os.path.getmtime(RESPOSTA_FILE) > pend.get('criado_em', 0):
                    v = open(RESPOSTA_FILE, encoding='utf-8').read().strip()[:1]
                    opcao = int(v) if v in ('1', '2', '3') else None
            except OSError:
                pass
            noticias += D.aplicar_resposta(car, pend, opcao, r0, hoje)
            car['pedido'] = None
            resposta_usada = True
        noticias += D.cobrar_promessas(car, r0, hoje)

    r = V.analisar(d, snap, efeitos(car))
    J = r['J']
    rnd = random.Random(f'{ck}|{hoje}')

    # notícias: conflitos que ainda não saíram na mídia (1 de salário por rodada, 1 por jogador)
    if nova_rodada:
        ja_saiu, salario_saiu = set(), False
        for tipo, txt, env in r['conflitos']:
            if len(noticias) >= MAX_NOTICIAS:
                break
            hid = f'{tipo}|{chave(env[0]["k"])}'
            foco = env[1:] if tipo == 'Ego salarial' else env[:1]
            if hid in car['historias'] or any(chave(x['k']) in ja_saiu for x in foco):
                continue
            if tipo == 'Ego salarial':
                if salario_saiu:
                    continue
                salario_saiu = True
            ja_saiu.update(chave(x['k']) for x in foco)
            noticias.append(materia(tipo, env, r, rnd))
            negativas += 1
            alvo = env[1:] if tipo == 'Ego salarial' else env[:1]   # quem é o foco da matéria
            car['historias'][hid] = {'data': hoje, 'restam': RODADAS_POLEMICA, 'peso': PESO_POLEMICA,
                                     'motivo': f'polêmica na mídia ({tipo.lower()})',
                                     'envolvidos': [chave(x['k']) for x in alvo]}
        # números do mês (estatísticas nativas: só contam partidas JOGADAS, não simuladas) — 1 manchete por mês
        destaques = [j for j in J if j.get('desempenho')]
        if destaques:
            j = max(destaques, key=lambda j: abs(j['desempenho'][0]))
            hid = f'Numeros|{hoje[0]}-{hoje[1]:02d}'
            if hid not in car['historias']:
                noticias.append(f'NÚMEROS DO MÊS: {j["nome"]} — {j["desempenho"][1]}.')
                car['historias'][hid] = {'data': hoje, 'restam': 0, 'peso': 0, 'motivo': '', 'envolvidos': []}
        # um elogio por rodada para quem está voando
        def elogiado_recente(j):
            pref = f'Elogio|{chave(j["k"])}|'
            return any(hid.startswith(pref) and V.dias(tuple(hoje), tuple(h['data'])) < 21
                       for hid, h in car['historias'].items())
        quentes = [j for j in J if j['moral'] >= 85 and j['r_nota'] >= 6.8 and not elogiado_recente(j)]
        if quentes and len(noticias) < MAX_NOTICIAS + 1:
            j = max(quentes, key=lambda j: (j['r_nota'], j['t_gols']))
            hid = f'Elogio|{chave(j["k"])}|{hoje}'
            noticias.append(elogio(j, rnd))
            car['historias'][hid] = {'data': hoje, 'restam': 1, 'peso': PESO_ELOGIO, 'motivo': 'elogiado pela mídia',
                                     'envolvidos': [chave(j['k'])]}
        try:
            ult_r = (r.get('ultimos') or [])[-1:]
            dimg = -negativas + (1 if ult_r and ult_r[0]['pro'] > ult_r[0]['contra'] else -1 if ult_r and ult_r[0]['pro'] < ult_r[0]['contra'] else 0)
            img = crises.imagem(car)
            dimg += 1 if img < 55 else -1 if img > 70 else 0
            if dimg:
                crises.mexer_imagem(car, dimg, 'rodada (resultado e polêmicas)', hoje)
        except Exception as e:  # noqa: BLE001
            print('aviso: imagem não atualizada:', e)
        if negativas >= 3:
            noticias.append(f'Clima pesado {clube.C["em_ct"]}: a sequência de polêmicas já afeta o grupo todo.')
            car['historias'][f'Clima|{hoje}'] = {'data': hoje, 'restam': 1, 'peso': PESO_CLIMA,
                                                 'motivo': 'clima pesado no elenco',
                                                 'envolvidos': [chave(j['k']) for j in J]}
        # as matérias desta rodada já pesam agora
        r = V.analisar(d, snap, efeitos(car))
        J = r['J']
        # novo pedido de conversa (no máximo 1 por rodada)
        p = D.novo_pedido(r, car, hoje)
        if p:
            p['criado_em'] = dt.datetime.now().timestamp()
            car['pedido'] = p
        # diretoria / presidente (metas, confiança, reuniões) — não grava no save
        try:
            sml = SaveML.__new__(SaveML)
            sml.path, sml.d, sml.base = None, bytearray(d), d.index(b'ARSENAL' + bytes(1))
            n_dir, dir_resp_usada = diretoria.rodada(car, d, sml, r, snap, hoje)
            noticias += n_dir
            noticias += espelhar_diretoria_nativa(car, d, hoje)
        except Exception as e:  # noqa: BLE001 - a diretoria nunca pode impedir a reunião do vestiário
            print('aviso: diretoria não avaliada:', e)
        # mensagem NATIVA na caixa do jogo: "Evolução de X" (assistente técnico) para promessa sem minutos
        if MENSAGENS_NATIVAS:
            msg_nativa = escolher_evolucao(car, J, hoje)
            if msg_nativa:
                noticias.append(f'Assistente técnico recomenda dar minutos a {msg_nativa["nome"]}: '
                                f'"ele tem demonstrado ser muito promissor" (mensagem na caixa do jogo).')
        # apelido dado pela torcida (sistema NATIVO de apelidos: ficha do jogador + mensagem "Apelido do X")
        if APELIDOS_TORCIDA:
            apelido_novo = apelidos.escolher(car, J, r['regs'], hoje)
            if apelido_novo:
                noticias.append(f'A torcida batizou {apelido_novo["nome"]}: agora ele é "{apelido_novo["texto"]}".')
        # etapa 2: compromissos cobrados pelas súmulas, casos de disciplina e calendário/rodízio
        extras_midia = []
        try:
            noticias += compromissos.verificar(car, r, hoje)
            sml_e = SaveML.__new__(SaveML)
            sml_e.path, sml_e.d, sml_e.base = None, bytearray(d), d.index(b'ARSENAL' + bytes(1))
            noticias += exigencias.verificar(car, d, sml_e, r['ti'], r, hoje)
            # pedido de exigência sem resposta por 14 dias: fica para depois (o jogador fica um pouco chateado)
            vivos = []
            for c in car.get('casos', []):
                if c['tipo'] == 'exigencia' and V.dias(tuple(hoje), tuple(c['data'])) >= 14:
                    compromissos.historias(car, c['opcoes'][2]['efeitos'], [chave(j['k']) for j in J], hoje, f'Caso|{c["id"]}|gaveta')
                elif c['tipo'] == 'crise' and V.dias(tuple(hoje), tuple(c['data'])) >= 10:
                    # crise sem resposta: vale a opção mais omissa (a de pior imagem), e a imprensa cobra
                    o = min(c['opcoes'], key=lambda o: o.get('imagem', 0))
                    compromissos.historias(car, o.get('efeitos', []), [chave(j['k']) for j in J], hoje, f'Caso|{c["id"]}|gaveta')
                    crises.mexer_imagem(car, min(-3, o.get('imagem', 0)), 'crise sem resposta: ' + c['titulo'], hoje)
                    noticias.append(f'Sem resposta do técnico, a crise "{c["titulo"]}" se arrastou e manchou a imagem do clube.')
                elif c['tipo'] == 'celular' and V.dias(tuple(hoje), tuple(c['data'])) >= 7:
                    # mensagem sem resposta: vale o "visualizou e não respondeu" (última opção)
                    compromissos.historias(car, c['opcoes'][-1]['efeitos'], [chave(j['k']) for j in J], hoje, f'Caso|{c["id"]}|gaveta')
                    car.setdefault('celular_hist', []).append({'id': c['id'], 'data': list(hoje), 'contato': c.get('contato'),
                                                               'mensagens': c.get('mensagens') or [], 'resposta': '(sem resposta)'})
                elif c['tipo'] == 'pessoal' and V.dias(tuple(hoje), tuple(c['data'])) >= 10:
                    compromissos.historias(car, c['opcoes'][-1]['efeitos'], [chave(j['k']) for j in J], hoje, f'Caso|{c["id"]}|gaveta')
                else:
                    vivos.append(c)
            car['casos'] = vivos
            extras_midia += [{'manchete': e['manchete'], 'fina': e['fina']} for e in car.pop('compromissos_ecos', [])]
            car['casos'] = [c for c in car.get('casos', []) if c['tipo'] != 'calendario']   # pedido vale 1 rodada
            todos_k = [chave(j['k']) for j in J]
            for c in disciplina.expirar(car, hoje):
                o = c['opcoes'][0]
                compromissos.historias(car, o['efeitos'] + [{'k': '*', 'delta': -1, 'rodadas': 1,
                                                             'motivo': 'o técnico deixou um caso disciplinar sem resposta'}],
                                       todos_k, hoje, f'Caso|{c["id"]}|gaveta')
                noticias.append(f'O caso "{c["titulo"]}" morreu na gaveta: sem decisão do técnico, virou só advertência.')
                for k in c['envolvidos']:
                    car.setdefault('disciplina_hist', []).append({'k': k, 'data': list(hoje), 'sub': c['sub'],
                                                                  'gravidade': c['gravidade'], 'titulo': c['titulo'],
                                                                  'decisao': 'sem resposta (advertência)'})
            rnd_d = random.Random(f'disc|{ck}|{hoje}')
            dificuldade.calcular(car, d, hoje)          # técnico novo + espírito baixo = vestiário mais difícil
            novos = disciplina.gerar(r, car, hoje, rnd_d)
            novos += crises.gerar(r, car, hoje, rnd_d)
            car['casos'] = car.get('casos', []) + novos   # antes dos pedidos: um assunto por jogador por rodada
            cg = calendario.carga(r, hoje)
            car.setdefault('calendario', {})['carga'] = cg
            pedidos = calendario.pedidos(r, car, hoje, rnd_d, cg)
            car['casos'] += pedidos
            novos += pedidos
            exig = exigencias.gerar(r, car, d, sml_e, hoje, rnd_d)
            car['casos'] += exig
            novos += exig
            # patrocínio: posição na liga (para a meta), fim de contrato, propostas novas
            pat = car.setdefault('patrocinio', {})
            eu_tab = next((t for t in ((car.get('diretoria') or {}).get('tabela') or []) if t.get('eu')), None)
            if eu_tab and eu_tab.get('j'):
                temp_atual = hoje[0] if hoje[1] >= 7 else hoje[0] - 1
                pat.setdefault('ultima_posicao', {})[str(temp_atual)] = eu_tab['pos']
            fim = patrocinio.fechar_temporada(car, r, hoje)
            if fim:
                car['multas_falhas'] = car.get('multas_falhas', 0) + fim[0]   # entra no próximo ajuste de orçamento
                noticias.append('PATROCÍNIO: ' + fim[1])
            pat_casos = patrocinio.propostas(d, r, car, hoje, rnd_d)
            car['casos'] += pat_casos
            novos += pat_casos
            pess = humor.pessoais(r, car, hoje, rnd_d)
            car['casos'] += pess
            novos += pess
            # fatos reais da rodada (sequência de gols, jejum, primeiro gol, marcos, aniversário de clube)
            for f in humor.fatos(r, car, hoje):
                compromissos.historias(car, f['efeitos'], [chave(j['k']) for j in J], hoje, f'Humor|{f["id"]}')
                noticias.append(f['noticia'])
                extras_midia.append({'manchete': f['eco'][0], 'fina': f['eco'][1]})
                novos.append({'tipo': 'humor'})
            for c in novos:
                if c['tipo'] == 'humor':
                    continue
                noticias.append({'disciplina': 'DISCIPLINA: ', 'crise': 'CRISE: ', 'calendario': 'CALENDÁRIO: ', 'pessoal': 'VIDA PESSOAL: ', 'patrocinio': 'COMERCIAL: '}.get(c['tipo'], 'VESTIÁRIO: ') + c['titulo'] + '.')
                if c['tipo'] in ('disciplina', 'crise') and c['envolvidos']:
                    extras_midia.append({'tipo': 'disciplina', 'caso': c})
            if novos or extras_midia:
                r = V.analisar(d, snap, efeitos(car))   # promessas cumpridas/quebradas já pesam nesta reunião
                J = r['J']
        except Exception as e:  # noqa: BLE001 - nunca derruba a reunião
            print('aviso: disciplina/calendário não processados:', e)
        try:   # saídas/chegadas EFETIVADAS (elenco da reunião anterior x atual) + pendentes da tabela (saidas.py)
            import saidas
            ex = saidas.executadas(car, r, d, hoje)
            vistos = {(tuple(m['k']), m['tipo']) for m in ex}
            r['movimentos'] = ex + [m for m in r.get('movimentos') or [] if (tuple(m['k']), m['tipo']) not in vistos]
        except Exception as e:  # noqa: BLE001
            print('aviso: movimentações efetivadas:', e)
        # a liga inteira (e a copa continental): resultados, goleadas, zebras, líder, artilharia
        try:
            import partidas_save as _ps
            r['agenda'] = _ps.agenda(d)
            import temporada
            temporada.definir(r)   # liga e começo da temporada desta carreira (qualquer calendário)
            if not midia_liga.liga_valida(car.get('liga')):
                car.pop('liga', None)   # 11/10/2026: "Amistoso" gravado como liga na pré-temporada
            painel_liga, fatos_liga = midia_liga.cobertura(r, car, hoje, snap)
            if painel_liga:
                car['liga'] = painel_liga
            extras_midia += fatos_liga
        except Exception as e:  # noqa: BLE001
            print('aviso: cobertura da liga não gerada:', e)
        # as prévias que existiam: o pós-jogo compara o jogo que acabou com o que a comissão técnica previu
        prox_antigo = [x for x in (car.get('proximos') or [car.get('proximo_jogo')]) if x]
        try:   # próximos 3 jogos + enquete (calendário e estatísticas do próprio jogo); a Central usa o que o pulso
            car['proximos'] = proximo_jogo.proximos(d, r, car, hoje, snap)   # disser que é o próximo
            car['proximo_jogo'] = car['proximos'][0] if car['proximos'] else None
        except Exception as e:  # noqa: BLE001
            print('aviso: próximo jogo não calculado:', e)
        try:   # 12/10/2026: a corrida do usuário na liga (título, vagas, rebaixamento) para o jornal e a Central
            import disputa
            todas = r.get('todas_partidas') or []
            jogos_dsp = ([dict(p, jogado=True) for p in todas]
                         + [dict(p, jogado=False, gols1=0, gols2=0) for p in r.get('agenda') or []])
            mp = proximo_jogo._disputas(d, todas, hoje)
            sv = SaveML.__new__(SaveML)
            sv.path, sv.d, sv.base = None, bytearray(d), d.index(b'ARSENAL\x00')
            car['corrida'] = disputa.corrida(mp, r['ti'], lambda t: clube.nome_time(sv.name(t).strip()), jogos_dsp, hoje)
        except Exception as e:  # noqa: BLE001
            print('aviso: corrida da liga não calculada:', e)
        try:   # 12/10/2026: o momento acumulado (sequência, rival que encostou, semana decisiva) — momento.py
            import momento
            car['momento'] = momento.calcular(r, car, hoje)
        except Exception as e:  # noqa: BLE001
            print('aviso: momento do time não calculado:', e)
        for j in r['J']:   # traços (vaidoso, líder, jovem impaciente...) já para o jornal, os rumores e o celular
            j.setdefault('perfil', exigencias.perfil(j, r['J']))
        try:   # o mundo: artilharia, revelações, Bola de Ouro, seleção da temporada (destaques.py)
            import destaques
            destaques.da_reuniao(car, r, d, snap)
        except Exception as e:  # noqa: BLE001
            print('aviso: destaques do mundo não calculados:', e)
        try:   # história do clube: fecha a temporada no banco (o jogo apaga tudo na virada), recordes e marcos
            import historia
            for m in historia.da_reuniao(car, r, d, snap):
                noticias.append(('RECORDE: ' if m['tipo'] == 'recorde' else 'MARCO: ') + m['texto'])
                extras_midia.append({'tipo': 'marco', 'sub': m['chave'], 'peso': 3.5 if m['tipo'] == 'recorde' else 2.0 + m['valor'] / 100, 'm': m})
        except Exception as e:  # noqa: BLE001
            print('aviso: história do clube não gravada:', e)
        try:   # seleção da rodada e jogador do mês (rodada_mes.py): matérias vão com a imprensa (redator), fatos para as capas
            import rodada_mes
            ms_rm, fs_rm = rodada_mes.da_reuniao(car, r, d, snap)
            car['_imprensa_extra'] = ms_rm
            extras_midia += fs_rm
        except Exception as e:  # noqa: BLE001
            print('aviso: rodada/mês não gerados:', e)
        try:   # Time do mês OFICIAL do jogo x a seleção da imprensa (time_do_mes.py)
            import time_do_mes
            ms_t, fs_t = time_do_mes.da_reuniao(car, r, d, snap)
            car['_imprensa_extra'] = (car.get('_imprensa_extra') or []) + ms_t
            extras_midia += fs_t
        except Exception as e:  # noqa: BLE001
            print('aviso: time do mês oficial:', e)
        try:   # Data FIFA: os nossos nas seleções (data_fifa.py)
            import data_fifa
            ms_df, fs_df = data_fifa.da_reuniao(car, r, d, snap)
            car['_imprensa_extra'] = (car.get('_imprensa_extra') or []) + ms_df
            extras_midia += fs_df
            for f in fs_df:
                noticias.append(f'DATA FIFA: {len(f["convocados"])} jogadores do elenco defenderam as seleções.')
        except Exception as e:  # noqa: BLE001
            print('aviso: Data FIFA não gerada:', e)
        try:   # 12/10/2026: departamento médico na imprensa (lesoes.py): lesão nova avaliada no cenário, e a volta
            import lesoes
            ms_l, fs_l = lesoes.atualizar(car, r, hoje)
            car['_imprensa_extra'] = (car.get('_imprensa_extra') or []) + ms_l
            extras_midia += fs_l
            for m in ms_l:
                noticias.append(('DEPARTAMENTO MÉDICO: ' if 'volta' not in m['chave'][:5] else 'DE VOLTA: ') + m['titulo'])
        except Exception as e:  # noqa: BLE001
            print('aviso: lesões não acompanhadas:', e)
        try:   # 13/10/2026: a noite da Bola de Ouro (premiacao.py): capas, três vozes, vestiário, celular, redes, coletiva
            import imprensa as _imp
            import premiacao
            ctx_p = _imp._contexto(car, r, d, snap)
            ms_p, fs_p, nt_p, cs_p = premiacao.cerimonia(car, r, d, ctx_p['s'], ctx_p['P'], hoje)
            car['_imprensa_extra'] = (car.get('_imprensa_extra') or []) + ms_p
            extras_midia += fs_p
            noticias += nt_p
            car['casos'] = car.get('casos', []) + cs_p
        except Exception as e:  # noqa: BLE001
            print('aviso: premiação não coberta:', e)
        try:   # 12/10/2026: análise pós-jogo com o porquê, em três vozes (analise_jogo.py)
            import analise_jogo
            car['_imprensa_extra'] = (car.get('_imprensa_extra') or []) + analise_jogo.da_reuniao(car, r, snap, hoje)
        except Exception as e:  # noqa: BLE001
            print('aviso: análise do jogo não gerada:', e)
        try:   # rumores de mercado sobre os nossos (rumores.py) e o celular do técnico (celular.py)
            import celular
            import rumores
            rnd_c = random.Random(f'cel|{ck}|{hoje}')
            fs_r, nt_r, consultas = rumores.da_reuniao(car, r, d, snap, rnd_c)
            extras_midia += fs_r
            noticias += nt_r
            car['casos'] = car.get('casos', []) + celular.gerar(r, car, hoje, rnd_c, consultas)
        except Exception as e:  # noqa: BLE001
            print('aviso: rumores/celular não gerados:', e)
        try:   # elencos vitoriosos: obrigação de vencer, renovações, joia da base (vitoriosos.py)
            import vitoriosos
            fs_v, nt_v, cs_v = vitoriosos.da_reuniao(car, r, hoje, random.Random(f'vit|{ck}|{hoje}'))
            extras_midia += fs_v
            noticias += nt_v
            car['casos'] = car.get('casos', []) + cs_v
        except Exception as e:  # noqa: BLE001
            print('aviso: elencos vitoriosos:', e)
        try:   # arquibancada: o termômetro da torcida (torcida.py)
            import torcida
            _t, nt_t = torcida.calcular(car, r, hoje)
            noticias += nt_t
        except Exception as e:  # noqa: BLE001
            print('aviso: arquibancada:', e)
        try:   # séries para os gráficos da Central: moral do grupo, orçamento e confiança da diretoria
            sr = car.setdefault('serie', [])
            dire = car.get('diretoria') or {}
            if not sr and dire.get('orcamento_atual'):   # 1ª vez: o orçamento é reconstruído para trás pelas entradas/saídas
                v = dire['orcamento_atual']
                for h in reversed(dire.get('orcamento_hist') or []):
                    sr.insert(0, {'d': list(h['data']), 'orc': v})
                    v -= h.get('delta') or 0
            ponto = {'d': list(hoje), 'moral': round(sum(j['moral'] for j in J) / max(1, len(J)), 1),
                     'orc': dire.get('orcamento_atual'), 'conf': dire.get('confianca'), 'torcida': (car.get('torcida') or {}).get('humor')}
            sr[:] = [x for x in sr if x['d'] != list(hoje)] + [ponto]
            sr.sort(key=lambda x: tuple(x['d']))
            car['serie'] = sr[-240:]
        except Exception as e:  # noqa: BLE001
            print('aviso: séries dos gráficos:', e)
        # mídia da rodada: capas de jornal, programa "Bola na Mesa" e coletiva de imprensa (Central do Técnico)
        try:
            midia.edicao(car, r, hoje, apelido_novo, car.pop('ecos', []) + extras_midia)
        except Exception as e:  # noqa: BLE001 - a mídia nunca pode impedir a reunião
            print('aviso: mídia da rodada não gerada:', e)
        try:   # imprensa (banco historico/imprensa.db): pré-jogo, 4 x 4, pós-jogo, temporada, mercado
            import imprensa
            imprensa.rodada(car, r, d, hoje, snap, prox_antigo)
        except Exception as e:  # noqa: BLE001
            print('aviso: imprensa não gerada:', e)

    # setas: base = seta do jogo (se ainda é a que nós gravamos, usa a original que o jogo tinha sorteado)
    mudancas, linhas_seta, setas_map = {}, [], {}
    for j in J:
        k = j['k']
        if k not in r['regs']:
            continue
        atual = js.campos(r['regs'][k])['seta']
        mem = car['setas'].get(chave(k))
        base = mem['original'] if mem and atual == mem['gravada'] else atual
        alvo = V.seta_alvo(base, j['moral'])
        car['setas'][chave(k)] = {'original': base, 'gravada': alvo}
        setas_map[j['nome']] = (base, alvo)
        if alvo != atual:
            mudancas[k] = js.set_seta(r['regs'][k], alvo)
        if alvo != base:
            linhas_seta.append(f'  {j["nome"]}: seta {base} -> {alvo} (moral {j["moral"]})')

    if apelido_novo:
        k_ap = tuple(apelido_novo['k'])
        mudancas[k_ap] = apelidos.com_apelido(mudancas.get(k_ap, r['regs'][k_ap]), apelido_novo['codigo'])

    # relatório + notícias
    rel = V.relatorio(r)
    rel += '\n\nSETAS AJUSTADAS PELA MORAL (0 pior .. 4 ótima):\n' + ('\n'.join(linhas_seta) or '  nenhuma')
    rel += '\n\nNOTÍCIAS DESTA RODADA:\n' + ('\n'.join('  - ' + n for n in noticias) or '  nenhuma nova')
    pend = car.get('pedido')
    decisao_txt = D.texto_pedido(pend) if pend else []
    rel += '\n\n' + ('\n'.join(decisao_txt) if decisao_txt else 'Nenhum pedido de conversa.')
    abertas = [pr for pr in car.get('promessas', []) if pr['status'] == 'aberta']
    rel += '\nPromessas em aberto: ' + (', '.join(f'{pr["nome"]} ({pr["tipo"]})' for pr in abertas) or 'nenhuma')
    os.makedirs(os.path.join(HERE, 'historico'), exist_ok=True)
    out_rel = os.path.join(HERE, 'historico', f'vestiario_{stamp}.txt')
    open(out_rel, 'w', encoding='utf-8').write(rel)

    h = r['hoje']
    news_txt = [f'VESTIÁRIO — {h[2]:02d}/{h[1]:02d}/{h[0]}']
    for n in noticias:
        news_txt += textwrap.wrap('• ' + n, 95, subsequent_indent='  ')
    if not noticias:
        news_txt.append('Sem novidades no vestiário.')
    reu_dir = (car.get('diretoria') or {}).get('reuniao')
    if reu_dir and reu_dir.get('opcoes'):
        news_txt.append(f'>> {reu_dir["titulo"]}: responda na Central do Técnico.')
    humores = sorted(J, key=lambda j: j['moral'])
    news_txt.append('Em baixa: ' + ', '.join(f'{j["nome"]} ({j["moral"]})' for j in humores[:3]))
    news_txt.append('Em alta: ' + ', '.join(f'{j["nome"]} ({j["moral"]})' for j in humores[::-1][:3]))

    if ensaio:
        print(rel)
        print('\n'.join(news_txt))
        print('\nENSAIO: save e memória do vestiário NÃO foram alterados.')
        return

    # orçamento de transferências (diretoria, etapa 3b): ajuste calculado pela diretoria nesta rodada
    dire = car.get('diretoria') or {}
    aj = dire.get('ajuste_pendente')
    falhas = car.pop('multas_falhas', 0)   # multas que não entraram ao vivo no orçamento vão junto aqui
    try:   # orçamento ilegível (ex.: valor absurdo de teste) não pode derrubar a reunião
        if falhas and MEXER_ORCAMENTO:
            if aj:
                aj = {**aj, 'delta': aj['delta'] + falhas, 'motivo': aj['motivo'] + ' + multas disciplinares'}
            else:
                aj = {'antes': financas_save.ler(d, r['ti'])['orcamento_transf'], 'delta': falhas,
                      'motivo': 'multas disciplinares', 'data': list(hoje)}
        if aj and MEXER_ORCAMENTO:
            orc_antes = financas_save.ler(d, r['ti'])['orcamento_transf']
            if orc_antes != aj['antes']:
                print('aviso: orçamento mudou desde o cálculo; ajuste da diretoria cancelado')
                aj = None
        else:
            aj = None
    except RuntimeError as e:
        print('aviso: orçamento não lido; ajuste fica para a próxima reunião:', e)
        car['multas_falhas'] = falhas
        aj = None
    ao_vivo_ok = False
    if so_central:
        if dire:
            dire['ajuste_pendente'] = None
    elif vivo and (mudancas or aj or msg_nativa or apelido_novo or (car.get('patrocinio') or {}).get('verba_pendente')):
        ao_vivo_ok = gravar_ao_vivo(r, d, mudancas, aj, msg_nativa, apelido_novo, car, dire, hoje, out_rel)
    elif mudancas or aj or msg_nativa or apelido_novo:
        d2 = js.regravar(d, mudancas) if mudancas else d
        r2 = js.registros(js.blob(d2))
        alterados = [k for k in r['regs'] if r['regs'][k] != r2.get(k)]
        assert sorted(alterados) == sorted(mudancas), 'mudou algo além das setas pedidas'
        if aj:
            d3 = financas_save.com_orcamento(d2, r['ti'], aj['antes'] + aj['delta'])
            pos = financas_save.achar_bloco(d2, r['ti'])
            dif = [i for i in range(pos - 64, pos + 64) if d2[i] != d3[i]]
            assert len(d3) == len(d2) and dif and min(dif) >= pos and max(dif) < pos + 4, 'orçamento: mudou além dos 4 bytes'
            assert d2[:pos] == d3[:pos] and d2[pos + 4:] == d3[pos + 4:], 'orçamento: mudou algo fora do campo'
            d2 = d3
            novo = financas_save.ler(d2, r['ti'])['orcamento_transf']
            dire.setdefault('orcamento_hist', []).append({**aj, 'depois': novo})
            dire['orcamento_hist'] = dire['orcamento_hist'][-24:]
            dire['orcamento_atual'] = novo
            rel_orc = f'ORÇAMENTO: R$ {aj["antes"]:,} -> R$ {novo:,} ({aj["motivo"]})'.replace(',', '.')
            print(rel_orc)
            with open(out_rel, 'a', encoding='utf-8') as f:
                f.write('\n' + rel_orc + '\n')
        if msg_nativa:
            try:
                mensagens_save.guardar_modelos(d2)
                ini = mensagens_save.achar_caixa(d2)
                nova = struct.unpack_from('<HBB', d2, ini + mensagens_save.mais_nova(d2, ini) * mensagens_save.REC + 8)
                data_msg = max(tuple(hoje), tuple(nova))
                d3, slot = mensagens_save.inserir(d2, 81, data_msg, jogadores=[tuple(msg_nativa['k'])])
                a, b = ini + slot * mensagens_save.REC, ini + (slot + 1) * mensagens_save.REC
                idx = ini + mensagens_save.INDICE_REL
                assert len(d3) == len(d2) and d2[:a] == d3[:a] and d2[b:idx] == d3[b:idx] and d2[idx + 1:] == d3[idx + 1:],                     'mensagem: mudou algo fora da posição/contador'
                d2 = d3
                car.setdefault('msgs_nativas', []).append({'tipo': 81, 'jogador': msg_nativa['jogador'],
                                                           'nome': msg_nativa['nome'], 'data': list(data_msg)})
                car['msgs_nativas'] = car['msgs_nativas'][-40:]
                print(f'MENSAGEM NATIVA: Evolução de {msg_nativa["nome"]} ({data_msg[2]:02d}/{data_msg[1]:02d}/{data_msg[0]})')
            except Exception as e:  # noqa: BLE001 - mensagem é enfeite: nunca derruba a reunião
                print('aviso: mensagem nativa não colocada:', e)
        if apelido_novo:
            try:
                ini = mensagens_save.achar_caixa(d2)
                nova = struct.unpack_from('<HBB', d2, ini + mensagens_save.mais_nova(d2, ini) * mensagens_save.REC + 8)
                data_msg = max(tuple(hoje), tuple(nova))
                u = (apelidos.GRUPO << 16) | apelido_novo['codigo']
                d3, slot = mensagens_save.inserir(d2, 89, data_msg, jogadores=[tuple(apelido_novo['k'])],
                                                  extra={64: ('<I', u)})
                a, b = ini + slot * mensagens_save.REC, ini + (slot + 1) * mensagens_save.REC
                idx = ini + mensagens_save.INDICE_REL
                assert len(d3) == len(d2) and d2[:a] == d3[:a] and d2[b:idx] == d3[b:idx] and d2[idx + 1:] == d3[idx + 1:],                     'mensagem do apelido: mudou algo fora da posição/contador'
                d2 = d3
            except Exception as e:  # noqa: BLE001 - a mensagem é enfeite; o apelido na ficha já vale
                print('aviso: mensagem do apelido não colocada:', e)
            car['apelido_mes'] = [hoje[0], hoje[1]]
            car.setdefault('apelidos', []).append({**apelido_novo, 'data': list(hoje)})
            car['historias'][f'Apelido|{chave(tuple(apelido_novo["k"]))}'] = {
                'data': list(hoje), 'restam': 3, 'peso': 4, 'motivo': f'ganhou o apelido "{apelido_novo["texto"]}"',
                'envolvidos': [chave(tuple(apelido_novo['k']))]}
            print(f'APELIDO: {apelido_novo["nome"]} -> "{apelido_novo["texto"]}" (código {apelido_novo["codigo"]})')
        if dire:
            dire['ajuste_pendente'] = None
        open(dat, 'wb').write(d2)
        out = os.path.join(work, 'ML_novo')
        run([ENCRYPT, os.path.join(work, 'dec'), out])
        run([DECRYPT, out, os.path.join(work, 'check')])
        assert open(os.path.join(work, 'check', 'data.dat'), 'rb').read() == d2, 'ida e volta não bateu'
        troca_save.substituir(ml, out, os.path.join(work, 'original'))   # confere byte a byte + troca atômica
    elif dire:
        dire['ajuste_pendente'] = None
    car['ultima_rodada'] = hoje
    car['noticias'] = (car['noticias'] + [{'data': hoje, 'texto': n} for n in noticias])[-60:]
    gravar_estado(estado)
    with open(NEWS_FILE, 'w', encoding='utf-8') as f:
        f.write('\n'.join(news_txt) + '\n')
    if decisao_txt:
        with open(DECISAO_FILE, 'w', encoding='utf-8') as f:
            for linha in decisao_txt:
                f.write('\n'.join(textwrap.wrap(linha, 95, subsequent_indent='      ')) + '\n')
    elif os.path.exists(DECISAO_FILE):
        os.remove(DECISAO_FILE)
    if resposta_usada and os.path.exists(RESPOSTA_FILE):
        os.remove(RESPOSTA_FILE)
    if dir_resp_usada and os.path.exists(diretoria.RESPOSTA):
        os.remove(diretoria.RESPOSTA)
    try:   # alvos de mercado: craques insatisfeitos em outros clubes (vestiário dos clubes da IA)
        import aplicar as _ap
        import mercado as _me
        import potencial as _po
        import vestiario_ia as _vi
        sml2 = SaveML.__new__(SaveML)
        sml2.path, sml2.d, sml2.base = None, bytearray(d), d.index(b'ARSENAL' + bytes(1))
        _times = _ap.build_teams(sml2, dados.load_players(snap), 800)
        _ins = _vi.insatisfeitos(d, _times, _me.best_rating, r['ti'], excluir=_po.national_team_names())
        car['insatisfeitos_fora'] = sorted(
            ({**v, 'clube': sml2.name(v['time'])} for v in _ins.values() if v['u'] >= 0.5),
            key=lambda v: (-v['nota'], -v['u']))[:15]
    except Exception as e:  # noqa: BLE001
        print('aviso: alvos de mercado não calculados:', e)
    for j in r['J']:   # perfil (traços e desejos) para os cartões da Central
        j['perfil'] = exigencias.perfil(j, r['J'])
    try:   # escudos oficiais para a Central (só refaz se o mapa não existe ou a base do patch mudou)
        import escudos
        if not os.path.exists(escudos.ARQ) or os.path.getmtime(escudos.ARQ) < os.path.getmtime(escudos.TEAM_BIN):
            escudos.gerar(d)
    except Exception as e:  # noqa: BLE001
        print('aviso: escudos não atualizados:', e)
    try:
        central_dados.exportar(r, car, noticias, setas_map)   # Central do Técnico (só leitura)
    except Exception as e:  # noqa: BLE001 - a Central nunca pode atrapalhar a reunião
        print('aviso: não consegui atualizar a Central:', e)
    sys.stdout.reconfigure(encoding='utf-8')
    print(rel)
    if so_central:
        print('\nSÓ CENTRAL (carreira de laboratório): nada foi escrito no jogo')
    elif vivo:
        print('\nMEMÓRIA ATUALIZADA AO VIVO (não precisa recarregar)' if ao_vivo_ok else '\nNADA ESCRITO NA MEMÓRIA')
    else:
        print('\nSAVE ATUALIZADO' if (mudancas or aj) else '\nNENHUMA SETA MUDOU (save não alterado)')


if __name__ == '__main__':
    main()
