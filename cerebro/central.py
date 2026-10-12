"""Central do Técnico — servidor local (só no seu PC) para abrir no segundo monitor.

Uso:  python central.py            -> http://127.0.0.1:8765
Etapa 1 (09/10/2026): mostra o retrato do vestiário (historico/central.json, gerado a cada reunião do vestiário),
notícias, pedido pendente e promessas. Não grava nada no jogo nem no save.
Etapa 2: POST /api/responder grava a resposta ao pedido de conversa em vestiario_resposta.txt (o mesmo arquivo
das teclas 1/2/3 do overlay); vale na próxima reunião. Continua sem tocar no save.

Etapa "vida futebolística" 1 (09/10/2026): TEMPO REAL.
  - GET /api/eventos (Server-Sent Events): a página recebe o estado sempre que algo muda (reunião do vestiário,
    ação na Central, efeito escrito no jogo, status do vigia). Sem polling.
  - POST /api/acao {tipo, ...}: ação da Central -> diário (acoes.py). Se mexe numa alavanca do jogo, o efeito é
    escrito na memória do jogo NA HORA (thread de fundo; o resultado chega pela mesma via de eventos).
  - O estado mostrado é a PROJEÇÃO: central.json + eventos que a reunião ainda não consumiu.

Rotas:
  /              página (central/index.html)
  /api/estado    estado projetado (uma vez)
  /api/eventos   o mesmo estado, empurrado a cada mudança (text/event-stream)
  /foto/<id>     foto do jogador (DDS do patch convertido para PNG e guardado em historico/fotos)
"""
import hashlib
import http.server
import json
import os
import socketserver
import sys
import threading
import time
import urllib.parse

import acoes

HERE = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(HERE, 'central')
HIST = os.path.join(HERE, 'historico')
DADOS_FIXO = os.environ.get('CENTRAL_DADOS')   # sandbox de testes: um arquivo só
SAVES = os.path.expandvars(r'%USERPROFILE%\OneDrive\Documentos\KONAMI\eFootball PES 2021 SEASON UPDATE')
ESTADO = os.environ.get('VESTIARIO_ESTADO') or os.path.join(HERE, 'historico', 'vestiario_estado.json')
STATUS_VIGIA = os.path.join(os.path.normpath(os.path.join(HERE, '..', '..', 'eFootball PES 2021')), 'mercado_status.txt')
_trabalhos = {}   # n do evento -> 'escrevendo no jogo' (mostrado na página enquanto a thread trabalha)
CACHE_FOTOS = os.path.join(HERE, 'historico', 'fotos')
GAME_DIR = os.path.normpath(os.path.join(HERE, '..', '..', 'eFootball PES 2021'))
FACES = os.path.join(GAME_DIR, 'GOGOSZ', 'Minifaces', 'common', 'render', 'symbol', 'player')
RESPOSTA = os.path.join(GAME_DIR, 'vestiario_resposta.txt')   # mesmo arquivo das teclas 1/2/3 do overlay
DECISAO = os.path.join(GAME_DIR, 'vestiario_decisao.txt')     # existe enquanto há pedido pendente
RESPOSTA_DIR = os.path.join(GAME_DIR, 'diretoria_resposta.txt')  # resposta à reunião com o presidente (etapa 3a)
PORTA = 8765


def foto_png(pid):
    """Caminho do PNG da foto (converte o DDS do patch na primeira vez). None se não houver foto."""
    if not pid.isdigit():
        return None
    png = os.path.join(CACHE_FOTOS, pid + '.png')
    if os.path.exists(png):
        return png
    for ext in ('.png', '.dds'):
        src = os.path.join(FACES, pid + ext)
        if os.path.exists(src):
            from PIL import Image
            os.makedirs(CACHE_FOTOS, exist_ok=True)
            Image.open(src).convert('RGBA').save(png)
            return png
    return None


