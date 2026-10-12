"""Vestiário IA v1 — SOMENTE LEITURA: lê o save da Master League e gera um relatório do elenco do usuário.

Para cada jogador calcula:
  - STATUS (lenda, ídolo, superastro, craque, promessa, veterano, elenco) por nota, idade, tempo de casa e produção;
  - MORAL 0-100 (minutos x o que ele espera pelo status, notas recentes, resultados do time, salário x colegas,
    contrato acabando, braçadeira);
  - TORCIDA 0-100 (produção na temporada, notas, tempo de casa, status);
  - LIDERANÇA (candidatos à braçadeira).
E lista os CONFLITOS: ego salarial, disputa de posição, disputa pela braçadeira, insatisfeitos com minutos.

Uso:  python vestiario.py <arquivo ML0000000X | data.dat descriptografado> [foto_memoria.bin]
Fontes: save (elenco, registros de jogador, súmulas, capitão) + foto de memória (nomes, atributos, idade).
Nada é gravado no save. O relatório vai para historico/vestiario_<data>.txt.
"""
import datetime as dt
import os
import shutil
import struct
import subprocess
import sys

import dados
import encaixe
import estatisticas_save as est
import jogadores_save as js
import partidas_save as ps
from save_ml import SaveML

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.normpath(os.path.join(HERE, '..'))
DECRYPT = os.path.join(TOOLS, 'pesXdecrypter', 'decrypter21.exe')
GAME_DIR = os.path.normpath(os.path.join(TOOLS, '..', 'eFootball PES 2021'))
SNAP = os.path.join(GAME_DIR, 'mercado_snap.bin')
HIST = os.path.join(HERE, 'historico')

TIME_DO_USUARIO = 'MANCHESTER UNITED'
TECNICO = 'Filipe Luís'          # nome do técnico no save (acha o bloco do time do usuário)
JANELA = 8                       # últimos N jogos do time para minutos/forma
SKILL_CAPITAO, SKILL_RACA = 25, 27
SALARIO_X = 430                  # salário do save x 430 = R$ na tela
CARENCIA_DIAS = 35               # recém-chegado não reclama de minutos nas primeiras semanas

# 'Função no time' nativa da ML (byte +72 do registro do jogador), confirmada na tela em 09/10/2026
FUNCOES = {0: '', 1: 'Jovem promessa', 2: 'Protegido', 5: 'Astro', 6: 'Líder', 10: 'Motorzinho', 12: 'Batalhador',
           13: 'Homem de referência', 16: 'Virtuoso', 18: 'Ídolo'}
LIDERANCA_FUNCAO = {'Líder': 15, 'Ídolo': 8, 'Homem de referência': 6, 'Batalhador': 3}
STATUS_ORDEM = ['Lenda', 'Ídolo', 'Superastro', 'Craque', 'Promessa', 'Veterano', 'Elenco']
# fatia de minutos que cada status ESPERA ter quando está entre os 11 ideais / fora deles
ESPERA = {'Lenda': (0.85, 0.45), 'Ídolo': (0.85, 0.40), 'Superastro': (0.90, 0.50), 'Craque': (0.80, 0.35),
          'Promessa': (0.60, 0.15), 'Veterano': (0.70, 0.20), 'Elenco': (0.70, 0.15)}


def dias(a, b):
    return (dt.date(*a) - dt.date(*b)).days


def carregar(path):
    """Aceita o save criptografado (ML0000000X) ou um data.dat já descriptografado."""
    d = open(path, 'rb').read()
    if b'ARSENAL\x00' in d[:0x10000]:
        return d
    work = os.path.join(TOOLS, 'save_work', 'vestiario_' + dt.datetime.now().strftime('%Y%m%d_%H%M%S'))
    os.makedirs(work)
    shutil.copy2(path, os.path.join(work, 'original'))
    r = subprocess.run([DECRYPT, os.path.join(work, 'original'), os.path.join(work, 'dec')],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr or r.stdout)
    return open(os.path.join(work, 'dec', 'data.dat'), 'rb').read()


GRUPO_NUMEROS = {'GK': None, 'CB': 'DEF', 'LB': 'DEF', 'RB': 'DEF', 'DMF': 'DEF', 'CMF': 'MEI', 'AMF': 'MEI',
                 'LMF': 'MEI', 'RMF': 'MEI', 'LWF': 'ALA', 'RWF': 'ALA', 'SS': 'ATA', 'CF': 'ATA'}