_escudos = {'quando': None, 'mapa': {}}


def escudo_png(nome):
    """Escudo oficial do time (arquivo do patch) pelo nome do save. Só serve arquivos do mapa (historico/escudos.json)."""
    import escudos
    try:
        t = os.path.getmtime(escudos.ARQ)
    except OSError:
        return None
    if _escudos['quando'] != t:
        _escudos['mapa'], _escudos['quando'] = escudos.por_nome(_ler_json(escudos.ARQ, {})), t
    arq = _escudos['mapa'].get(nome.strip())
    return os.path.join(escudos.FLAG, arq) if arq else None


def _ler_json(path, padrao):
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return padrao


# ------------------------------------------------------------------ várias carreiras (10/10/2026)
# Cada carreira tem o seu historico/central_<arquivo>.json (ex.: central_ML00000003.json). A Central mostra a carreira
# ATIVA = a do save gravado por último (a que está sendo jogada), ou a escolhida no seletor da página (?carreira=).
def _migrar():
    velho, novo = os.path.join(HIST, 'central.json'), os.path.join(HIST, 'central_ML00000000.json')
    if os.path.exists(velho) and not os.path.exists(novo):
        import shutil
        shutil.copy2(velho, novo)


def carreiras():
    """[{slot, arquivo, time, laboratorio, save_mtime}] das carreiras que já têm dados para a Central."""
    import glob
    if DADOS_FIXO:
        d = _ler_json(DADOS_FIXO, {})
        return [{'slot': d.get('slot', 'ML00000000'), 'arquivo': DADOS_FIXO, 'time': d.get('time'),
                 'laboratorio': d.get('laboratorio', False), 'save_mtime': 0}]
    saves = {os.path.basename(f): os.path.getmtime(f) for f in glob.glob(os.path.join(SAVES, '*', 'save', 'ML0000000?'))}
    out = []
    for f in glob.glob(os.path.join(HIST, 'central_ML*.json')):
        slot = os.path.basename(f)[len('central_'):-len('.json')]
        d = _ler_json(f, {})
        out.append({'slot': slot, 'arquivo': f, 'time': d.get('time'), 'laboratorio': d.get('laboratorio', False),
                    'tecnico': d.get('tecnico'), 'save_mtime': saves.get(slot, 0)})
    return sorted(out, key=lambda c: -c['save_mtime'])


def escolher(slot=None):
    cs = carreiras()
    if not cs:
        return None
    return next((c for c in cs if c['slot'] == slot), cs[0])


def estado_projetado(slot=None):
    c = escolher(slot)
    d = (_ler_json(c['arquivo'], None) if c else None) or {'vazio': True}
    d['carreiras'] = [{k: x[k] for k in ('slot', 'time', 'laboratorio')} for x in carreiras()]
    d['carreira_ativa'] = c['slot'] if c else None
    if not d.get('vazio'):
        d['ultimos_jogos_reuniao'] = d.get('ultimos_jogos') or []
        misturar_pulso(d)
        try:   # coletiva pós-jogo no dia do jogo: nasce do pulso (memória), não espera a reunião (coletiva_viva.py)
            import coletiva_viva
            pulso_d = _ler_json(_pulso_arq(d.get('carreira_ativa') or ''), None)
            viva = coletiva_viva.atual(d, pulso_d, d.get('carreira_ativa'))
            d['coletiva'] = coletiva_viva.escolher(d, viva)
        except Exception as e:  # noqa: BLE001
            print('aviso: coletiva ao vivo:', e, flush=True)
        acoes.projetar(d, _ler_json(ESTADO, {}))
        try:   # imprensa: matérias do banco (pré-jogo, 4 x 4, pós-jogo, temporada, mercado)
            import imprensa_db
            d['imprensa'] = imprensa_db.ultimas(d.get('carreira')) if d.get('carreira') else {}
            import legado
            d['hall'] = legado.hall(d.get('carreira')) if d.get('carreira') else None
        except Exception as e:  # noqa: BLE001
            d['imprensa'] = {}
            print('aviso: imprensa não lida:', e, flush=True)
    for chave, arq in (('resposta_overlay', RESPOSTA), ('resposta_diretoria', RESPOSTA_DIR)):
        try:
            d[chave] = open(arq, encoding='utf-8').read().strip()[:1]
        except OSError:
            d[chave] = ''
    try:
        d['vigia'] = {'texto': open(STATUS_VIGIA, encoding='utf-8').read().strip(),
                      'quando': os.path.getmtime(STATUS_VIGIA)}
    except OSError:
        d['vigia'] = None
    try:   # 11/10/2026: save mais novo que a última reunião = imprensa atrasada; diz se o vigia está vivo
        atraso = c['save_mtime'] - os.path.getmtime(c['arquivo']) if c and c['save_mtime'] else 0
        vivo = time.time() - os.path.getmtime(os.path.join(HIST, 'vigia_vivo.txt')) < 30
        d['atraso'] = {'minutos': round(atraso / 60), 'vigia_vivo': vivo} if atraso > 180 else None
    except OSError:
        d['atraso'] = {'minutos': round(atraso / 60), 'vigia_vivo': False} if atraso > 180 else None
    d['vigia_reinicio'] = dict(_VIGIA_REINICIO) if _VIGIA_REINICIO['n'] else None
    ia = _ler_json(os.path.join(HIST, 'ia_adversaria.json'), {}) or {}
    reg = ia.get('registro') or []
    d['ia_adversaria'] = reg[-1] if reg else None   # como o adversário do próximo jogo foi preparado
    d['ia_adversaria_resumo'] = ia.get('resumo')    # o que a IA já aprendeu sobre o usuário
    d['trabalhando'] = list(_trabalhos.values())
    d['trabalhando_n'] = list(_trabalhos.keys())   # qual resposta está sendo escrita no jogo agora
    return d


def _pulso_arq(slot):
    return os.path.join(HIST, f'pulso_{slot}.json')


def misturar_pulso(d):
    """O pulso ao vivo (pulso.py, memória do jogo) é mais novo que a última reunião: sobrepõe data, jogos, próximo
    jogo, tabela e orçamento. O resto (vestiário, mídia, pedidos) continua vindo da reunião."""
    p = _ler_json(_pulso_arq(d.get('carreira_ativa') or ''), None)
    if not p or not p.get('data_jogo'):
        return d
    import datetime as _dt
    try:
        gerado = _dt.datetime.fromisoformat(d.get('gerado_em', '')).timestamp()
    except ValueError:
        gerado = 0
    if p['quando'] < gerado - 5:
        return d
    d['ao_vivo'] = {'quando': p['quando'], 'data_jogo': p['data_jogo']}
    d['data_jogo'] = p['data_jogo']
    if p.get('ultimos_jogos'):
        d['ultimos_jogos'] = p['ultimos_jogos']
    if p.get('classificacao'):
        if d.get('diretoria') is not None:
            d['diretoria']['tabela'] = p['classificacao']
        if d.get('liga'):
            d['liga']['classificacao'] = p['classificacao']
    if p.get('resultados_liga') and d.get('liga'):
        d['liga']['resultados'] = p['resultados_liga']
    if p.get('orcamento') is not None and d.get('diretoria') is not None:
        d['diretoria']['orcamento_atual'] = p['orcamento']
    pj, pr = d.get('proximo_jogo') or {}, p.get('proximo')
    if pr and (pj.get('data') != pr['data'] or pj.get('casa') != pr['casa'] or pj.get('fora') != pr['fora']):
        # a reunião já deixou pronta a prévia desse jogo? (próximos 3 do calendário)
        pronta = next((x for x in d.get('proximos') or [] if x.get('data') == pr['data'] and x.get('casa') == pr['casa']
                       and x.get('fora') == pr['fora']), None)
        if pronta:
            d['proximo_jogo'] = pronta
            return d
        from proximo_jogo import nome_comp
        d['proximo_jogo'] = {'parcial': True, 'data': pr['data'], 'casa': pr['casa'], 'fora': pr['fora'], 'final': pr.get('final'),
                             'competicao': nome_comp(pr['comp']), 'rodada': pr['rodada'],
                             'tabela': {'casa': next((t for t in p.get('classificacao') or [] if t['time'] == pr['casa']), None),
                                        'fora': next((t for t in p.get('classificacao') or [] if t['time'] == pr['fora']), None)}}
    return d