def _pct(a, b):
    return a / b if b else None


def avaliar_numeros(pos, e):
    """Desempenho técnico do MÊS (estatísticas nativas do jogo) -> (delta de moral, motivo) ou None.
    Só vale com pelo menos 180 minutos no mês. Critério por função:
      ATA: % de chutes no gol | ALA: % de dribles certos | MEI: % de passes certos | DEF: % de bolas aéreas
      ganhas e desarmes+interceptações por 90 minutos."""
    g = GRUPO_NUMEROS.get(pos)
    if not e or not g or e['minutos'] < 180:
        return None
    if g == 'ATA' and e['chutes'] >= 6:
        p = _pct(e['chutes_gol'], e['chutes'])
        if p >= 0.45:
            return 5, f'mês ótimo nas finalizações ({p:.0%} dos chutes no gol)'
        if p < 0.25:
            return -5, f'mês ruim nas finalizações (só {p:.0%} dos chutes no gol)'
    if g == 'ALA' and e['dribles'] >= 10:
        p = _pct(e['dribles_ok'], e['dribles'])
        if p >= 0.78:
            return 5, f'mês ótimo nos dribles ({p:.0%} certos)'
        if p < 0.55:
            return -5, f'mês ruim nos dribles (só {p:.0%} certos)'
    if g == 'MEI' and e['passes'] >= 30:
        p = _pct(e['passes_ok'], e['passes'])
        if p >= 0.85:
            return 4, f'mês ótimo nos passes ({p:.0%} certos)'
        if p < 0.65:
            return -4, f'mês ruim nos passes (só {p:.0%} certos)'
    if g == 'DEF':
        acoes90 = (e['desarmes'] + e['interceptacoes']) * 90 / e['minutos']
        if e['aereas'] >= 6:
            p = _pct(e['aereas_ok'], e['aereas'])
            if p < 0.40:
                return -5, f'mês ruim nas divididas pelo alto (venceu só {p:.0%})'
            if p >= 0.65 and acoes90 >= 2.5:
                return 5, f'mês sólido na defesa ({p:.0%} pelo alto, {acoes90:.1f} desarmes+interceptações por jogo)'
        if acoes90 < 1.0 and e['minutos'] >= 270:
            return -3, f'pouco combativo no mês ({acoes90:.1f} desarmes+interceptações por jogo)'
    return None


def seta_alvo(seta_jogo, moral):
    """Moral -> ajuste na seta de condição (0 pior .. 4 ótima) sobre a seta que o próprio jogo sorteou."""
    delta = 1 if moral >= 85 else -2 if moral < 35 else -1 if moral < 45 else 0
    return max(0, min(4, seta_jogo + delta))