def _pulso_thread():
    import pulso

    def atual():
        c = escolher()
        if not c:
            return None, None
        d = _ler_json(c['arquivo'], {})
        return c['slot'], (d.get('diretoria') or {}).get('orcamento_atual')
    pulso.laco(atual, log=lambda m: print(m, flush=True))


def versao(slot=None):
    """Muda sempre que alguma fonte do estado muda (barato: só datas/tamanhos de arquivo)."""
    c = escolher(slot)
    partes = [c['slot'] if c else '-', ','.join(x['slot'] for x in carreiras()), str(c['save_mtime'] if c else 0)]
    try:
        partes.append(str(time.time() - os.path.getmtime(os.path.join(HIST, 'vigia_vivo.txt')) < 30))
    except OSError:
        partes.append('sem vigia')
    import imprensa_db
    for p in ((c['arquivo'] if c else ''), (_pulso_arq(c['slot']) if c else ''), ESTADO, acoes.DIARIO, STATUS_VIGIA, RESPOSTA, RESPOSTA_DIR,
              imprensa_db.ARQ):
        try:
            st = os.stat(p)
            partes.append(f'{st.st_mtime_ns}:{st.st_size}')
        except OSError:
            partes.append('-')
    partes.append(','.join(sorted(_trabalhos.values())))
    return hashlib.md5('|'.join(partes).encode()).hexdigest()


def _efeito_em_fundo(ev, slot):
    """Escreve no jogo o que a ação mudou (ex.: seta pela moral). Pode levar ~35 s (varredura da memória)."""
    _trabalhos[ev['n']] = 'Escrevendo no jogo: ' + ev.get('texto_resposta', ev['tipo'])[:60]
    try:
        acoes.efeitos_ao_vivo(ev, estado_projetado(slot), log=lambda m: print(m, flush=True))
    except Exception as e:  # noqa: BLE001
        acoes.registrar({'tipo': 'ao_vivo_erro', 'carreira': ev.get('carreira'), 'ref': ev['n'], 'erro': str(e)})
    finally:
        _trabalhos.pop(ev['n'], None)


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):   # silencioso
        pass

    def _send(self, code, body, ctype):
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Cache-Control', 'no-store' if ctype.startswith('application/json') else 'max-age=3600')
        self.end_headers()
        self.wfile.write(body)

    def _slot(self):
        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        v = (q.get('carreira') or [''])[0]
        return v if v.startswith('ML') and v[2:].isdigit() else None

    def _ok_rede(self):
        import central_rede
        return central_rede.autorizado(self.client_address[0], self.headers.get('Cookie'))

    def do_GET(self):
        path = self.path.split('?')[0]
        try:
            if not self._ok_rede():   # aparelho da rede sem o PIN: só a tela do PIN (central_rede.py)
                import central_rede
                if path in ('/', '/index.html'):
                    return self._send(200, central_rede.PAGINA_PIN.encode('utf-8'), 'text/html; charset=utf-8')
                return self._send(401, b'PIN', 'text/plain')
            if path == '/api/rede':   # endereço + PIN para o rodapé: só para o próprio PC
                import central_rede
                if not central_rede.eh_local(self.client_address[0]):
                    return self._send(403, b'', 'text/plain')
                c = central_rede.config()
                return self._send(200, json.dumps({'rede': bool(c.get('rede')), 'pin': c['pin'],
                                                   'url': f'http://{central_rede.ip_local()}:{self.server.server_address[1]}'}).encode('utf-8'),
                                  'application/json; charset=utf-8')
            if path in ('/', '/index.html'):
                with open(os.path.join(WEB, 'index.html'), 'rb') as f:
                    return self._send(200, f.read(), 'text/html; charset=utf-8')
            if path == '/api/estado':
                return self._send(200, json.dumps(estado_projetado(self._slot()), ensure_ascii=False).encode('utf-8'),
                                  'application/json; charset=utf-8')
            if path == '/api/eventos':
                return self._eventos()
            if path.startswith('/escudo/'):
                png = escudo_png(urllib.parse.unquote(path[len('/escudo/'):]))
                if png:
                    with open(png, 'rb') as f:
                        return self._send(200, f.read(), 'image/png')
                return self._send(404, b'', 'text/plain')
            if path.startswith('/foto/'):
                png = foto_png(path[len('/foto/'):].replace('.png', ''))
                if png:
                    with open(png, 'rb') as f:
                        return self._send(200, f.read(), 'image/png')
                return self._send(404, b'', 'text/plain')
            return self._send(404, b'nao encontrado', 'text/plain')
        except Exception as e:  # noqa: BLE001 - a Central nunca derruba nada
            return self._send(500, str(e).encode('utf-8'), 'text/plain; charset=utf-8')

    def _eventos(self):
        """Server-Sent Events: manda o estado projetado quando a versão muda; comentário a cada 15 s (mantém viva)."""
        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream; charset=utf-8')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Connection', 'keep-alive')
        self.end_headers()
        ultima, pulso = None, 0.0
        slot = self._slot()
        try:
            while True:
                v = versao(slot)
                if v != ultima:
                    corpo = json.dumps(estado_projetado(slot), ensure_ascii=False)
                    self.wfile.write(f'event: estado\ndata: {corpo}\n\n'.encode('utf-8'))
                    self.wfile.flush()
                    ultima, pulso = v, time.time()
                elif time.time() - pulso > 15:
                    self.wfile.write(b': pulso\n\n')
                    self.wfile.flush()
                    pulso = time.time()
                time.sleep(0.7)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError):
            return

    def _origem_ok(self):
        """Só aceita chamadas da própria página (cabeçalho X-Central); um site qualquer aberto no navegador não
        consegue enviar esse cabeçalho sem permissão (CORS), e aqui não damos permissão. No PC: Host local. No celular
        (12/10/2026): aparelho da rede que já passou pelo PIN."""
        porta = self.server.server_address[1]
        if self.headers.get('X-Central') != '1':
            return False
        if self.headers.get('Host') in (f'127.0.0.1:{porta}', f'localhost:{porta}'):
            return True
        import central_rede
        return not central_rede.eh_local(self.client_address[0]) and self._ok_rede()

    def _corpo(self):
        n = int(self.headers.get('Content-Length') or 0)
        return json.loads(self.rfile.read(min(n, 4000)) or b'{}')

    def do_POST(self):
        path = self.path.split('?')[0]
        if path == '/api/pin':   # tela do PIN (central_rede.py)
            import central_rede
            if self.headers.get('X-Central') != '1':
                return self._send(403, b'proibido', 'text/plain')
            ok, msg = central_rede.tentar_pin(self.client_address[0], (self._corpo() or {}).get('pin', ''))
            if not ok:
                return self._send(403, msg.encode('utf-8'), 'text/plain; charset=utf-8')
            self.send_response(200)
            self.send_header('Set-Cookie', f'cpin={central_rede.token()}; Path=/; Max-Age=31536000; HttpOnly; SameSite=Strict')
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'ok')
            return None
        if not self._ok_rede():
            return self._send(401, b'PIN', 'text/plain')
        if path == '/api/acao':
            return self._acao()
        return self._responder(path)

    def _acao(self):
        """Ação genérica da Central -> diário; efeito no jogo em segundo plano."""
        try:
            if not self._origem_ok():
                return self._send(403, b'proibido', 'text/plain')
            corpo = self._corpo()
            f = acoes.ACOES.get(corpo.get('tipo'))
            if not f:
                return self._send(400, 'ação desconhecida'.encode('utf-8'), 'text/plain; charset=utf-8')
            c = escolher(corpo.get('slot'))
            # o mesmo estado que a página mostra (inclui a coletiva ao vivo do pulso e a data real do jogo)
            d = estado_projetado(c['slot']) if c else {}
            if d.get('laboratorio'):
                raise acoes.Recusada('carreira de laboratório (teste): a Central só mostra, não escreve nada no jogo')
            ev = f(corpo, d)
            threading.Thread(target=_efeito_em_fundo, args=(ev, c['slot']), daemon=True).start()
            return self._send(200, json.dumps({'ok': True, 'evento': ev['n']}).encode('utf-8'),
                              'application/json; charset=utf-8')
        except acoes.Recusada as e:
            return self._send(409, str(e).encode('utf-8'), 'text/plain; charset=utf-8')
        except Exception as e:  # noqa: BLE001
            return self._send(500, str(e).encode('utf-8'), 'text/plain; charset=utf-8')

    def _responder(self, path):
        """Etapa 2: resposta ao pedido de conversa (grava o MESMO arquivo que as teclas 1/2/3 do overlay)."""
        try:
            if path != '/api/responder':
                return self._send(404, b'', 'text/plain')
            if not self._origem_ok():
                return self._send(403, b'proibido', 'text/plain')
            corpo = self._corpo()
            opcao = str(corpo.get('opcao', ''))
            if opcao not in ('1', '2', '3'):
                return self._send(400, b'opcao invalida', 'text/plain')
            c = escolher(corpo.get('slot'))
            d = _ler_json(c['arquivo'], {}) if c else {}
            if d.get('laboratorio'):
                return self._send(409, 'carreira de laboratório: só leitura'.encode('utf-8'), 'text/plain; charset=utf-8')
            if corpo.get('canal') == 'diretoria':
                p = (d.get('diretoria') or {}).get('reuniao')
                destino = RESPOSTA_DIR
                pendente = bool(p and p.get('opcoes'))
            else:
                p = d.get('pedido')
                destino = RESPOSTA
                pendente = bool(p) and os.path.exists(DECISAO)
            if not pendente or corpo.get('pedido') != p.get('id'):
                return self._send(409, 'não há pedido pendente (ou ele mudou)'.encode('utf-8'), 'text/plain; charset=utf-8')
            tmp = destino + '.tmp'
            with open(tmp, 'w', encoding='utf-8') as f:
                f.write(opcao + '\n')
            os.replace(tmp, destino)
            return self._send(200, json.dumps({'ok': True, 'opcao': opcao}).encode('utf-8'),
                              'application/json; charset=utf-8')
        except Exception as e:  # noqa: BLE001
            return self._send(500, str(e).encode('utf-8'), 'text/plain; charset=utf-8')