def analisar(d, snap=SNAP, extra=None):
    """extra: {(reg, id): [(delta_moral, motivo), ...]} — efeitos que vêm de fora (ex.: polêmica na mídia)."""
    extra = extra or {}
    s = SaveML.__new__(SaveML)
    s.path, s.d, s.base = None, bytearray(d), d.index(b'ARSENAL\x00')
    import carreira
    ti = carreira.indice_do_usuario(d)
    if ti is None:
        ti = s.find_team(TIME_DO_USUARIO)
    elenco = s.squad(ti)
    regs = js.registros(js.blob(d))
    fotos = dados.load_players(snap)
    blk, tecnico = carreira.bloco_usuario(d)   # posição fixa (vale para qualquer carreira)
    if blk is None:
        blk, tecnico = s.user_block(TECNICO), TECNICO
    cap_idx = s.d[blk + 49]
    capitao = elenco[cap_idx] if cap_idx < len(elenco) else None
    cobradores = {elenco[i] for i in s.d[blk + 40:blk + 46] if i < len(elenco)}

    todas_partidas = ps.todas(d, *ps.FAIXA)
    jogos = sorted((p for p in todas_partidas if ti in (p['time1'], p['time2'])),
                   key=lambda p: p['data'])
    hoje = jogos[-1]['data'] if jogos else (2000, 1, 1)
    try:   # o jogo apaga as súmulas na virada de temporada: a mensagem mais nova da caixa também dá o "hoje"
        import mensagens_save
        cx = mensagens_save.achar_caixa(d)
        hoje = max(tuple(hoje), struct.unpack_from('<HBB', d, cx + mensagens_save.mais_nova(d, cx) * mensagens_save.REC + 8))
    except Exception:  # noqa: BLE001
        pass
    if tuple(hoje) < (2015, 1, 1):   # carreira recém-criada: sem jogos e sem mensagens -> data da foto da memória
        try:
            import janela
            hoje = tuple(janela.career_date(snap) or hoje)
        except Exception:  # noqa: BLE001
            pass
    import temporada   # 12/10/2026: o começo da temporada vem da 1ª rodada da liga do clube (Brasil = janeiro...)
    ini_temp = temporada.inicio(todas_partidas, temporada.liga(todas_partidas, ti), hoje)

    # resultados do time
    def pontos(p):
        g_n, g_c = (p['gols1'], p['gols2']) if p['time1'] == ti else (p['gols2'], p['gols1'])
        return 3 if g_n > g_c else 1 if g_n == g_c else 0
    ult = jogos[-5:]
    ppg = sum(pontos(p) for p in ult) / max(1, len(ult))

    # jogadores
    J = []
    for k in elenco:
        f = fotos.get(k)
        c = js.campos(regs[k]) if k in regs else {}
        if f is None:
            continue
        ovr = round(encaixe.rating(f, f.pos))
        chegada = c.get('chegada') or (2020, 1, 1)
        if chegada == (2020, 1, 1) and k in regs and (struct.unpack_from('<I', regs[k], 96)[0] & 0x3FFF) != ti:
            # 01/01/2020 = "no clube desde o início da carreira", e +96 diz QUAL clube. Se não é o do usuário,
            # ele chegou depois (ex.: Gavi, emprestado e comprado): conta do 1º jogo pelo time do usuário.
            meus = [p['data'] for p in jogos
                    if any((x['reg'], x['pid']) == k for x in p['linhas1'] + p['linhas2'])]
            chegada = meus[0] if meus else hoje
        anos = max(0.0, dias(hoje, chegada) / 365.25)
        temp = [p for p in jogos if p['data'] >= ini_temp and p['data'] >= chegada]
        rec = [p for p in jogos if p['data'] >= chegada][-JANELA:]

        def linhas(lst):
            out = []
            for p in lst:
                for x in p['linhas1'] + p['linhas2']:
                    if (x['reg'], x['pid']) == k:
                        out.append(x)
            return out
        lt, lr = linhas(temp), linhas(rec)
        jp = dict(
            k=k, nome=f.name.strip(), pos=f.pos, idade=f.age, ovr=ovr, salario=c.get('salario', 0),
            contrato=c.get('contrato_fim'), chegada=chegada, anos=anos, seta=c.get('seta'), condicao=c.get('condicao'),
            capitao=(k == capitao), cobrador=(k in cobradores),
            skill_cap=SKILL_CAPITAO in f.skills, skill_raca=SKILL_RACA in f.skills,
            # mérito de bola parada pelos atributos do próprio jogo (exigencias.py compara pedinte x dono do posto)
            n_penalti=round(f['finish'] * 0.55 + f['place_kick'] * 0.35 + f['kick_pwr'] * 0.10 + (8 if 36 in f.skills else 0)),
            n_falta=round(f['place_kick'] * 0.5 + f['curl'] * 0.35 + f['kick_pwr'] * 0.15
                          + (4 if 8 in f.skills else 0) + (4 if 32 in f.skills else 0) + (3 if 15 in f.skills else 0)),
            funcao=FUNCOES.get(c.get('funcao', 0), f'função {c.get("funcao")}'), funcao_prog=c.get('funcao_prog', 0),
            apelido=c.get('apelido', 0),
            t_jogos=len(lt), t_gols=sum(x['gols'] for x in lt), t_assist=sum(x['assist'] for x in lt),
            t_titular=sum(x['titular'] for x in lt),
            t_nota=(sum(x['nota'] for x in lt if x['nota']) / max(1, sum(1 for x in lt if x['nota']))) if lt else 0,
            r_jogos_time=len(rec), r_min=sum(x['minutos'] for x in lr),
            r_nota=(sum(x['nota'] for x in lr if x['nota']) / max(1, sum(1 for x in lr if x['nota']))) if lr else 0,
            r_gols=sum(x['gols'] for x in lr),
        )
        J.append(jp)

    # estatísticas detalhadas do jogo (blocos do time do usuário: [mês anterior], mês atual, temporada)
    try:
        blocos = est.tabelas(d, set(regs), ini=0x400000, fim=0x1100000, minimo=5)
    except Exception:  # noqa: BLE001
        blocos = []
    blocos.sort()
    temp_est = est.por_jogador(d, *blocos[-1]) if blocos else {}
    mes_est = est.por_jogador(d, *blocos[-2]) if len(blocos) >= 2 else {}
    for j in J:
        j['est_temp'] = temp_est.get(j['k'])
        j['est_mes'] = mes_est.get(j['k'])
        j['desempenho'] = avaliar_numeros(j['pos'], j['est_mes'])

    # 11 ideais (4-3-3 de referência) para saber quem "deveria" ser titular
    ideais = {id(p) for _, p, _ in encaixe.best_xi([fotos[j['k']] for j in J])[0]}
    for j in J:
        j['ideal'] = id(fotos[j['k']]) in ideais

    # STATUS
    melhor_ovr = max(j['ovr'] for j in J)
    for j in J:
        prod = j['t_gols'] + 0.7 * j['t_assist']
        if j['anos'] >= 8 and j['ovr'] >= 84:
            st = 'Lenda'
        elif j['anos'] >= 4 and (j['ovr'] >= 85 or prod >= 8):
            st = 'Ídolo'
        elif j['ovr'] >= max(90, melhor_ovr - 4):
            st = 'Superastro'
        elif j['ovr'] >= 85:
            st = 'Craque'
        elif j['idade'] <= 21:
            st = 'Promessa'
        elif j['idade'] >= 32:
            st = 'Veterano'
        else:
            st = 'Elenco'
        # a função nativa do jogo pesa no status (o elenco reconhece o papel dele)
        rank = STATUS_ORDEM.index
        if j['funcao'] == 'Ídolo' and rank(st) > rank('Ídolo'):
            st = 'Ídolo'
        elif j['funcao'] in ('Virtuoso', 'Superastro') and rank(st) > rank('Superastro'):
            st = 'Superastro'
        elif j['funcao'] == 'Astro' and rank(st) > rank('Craque'):
            st = 'Craque'
        elif j['funcao'] in ('Jovem promessa', 'Protegido') and st == 'Elenco':
            st = 'Promessa'
        j['status'] = st

    # LIDERANÇA (braçadeira)
    for j in J:
        idade_f = 10 if 27 <= j['idade'] <= 34 else 5 if j['idade'] >= 24 else 0
        j['lider'] = round(min(j['anos'], 10) * 3 + idade_f + (12 if j['skill_cap'] else 0) +
                           (4 if j['skill_raca'] else 0) + {'Lenda': 15, 'Ídolo': 10, 'Superastro': 8,
                                                            'Craque': 5}.get(j['status'], 0) +
                           (6 if j['ideal'] else 0) +
                           round(LIDERANCA_FUNCAO.get(j['funcao'], 0) * (0.5 + j['funcao_prog'] / 510)))
    lideres = sorted(J, key=lambda j: -j['lider'])
    cap = next((j for j in J if j['capitao']), None)

    # MORAL, TORCIDA e motivos
    conflitos = []
    ego = {}
    for j in J:
        mot = []
        m = 70.0
        esp = ESPERA[j['status']][0 if j['ideal'] else 1]
        if j['r_jogos_time'] >= 2 and dias(hoje, j['chegada']) >= CARENCIA_DIAS:
            fatia = j['r_min'] / (90 * j['r_jogos_time'])
            dm = max(-30, min(15, (fatia - esp) * 60))
            m += dm
            if dm <= -8:
                mot.append(f'joga pouco ({fatia:.0%} dos minutos, espera ~{esp:.0%})')
            elif dm >= 6:
                mot.append(f'tem minutos ({fatia:.0%})')
        else:
            mot.append('recém-chegado/sem jogos suficientes')
        if j['r_nota']:
            dn = max(-12, min(12, (j['r_nota'] - 6.2) * 15))
            m += dn
            if dn <= -5:
                mot.append(f'fase ruim (nota média {j["r_nota"]:.1f})')
            elif dn >= 5:
                mot.append(f'fase boa (nota média {j["r_nota"]:.1f})')
        m += (ppg - 1.5) * 5
        # ego salarial: alguém pior ganha bem mais
        if j['status'] in ('Lenda', 'Ídolo', 'Superastro', 'Craque') and j['salario']:
            pior_rico = [o for o in J if o is not j and o['ovr'] <= j['ovr'] - 3 and o['salario'] >= 1.5 * j['salario']]
            if pior_rico:
                o = max(pior_rico, key=lambda o: o['salario'])
                m -= 8
                mot.append(f'ganha menos que {o["nome"]} (R$ {o["salario"] * SALARIO_X / 1e6:.1f} mi x '
                           f'R$ {j["salario"] * SALARIO_X / 1e6:.1f} mi)')
                ego.setdefault(o['nome'], (o, []))[1].append(j)
        if j['contrato'] and 0 <= dias(j['contrato'], hoje) <= 365 and j['status'] != 'Veterano':
            m -= 6
            mot.append(f'contrato acaba em {j["contrato"][2]:02d}/{j["contrato"][1]:02d}/{j["contrato"][0]}')
        if j['capitao']:
            m += 5
            mot.append('é o capitão')
        if j.get('desempenho'):
            dm, txt = j['desempenho']
            m += dm
            mot.append(txt)
        for dm, motivo in extra.get(j['k'], []):
            m += dm
            mot.append(motivo)
        j['moral'] = round(max(0, min(100, m)))
        j['motivos'] = mot
        j['torcida'] = round(max(0, min(100, 40 + {'Lenda': 30, 'Ídolo': 22, 'Superastro': 15, 'Craque': 8}
                                           .get(j['status'], 0) + min(j['anos'], 10) * 1.5 +
                                           min(j['t_gols'] * 1.5 + j['t_assist'], 15) +
                                           ((j['t_nota'] - 6.2) * 10 if j['t_nota'] else 0))))

    for o, vitimas in ego.values():
        conflitos.append(('Ego salarial', f'{o["nome"]} (nota {o["ovr"]}) ganha R$ {o["salario"] * SALARIO_X / 1e6:.1f} mi '
                                          f'por ano, mais que ' + ', '.join(v['nome'] for v in vitimas) +
                                          ', que têm nota maior', [o] + vitimas))
    # braçadeira
    top = lideres[0]
    if cap and top is not cap and top['lider'] - cap['lider'] >= 8:
        top['moral'] = max(0, top['moral'] - 6)
        top['motivos'].append(f'acha que a braçadeira deveria ser dele (liderança {top["lider"]} x {cap["lider"]})')
        conflitos.append(('Braçadeira', f'{top["nome"]} ({top["status"]}, {top["anos"]:.0f} anos de clube) '
                                        f'contesta a faixa de {cap["nome"]} ({cap["status"]}, {cap["anos"]:.0f} anos)',
                          [top, cap]))
    # disputa de posição: dois de status alto na mesma posição, um sem minutos
    alto = [j for j in J if j['status'] in ('Lenda', 'Ídolo', 'Superastro', 'Craque')]
    for a in alto:
        for b in alto:
            if a['pos'] == b['pos'] and a['ovr'] >= b['ovr'] and a is not b and b['r_jogos_time'] >= 3 and \
                    b['r_min'] < 0.35 * 90 * b['r_jogos_time'] <= a['r_min']:
                conflitos.append(('Posição', f'{b["nome"]} ({b["status"]}) perde espaço para {a["nome"]} na {a["pos"]}',
                                  [b, a]))
    for j in J:
        if j['moral'] < 45:
            conflitos.append(('Insatisfeito', f'{j["nome"]}: ' + '; '.join(j['motivos'][:2]), [j]))
    ultimos = []
    for p in jogos[-6:]:
        casa = p['time1'] == ti
        adv = p['time2'] if casa else p['time1']
        gp, gc = (p['gols1'], p['gols2']) if casa else (p['gols2'], p['gols1'])
        ultimos.append({'data': p['data'], 'casa': casa, 'adversario': s.name(adv), 'pro': gp, 'contra': gc})
    movimentos = []
    try:   # saídas, chegadas e renovações (tabela de transferências do save; saidas.py)
        import saidas
        porK = {j['k']: j for j in J}
        for m in saidas.movimentos(d, ti, fotos, hoje, J):
            m['clube'] = s.name(m['destino']).strip()
            j = porK.get(m['k'])
            if m['tipo'] == 'chegada' and j and abs(dias(tuple(m['data']), tuple(j['chegada']))) > 10:
                m['tipo'] = 'renovacao'   # destino = o próprio clube, mas ele já estava aqui: contrato renovado
            movimentos.append(m)
    except Exception as e:  # noqa: BLE001
        print('aviso: movimentações não lidas:', e)
    return dict(time=s.name(ti).strip(), tecnico=tecnico, ti=ti, hoje=hoje, todas_partidas=todas_partidas, movimentos=movimentos,
                _nomes_time=lambda i: s.name(i).strip(), jogos=jogos, ppg=ppg, J=J, lideres=lideres[:3], capitao=cap,
                conflitos=conflitos, regs=regs, ultimos=ultimos)