def _preparar_adversario(slot, pr):
    """12/10/2026: o técnico da IA prepara o próximo adversário (ia_adversaria.py): escreve o plano de jogo dele na
    memória e devolve o anterior ao plano original. Desliga com "ia_adversaria": false no automacao.json."""
    try:
        if _ler_json(os.path.join(HERE, 'automacao.json'), {}).get('ia_adversaria', True) is False:
            return
        import glob
        import carreira
        import ia_adversaria
        from save_ml import SaveML
        dados = estado_projetado(slot)
        if dados.get('laboratorio'):
            return
        decs = glob.glob(os.path.join(HERE, '..', 'save_work', 'vestiario_*', 'dec', 'data.dat'))
        if not decs:
            return
        d = open(max(decs, key=os.path.getmtime), 'rb').read()
        _, nome = carreira.time_do_usuario(d)
        if nome not in (pr['casa'], pr['fora']):   # o save da última reunião é de outra carreira
            return
        adv = pr['fora'] if pr['casa'] == nome else pr['casa']
        s = SaveML.__new__(SaveML)
        s.path, s.d, s.base = None, bytearray(d), d.index(b'ARSENAL\x00')
        ti = s.find_team(adv)
        if ti is None:
            return
        import dados as _dados
        import olheiro
        try:
            P = _dados.load_players(os.path.join(HERE, '..', '..', 'eFootball PES 2021', 'mercado_snap.bin'))
        except Exception:  # noqa: BLE001
            P = {}
        olho = olheiro.perfil(d, dados, P, s.squad(s.find_team(nome)))
        ia_adversaria.preparar(d, ti, adv, ia_adversaria.contexto(dados, pr), olho=olho, P=P,
                               resultados=dados.get('ultimos_jogos'), escrever_de_verdade=True,
                               log=lambda m: print(time.strftime('%H:%M:%S'), m, flush=True))
    except Exception as e:  # noqa: BLE001 - nunca derruba a Central
        print('aviso: IA adversária:', e, flush=True)


def _imprensa_viva_thread():
    """Pós-jogo ao vivo: quando o pulso mostra um jogo novo nosso, escreve a matéria sem esperar o save/reunião."""
    import imprensa
    feito = feito_pre = None
    while True:
        try:
            c = escolher()
            if c:
                p = _ler_json(_pulso_arq(c['slot']), None)
                uj = (p or {}).get('ultimo_jogo') or {}
                marca = (c['slot'], uj.get('num'), tuple(uj.get('data') or ()))
                pr = (p or {}).get('proximo') or {}
                marca_pre = (c['slot'], tuple(pr.get('data') or ()), pr.get('casa'), pr.get('fora'))
                snap = os.path.join(HERE, '..', '..', 'eFootball PES 2021', 'mercado_snap.bin')
                log = lambda m: print(m, flush=True)
                if uj.get('linhas') and marca != feito:
                    aux = _ler_json(os.path.join(HIST, f'pulso_aux_{c["slot"]}.json'), None)
                    if aux:
                        feito = marca   # marca antes: se falhar, não fica repetindo a cada 10 s
                        d = estado_projetado(c['slot'])
                        imprensa.pos_jogo_vivo(d, p, aux, snap, log=log)
                        import bola_na_mesa   # Bola na Mesa + redes do PÓS-JOGO, sem esperar o save
                        bola_na_mesa.vivo(d, p, snap, 'pos', log=log)
                if pr and marca_pre != feito_pre:   # o próximo jogo mudou: edição PRÉ-JOGO
                    feito_pre = marca_pre
                    threading.Thread(target=_preparar_adversario, args=(c['slot'], pr), daemon=True).start()
                    import bola_na_mesa
                    bola_na_mesa.vivo(estado_projetado(c['slot']), p, snap, 'pre', log=log)
        except Exception as e:  # noqa: BLE001 - nunca derruba a Central
            print('aviso: imprensa ao vivo:', e, flush=True)
        time.sleep(10)


VIGIA_PARADO = 180   # s sem batimento com o jogo aberto = vigia travado ou fechado (a foto da memória leva ~5 s)
_VIGIA_REINICIO = {'quando': 0, 'n': 0}


def _jogo_aberto():
    import subprocess
    r = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq PES2021.exe', '/NH'], capture_output=True, text=True,
                       creationflags=0x08000000)   # sem janela
    return 'PES2021.exe' in r.stdout