def humor(m):
    return 'Motivado' if m >= 80 else 'Satisfeito' if m >= 60 else 'Insatisfeito' if m >= 40 else 'Revoltado'


def relatorio(r):
    L = []
    h = r['hoje']
    L.append(f'VESTIÁRIO — {r["time"]} — {h[2]:02d}/{h[1]:02d}/{h[0]}')
    ult = r['jogos'][-5:]
    L.append(f'Últimos {len(ult)} jogos: {r["ppg"]:.1f} pontos por jogo')
    L.append('')
    L.append(f'{"Jogador":22s} {"Pos":4s} {"Id":>2s} {"Nota":>4s} {"Status":10s} {"Função":14s} {"Casa":>5s} {"Moral":>5s} '
             f'{"Humor":12s} {"Torc.":>5s}  Temporada (J/G/A, nota)')
    for j in sorted(r['J'], key=lambda j: (STATUS_ORDEM.index(j['status']), -j['ovr'])):
        tag = ' (C)' if j['capitao'] else ''
        L.append(f'{(j["nome"] + tag)[:22]:22s} {j["pos"]:4s} {j["idade"]:2d} {j["ovr"]:4d} {j["status"]:10s} {j["funcao"][:14]:14s} '
                 f'{j["anos"]:4.1f}a {j["moral"]:5d} {humor(j["moral"]):12s} {j["torcida"]:5d}  '
                 f'{j["t_jogos"]}/{j["t_gols"]}/{j["t_assist"]}, {j["t_nota"]:.1f}')
    L.append('')
    L.append('Por que cada um está assim:')
    for j in sorted(r['J'], key=lambda j: j['moral']):
        if j['motivos']:
            L.append(f'  {j["nome"]} ({j["moral"]}): ' + '; '.join(j['motivos']))
    L.append('')
    L.append('Liderança (candidatos à braçadeira): ' +
             ', '.join(f'{j["nome"]} {j["lider"]}' for j in r['lideres']) +
             (f' | capitão atual: {r["capitao"]["nome"]} {r["capitao"]["lider"]}' if r['capitao'] else ''))
    L.append('')
    L.append('CONFLITOS:' if r['conflitos'] else 'Sem conflitos no momento.')
    for tipo, txt, _env in r['conflitos']:
        L.append(f'  [{tipo}] {txt}')
    return '\n'.join(L)


def main():
    path = sys.argv[1]
    snap = sys.argv[2] if len(sys.argv) > 2 else SNAP
    r = analisar(carregar(path), snap)
    txt = relatorio(r)
    try:   # atualiza a Central do Técnico com este retrato (só leitura; usa a memória do vestiário se existir)
        import json
        import central_dados
        est = os.path.join(HIST, 'vestiario_estado.json')
        car = next(iter(json.load(open(est, encoding='utf-8'))['carreiras'].values()), {}) if os.path.exists(est) else {}
        central_dados.exportar(r, car)
    except Exception as e:  # noqa: BLE001
        print('aviso: Central não atualizada:', e)
    os.makedirs(HIST, exist_ok=True)
    out = os.path.join(HIST, 'vestiario_' + dt.datetime.now().strftime('%Y%m%d_%H%M%S') + '.txt')
    open(out, 'w', encoding='utf-8').write(txt)
    sys.stdout.reconfigure(encoding='utf-8')
    print(txt)
    print('\nrelatório salvo em', out)


if __name__ == '__main__':
    main()