def _reiniciar_vigia():
    """O mesmo que o REINICIAR_VIGIA.bat: fecha o vigia travado (a trava de cópia única impediria o novo) e abre outro,
    minimizado. Ao abrir, ele recupera sozinho o save que ficou sem reunião."""
    import subprocess
    subprocess.run(['powershell', '-NoProfile', '-Command',
                    "Get-CimInstance Win32_Process -Filter \"Name like 'python%'\" | Where-Object { $_.CommandLine -like '*vigia.py*' }"
                    " | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"], capture_output=True, timeout=60, creationflags=0x08000000)
    si = subprocess.STARTUPINFO()
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    si.wShowWindow = 7   # minimizada, sem roubar o foco do jogo
    subprocess.Popen([sys.executable, os.path.join(HERE, 'vigia.py')], cwd=os.path.dirname(HERE),
                     creationflags=subprocess.CREATE_NEW_CONSOLE, startupinfo=si)


def _guarda_vigia_thread():
    """12/10/2026: com o jogo aberto e o vigia sem batimento há 3 min (travou, fechou ou o jogo foi aberto sem o .bat),
    a Central reinicia o vigia sozinha. No máximo 1 vez a cada 5 min; desliga com "vigia_autoreinicio": false no
    automacao.json."""
    while True:
        time.sleep(30)
        try:
            if _ler_json(os.path.join(HERE, 'automacao.json'), {}).get('vigia_autoreinicio', True) is False:
                continue
            try:
                parado = time.time() - os.path.getmtime(os.path.join(HIST, 'vigia_vivo.txt'))
            except OSError:
                parado = float('inf')
            if parado < VIGIA_PARADO or time.time() - _VIGIA_REINICIO['quando'] < 300 or not _jogo_aberto():
                continue
            _VIGIA_REINICIO.update(quando=time.time(), n=_VIGIA_REINICIO['n'] + 1)
            print(time.strftime('%H:%M:%S'), f'vigia sem batimento há {round(min(parado, 99999))} s com o jogo aberto: reiniciando', flush=True)
            _reiniciar_vigia()
            with open(os.path.join(HIST, 'vigia_erros.txt'), 'a', encoding='utf-8') as f:
                f.write(f'{time.strftime("%Y-%m-%d %H:%M:%S")} [central] vigia reiniciado automaticamente '
                        f'(sem batimento há {round(min(parado, 99999))} s)\n')
        except Exception as e:  # noqa: BLE001 - nunca derruba a Central
            print('aviso: guarda do vigia:', e, flush=True)


def main():
    porta = int(sys.argv[1]) if len(sys.argv) > 1 else PORTA
    _migrar()
    if not DADOS_FIXO:   # pulso ao vivo (memória do jogo) só na Central de verdade, não no sandbox de testes
        threading.Thread(target=_pulso_thread, daemon=True).start()
        threading.Thread(target=_imprensa_viva_thread, daemon=True).start()
        threading.Thread(target=_guarda_vigia_thread, daemon=True).start()
    socketserver.ThreadingTCPServer.allow_reuse_address = True
    socketserver.ThreadingTCPServer.daemon_threads = True   # conexões de eventos não seguram o fechamento
    import central_rede
    rede = bool(central_rede.config().get('rede')) and not DADOS_FIXO   # 12/10/2026: celular na rede de casa, com PIN
    with socketserver.ThreadingTCPServer(('0.0.0.0' if rede else '127.0.0.1', porta), Handler) as srv:
        print(f'Central do Técnico em http://127.0.0.1:{porta}  (feche esta janela para desligar)', flush=True)
        if rede:
            c = central_rede.config()
            print(f'No celular (mesmo Wi-Fi): http://{central_rede.ip_local()}:{porta}   PIN {c["pin"]}', flush=True)
        srv.serve_forever()


if __name__ == '__main__':
    import unica
    unica.garantir('central')   # só uma cópia rodando (o .bat aberto duas vezes duplicava tudo)
    main()
