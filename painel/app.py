# Mercado IA — autor: William (https://github.com/WilliamProgramadorBR)
"""MERCADO IA — PAINEL (12/10/2026). Aplicativo Qt6 (PySide6) que reúne tudo o que antes ficava espalhado em .bat,
janelas de console e no navegador:

  Início         estado do jogo, do vigia, da Central, do técnico da IA e do duelo; botão Jogar
  Central        a Central do Técnico dentro do app (a mesma página; no celular continua pelo navegador + PIN)
  Rede neural    o duelo estatística x rede: placar das duas arenas, evolução, aprendizado e palpites
  IA adversária  o que o técnico do computador aprendeu contra você e os planos dos últimos jogos
  Configuração   pastas (jogo, saves, pesXdecrypter), verificação do Sider, chave do Gemini, automações
  Registros      o que o vigia e a Central estão fazendo, ao vivo
  Manual         como funciona e como configurar

Os serviços rodam como processos separados (servicos.py); fechar a janela deixa o Painel na bandeja do Windows.
"""
import datetime as dt
import json
import os
import sys
import time
import webbrowser

from PySide6.QtCore import QSize, Qt, QTimer, QUrl
from PySide6.QtGui import QAction, QColor, QFont, QIcon, QPainter, QPixmap, QBrush, QPen
from PySide6.QtNetwork import QLocalServer, QLocalSocket, QNetworkAccessManager, QNetworkRequest
from PySide6.QtWidgets import (QApplication, QCheckBox, QFileDialog, QFrame, QGridLayout, QHBoxLayout, QLabel,
                               QLineEdit, QListWidget, QListWidgetItem, QMainWindow, QMenu, QMessageBox, QPlainTextEdit,
                               QPushButton, QScrollArea, QStackedWidget, QSystemTrayIcon, QTabWidget, QTableWidget,
                               QTableWidgetItem, QTextBrowser, QVBoxLayout, QWidget, QHeaderView, QComboBox)

from painel import base, servicos, sistema, verificar

import caminhos  # noqa: E402  (base.py põe o cerebro no sys.path)

URL_CENTRAL = 'http://127.0.0.1:8765/'
COR = {'fundo': '#0f1512', 'painel': '#151d18', 'linha': '#25322a', 'texto': '#e8efe9', 'mudo': '#8fa396',
       'ouro': '#f5c542', 'azul': '#1d9bf0', 'bom': '#3fb96b', 'aviso': '#e0a030', 'ruim': '#e05a4f'}
QSS = f"""
* {{ font-family: 'Segoe UI'; font-size: 10pt; color: {COR['texto']}; }}
QMainWindow, QWidget#raiz {{ background: {COR['fundo']}; }}
QWidget {{ background: transparent; }}
QListWidget#menu {{ background: {COR['painel']}; border: 0; border-right: 1px solid {COR['linha']}; padding-top: 8px; outline: 0; }}
QListWidget#menu::item {{ padding: 10px 14px; border-radius: 6px; margin: 2px 8px; color: {COR['mudo']}; }}
QListWidget#menu::item:selected {{ background: #1f2b23; color: {COR['texto']}; border-left: 3px solid {COR['ouro']}; }}
QFrame.cartao {{ background: {COR['painel']}; border: 1px solid {COR['linha']}; border-radius: 10px; }}
QLabel.titulo {{ font-size: 17pt; font-weight: 700; }}
QLabel.sub {{ color: {COR['mudo']}; }}
QLabel.h2 {{ font-size: 11pt; font-weight: 700; color: {COR['ouro']}; }}
QPushButton {{ background: #1f2b23; border: 1px solid {COR['linha']}; border-radius: 6px; padding: 7px 14px; }}
QPushButton:hover {{ border-color: {COR['ouro']}; }}
QPushButton:disabled {{ color: #5d6b62; }}
QPushButton#principal {{ background: {COR['ouro']}; color: #1a1406; font-weight: 700; border: 0; padding: 10px 22px; font-size: 11pt; }}
QLineEdit, QComboBox, QPlainTextEdit, QTextBrowser, QTableWidget {{ background: #0b100d; border: 1px solid {COR['linha']}; border-radius: 6px; padding: 5px; selection-background-color: #2c4a36; }}
QHeaderView::section {{ background: {COR['painel']}; border: 0; border-bottom: 1px solid {COR['linha']}; padding: 5px; color: {COR['mudo']}; }}
QTabWidget::pane {{ border: 1px solid {COR['linha']}; border-radius: 6px; }}
QTabBar::tab {{ background: {COR['painel']}; padding: 7px 14px; border: 1px solid {COR['linha']}; border-bottom: 0; }}
QTabBar::tab:selected {{ color: {COR['ouro']}; }}
QScrollArea {{ border: 0; }}
QCheckBox::indicator {{ width: 16px; height: 16px; }}
QScrollBar:vertical {{ background: {COR['fundo']}; width: 10px; margin: 0; }}
QScrollBar:horizontal {{ background: {COR['fundo']}; height: 10px; margin: 0; }}
QScrollBar::handle {{ background: #2c3a31; border-radius: 5px; min-height: 30px; min-width: 30px; }}
QScrollBar::handle:hover {{ background: #3b4d41; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: none; }}
QToolTip {{ background: {COR['painel']}; color: {COR['texto']}; border: 1px solid {COR['linha']}; padding: 4px; }}
"""


def icone_app():
    pm = QPixmap(64, 64)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setBrush(QBrush(QColor('#14532d')))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawRoundedRect(2, 2, 60, 60, 14, 14)
    p.setPen(QPen(QColor(COR['ouro'])))
    f = QFont('Segoe UI', 30, QFont.Weight.Black)
    p.setFont(f)
    p.drawText(pm.rect(), Qt.AlignmentFlag.AlignCenter, 'M')
    p.end()
    return QIcon(pm)


def cartao(*widgets, layout=None):
    f = QFrame()
    f.setProperty('class', 'cartao')
    l = layout or QVBoxLayout()
    l.setContentsMargins(14, 12, 14, 12)
    for w in widgets:
        l.addWidget(w) if isinstance(w, QWidget) else l.addLayout(w)
    f.setLayout(l)
    return f


def rotulo(txt, classe=None, rico=False):
    l = QLabel(txt)
    l.setWordWrap(True)
    if classe:
        l.setProperty('class', classe)
    if rico:
        l.setTextFormat(Qt.TextFormat.RichText)
        l.setOpenExternalLinks(True)
    return l


def ler_json(arq, padrao=None):
    try:
        with open(arq, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return padrao


def mtime_txt(arq):
    try:
        t = os.path.getmtime(arq)
    except OSError:
        return None, None
    seg = time.time() - t
    quando = 'agora' if seg < 60 else f'há {int(seg // 60)} min' if seg < 3600 else f'há {int(seg // 3600)} h' if seg < 86400 else dt.datetime.fromtimestamp(t).strftime('%d/%m %H:%M')
    return seg, quando


# ====================================================================== Início
class PaginaInicio(QWidget):
    def __init__(self, janela):
        super().__init__()
        self.j = janela
        v = QVBoxLayout(self)
        v.setContentsMargins(24, 20, 24, 20)
        v.setSpacing(14)
        topo = QHBoxLayout()
        tt = QVBoxLayout()
        tt.addWidget(rotulo('Mercado IA', 'titulo'))
        tt.addWidget(rotulo('PES 2021 · Master League viva: mercado, vestiário, imprensa, IA adversária e o duelo estatística x rede neural', 'sub'))
        topo.addLayout(tt, 1)
        self.b_jogar = QPushButton('▶  Jogar')
        self.b_jogar.setObjectName('principal')
        self.b_jogar.clicked.connect(self.j.jogar)
        self.b_serv = QPushButton('Ligar serviços')
        self.b_serv.clicked.connect(self.alternar)
        topo.addWidget(self.b_serv)
        topo.addWidget(self.b_jogar)
        v.addLayout(topo)
        self.aviso = rotulo('', rico=True)
        self.aviso.hide()
        v.addWidget(self.aviso)
        g = QGridLayout()
        g.setSpacing(12)
        self.cards = {}
        for i, (k, t) in enumerate([('jogo', 'Jogo'), ('vigia', 'Vigia'), ('central', 'Central do Técnico'),
                                    ('reuniao', 'Última reunião'), ('tecnico', 'Técnico da IA'), ('duelo', 'Duelo estatística x rede')]):
            tit = rotulo(t, 'sub')
            val = rotulo('—')
            val.setStyleSheet('font-size: 13pt; font-weight: 600;')
            det = rotulo('', 'sub')
            self.cards[k] = (val, det)
            g.addWidget(cartao(tit, val, det), i // 3, i % 3)
        v.addLayout(g)
        v.addWidget(rotulo('Dica: feche a janela à vontade — o Painel fica na bandeja (perto do relógio) e os serviços continuam.', 'sub'))
        v.addStretch(1)

    def alternar(self):
        if any(s.querer for s in self.j.serv.s.values()):
            self.j.serv.desligar_tudo()
        else:
            self.j.serv.ligar_tudo()
        self.atualizar()

    def marcar(self, k, valor, detalhe='', cor=None):
        val, det = self.cards[k]
        val.setText(valor)
        val.setStyleSheet(f'font-size: 13pt; font-weight: 600; color: {cor or COR["texto"]};')
        det.setText(detalhe)

    def atualizar(self):
        S = self.j.serv.s
        ligado = any(s.querer for s in S.values())
        self.b_serv.setText('Desligar serviços' if ligado else 'Ligar serviços')
        aberto = sistema.jogo_aberto()
        self.marcar('jogo', 'aberto' if aberto else 'fechado', 'PES2021.exe', COR['bom'] if aberto else COR['mudo'])
        seg, q = mtime_txt(os.path.join(base.HIST, 'vigia_vivo.txt'))
        vivo = S['vigia'].rodando()
        self.marcar('vigia', 'rodando' if vivo else 'parado', f'batimento {q}' if q else 'sem batimento ainda',
                    COR['bom'] if vivo and seg is not None and seg < 60 else COR['aviso'] if vivo else COR['ruim'] if ligado else COR['mudo'])
        c_ok = self.j.central_ok
        self.marcar('central', 'no ar' if c_ok else 'fora do ar', URL_CENTRAL if c_ok else ('iniciando...' if S['central'].rodando() else 'desligada'),
                    COR['bom'] if c_ok else COR['aviso'] if S['central'].rodando() else COR['mudo'])
        est = ler_json(os.path.join(base.HIST, 'vestiario_estado.json'), {}) or {}
        seg, q = mtime_txt(os.path.join(base.HIST, 'vestiario_estado.json'))
        self.marcar('reuniao', q or '—', 'o vestiário, a imprensa e o momento são atualizados a cada save')
        ei = ler_json(os.path.join(base.HIST, 'escalacao_ia.json'), {}) or {}
        u = ei.get('ultima') or {}
        self.marcar('tecnico', f'{u.get("escritas", 0)} escalação(ões)' if u else '—',
                    f'última passada: {u.get("quando", "—")} (data do jogo {"/".join(str(x) for x in (u.get("hoje") or [])[::-1])})' if u else 'roda com o jogo aberto numa carreira')
        try:
            import duelo
            r = duelo.resumo()
            nome = {'estatistica': 'Estatística', 'rede': 'Rede neural'}
            pu, ps_ = r['usuario']['placar'], r['simulados']['placar']
            self.marcar('duelo', f'{nome[r["simulados"]["lider"]]} · {nome[r["usuario"]["lider"]]}',
                        f'jogos da IA: {ps_["estatistica"]} x {ps_["rede"]} ({ps_["jogos"]}/100) · seus jogos: {pu["estatistica"]} x {pu["rede"]} ({pu["jogos"]}/100)')
        except Exception as e:  # noqa: BLE001
            self.marcar('duelo', '—', str(e)[:80])
        erros = [i for i in self.j.verificacao if i.estado == 'erro']
        if erros:
            self.aviso.setText(f'<span style="color:{COR["ruim"]}">⚠ Falta configurar: {", ".join(i.titulo for i in erros)}.</span> '
                               f'<a href="#config" style="color:{COR["ouro"]}">Abrir a Configuração</a>')
            self.aviso.linkActivated.connect(lambda _: self.j.ir('config')) if not self.aviso.property('lig') else None
            self.aviso.setProperty('lig', True)
            self.aviso.show()
        else:
            self.aviso.hide()


# ====================================================================== Central (web)
class PaginaCentral(QWidget):
    def __init__(self, janela):
        super().__init__()
        self.j = janela
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        barra = QHBoxLayout()
        barra.setContentsMargins(12, 8, 12, 8)
        self.info = rotulo('A Central do Técnico dentro do Painel.', 'sub')
        barra.addWidget(self.info, 1)
        b1 = QPushButton('Recarregar')
        b2 = QPushButton('Abrir no navegador')
        b2.clicked.connect(lambda: webbrowser.open(URL_CENTRAL))
        barra.addWidget(b1)
        barra.addWidget(b2)
        v.addLayout(barra)
        self.web = None
        try:
            from PySide6.QtWebEngineWidgets import QWebEngineView
            self.web = QWebEngineView()
            self.web.page().setBackgroundColor(QColor(COR['fundo']))
            self._ligar_notificacoes()
            b1.clicked.connect(self.carregar)
            v.addWidget(self.web, 1)
        except Exception as e:  # noqa: BLE001 - sem o motor web: abre no navegador
            v.addWidget(rotulo(f'O visualizador embutido não está disponível ({e}). Use "Abrir no navegador".'))
            b1.clicked.connect(lambda: webbrowser.open(URL_CENTRAL))
        self.carregou = False

    def _ligar_notificacoes(self):
        """As notificações da Central (sininho) aparecem como aviso do Windows pela bandeja do Painel."""
        from PySide6 import QtWebEngineCore as W
        pg = self.web.page()
        self._ultima_notif = None

        def apresentar(n):
            self._ultima_notif = n
            n.show()
            self.j.bandeja.showMessage(n.title(), n.message(), icone_app(), 8000)
        try:
            pg.profile().setNotificationPresenter(apresentar)
        except Exception:  # noqa: BLE001
            return
        if hasattr(pg, 'permissionRequested'):          # Qt 6.8+
            pg.permissionRequested.connect(lambda p: p.grant() if p.permissionType() == W.QWebEnginePermission.PermissionType.Notifications else None)
        else:
            pg.featurePermissionRequested.connect(lambda url, f: pg.setFeaturePermission(
                url, f, W.QWebEnginePage.PermissionPolicy.PermissionGrantedByUser) if f == W.QWebEnginePage.Feature.Notifications else None)

        def clicou():
            self.j.mostrar()
            self.j.ir('central')
            if self._ultima_notif is not None:
                self._ultima_notif.click()
        self.j.bandeja.messageClicked.connect(clicou)

    def carregar(self):
        if self.web is not None and self.j.central_ok:
            self.web.setUrl(QUrl(URL_CENTRAL))
            self.carregou = True

    def mostrar(self):
        if not self.carregou:
            self.carregar()
        rede = self.j.rede_lan
        if rede and rede.get('rede'):
            self.info.setText(f'No celular (mesma rede Wi-Fi): {rede.get("url", "")} · PIN na página da Central, no PC.')
        elif not self.j.central_ok:
            self.info.setText('A Central ainda não está no ar: ligue os serviços na aba Início.')


# ====================================================================== Rede neural
class PaginaRede(QWidget):
    def __init__(self, janela):
        super().__init__()
        self.j = janela
        area = QScrollArea()
        area.setWidgetResizable(True)
        dentro = QWidget()
        self.v = QVBoxLayout(dentro)
        self.v.setContentsMargins(24, 20, 24, 20)
        self.v.setSpacing(14)
        self.v.addWidget(rotulo('Duelo: estatística x rede neural', 'titulo'))
        self.v.addWidget(rotulo('Bolão a cada jogo: placar exato 3 pontos, saldo certo 2, vencedor certo 1. '
                                'Quem somar mais nos últimos 100 jogos de uma arena passa a decidir: nos jogos da IA, o rodízio de '
                                'titulares; nos seus jogos, o plano tático do adversário. A estatística nunca é apagada: ela segue '
                                'competindo e volta a mandar se passar à frente.', 'sub'))
        linha = QHBoxLayout()
        self.arena = {}
        for a, t in (('usuario', 'Seus jogos'), ('simulados', 'Jogos da IA (simulados)')):
            tit = rotulo(t, 'h2')
            lid = rotulo('')
            lid.setStyleSheet('font-size: 13pt; font-weight: 600;')
            plc = rotulo('')
            det = rotulo('', 'sub')
            self.arena[a] = (lid, plc, det)
            linha.addWidget(cartao(tit, lid, plc, det), 1)
        self.v.addLayout(linha)
        self.grafico = self._grafico()
        self.vazio_g = rotulo('O gráfico aparece quando os primeiros jogos da IA forem pontuados (na próxima rodada de clubes com o jogo aberto).', 'sub')
        if self.grafico is not None:
            self.v.addWidget(cartao(rotulo('Pontos acumulados nos jogos da IA', 'h2'), self.vazio_g, self.grafico))
        self.perdas = self._grafico(altura=200)
        self.vazio_p = rotulo('A curva aparece depois do primeiro treino com jogos novos.', 'sub')
        if self.perdas is not None:
            self.v.addWidget(cartao(rotulo('Aprendizado da rede (perda média a cada treino; quanto mais baixo, melhor ela explica os placares)', 'h2'), self.vazio_p, self.perdas))
        self.tab = QTableWidget(0, 6)
        self.tab.setHorizontalHeaderLabels(['Data', 'Adversário', 'Deu', 'Estatística', 'Rede', 'Plano escolhido por'])
        self.tab.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tab.verticalHeader().hide()
        self.tab.setMinimumHeight(220)
        self.v.addWidget(cartao(rotulo('Palpites nos seus jogos', 'h2'), self.tab))
        bar = QHBoxLayout()
        self.b_estudar = QPushButton('Estudar o histórico do save de novo')
        self.b_estudar.setToolTip('Reaprende do zero com todas as súmulas do save (leva ~1 minuto). O placar do duelo não muda.')
        self.b_estudar.clicked.connect(self.estudar)
        bar.addWidget(self.b_estudar)
        bar.addStretch(1)
        self.v.addLayout(bar)
        self.saida = QPlainTextEdit()
        self.saida.setReadOnly(True)
        self.saida.setMaximumHeight(120)
        self.saida.hide()
        self.v.addWidget(self.saida)
        self.v.addStretch(1)
        area.setWidget(dentro)
        out = QVBoxLayout(self)
        out.setContentsMargins(0, 0, 0, 0)
        out.addWidget(area)
        self.proc = None

    def _grafico(self, altura=260):
        try:
            from PySide6.QtCharts import QChart, QChartView
        except Exception:  # noqa: BLE001
            return None
        ch = QChart()
        ch.setBackgroundBrush(QBrush(QColor(COR['painel'])))
        ch.setPlotAreaBackgroundVisible(False)
        ch.legend().setLabelColor(QColor(COR['texto']))
        ch.setMargins(__import__('PySide6.QtCore', fromlist=['QMargins']).QMargins(4, 4, 4, 4))
        vw = QChartView(ch)
        vw.setRenderHint(QPainter.RenderHint.Antialiasing)
        vw.setMinimumHeight(altura)
        vw.setStyleSheet('background: transparent; border: 0;')
        return vw

    def _series(self, view, series, eixo_x, eixo_y):
        from PySide6.QtCharts import QLineSeries, QValueAxis
        ch = view.chart()
        ch.removeAllSeries()
        for ax in list(ch.axes()):
            ch.removeAxis(ax)
        ax_x, ax_y = QValueAxis(), QValueAxis()
        for ax, t in ((ax_x, eixo_x), (ax_y, eixo_y)):
            ax.setTitleText(t)
            ax.setLabelsColor(QColor(COR['mudo']))
            ax.setTitleBrush(QBrush(QColor(COR['mudo'])))
            ax.setGridLineColor(QColor(COR['linha']))
            ax.setLabelFormat('%d' if ax is ax_x else '%.1f' if eixo_y.startswith('perda') else '%d')
        ch.addAxis(ax_x, Qt.AlignmentFlag.AlignBottom)
        ch.addAxis(ax_y, Qt.AlignmentFlag.AlignLeft)
        mx_x = mx_y = 1
        mn_y = None
        for nome, cor, pts in series:
            s = QLineSeries()
            s.setName(nome)
            pen = QPen(QColor(cor))
            pen.setWidth(2)
            s.setPen(pen)
            for x, y in pts:
                s.append(x, y)
                mx_x, mx_y = max(mx_x, x), max(mx_y, y)
                mn_y = y if mn_y is None else min(mn_y, y)
            ch.addSeries(s)
            s.attachAxis(ax_x)
            s.attachAxis(ax_y)
        ax_x.setRange(0, mx_x)
        ax_x.setTickCount(min(6, int(mx_x) + 1) if mx_x >= 1 else 2)
        ax_y.setRange(min(0, mn_y or 0) if not eixo_y.startswith('perda') else (mn_y or 0) * 0.95, mx_y * 1.05)

    def atualizar(self):
        try:
            import duelo
            e = duelo.estado()
            r = duelo.resumo()
        except Exception as ex:  # noqa: BLE001
            self.arena['usuario'][0].setText(f'indisponível: {ex}')
            return
        nome = {'estatistica': '📊 Estatística', 'rede': '🧠 Rede neural'}
        for a, (lid, plc, det) in self.arena.items():
            x = r[a]
            pl = x['placar']
            lid.setText(f'Decide: {nome[x["lider"]]}')
            plc.setText(f'<span style="color:{COR["ouro"]}">Estatística {pl["estatistica"]}</span> × '
                        f'<span style="color:{COR["azul"]}">{pl["rede"]} Rede</span>')
            plc.setTextFormat(Qt.TextFormat.RichText)
            det.setText(f'{pl["jogos"]} de 100 jogos pontuados · placares exatos {pl["exatos"]["estatistica"]} x {pl["exatos"]["rede"]} · '
                        f'vencedor certo {pl["vencedor"]["estatistica"]} x {pl["vencedor"]["rede"]} · '
                        f'{x["pendentes"]} palpite(s) esperando o jogo'
                        + (''.join(f' · {t["lider"]} assumiu em {"/".join(map(str, t["data"][::-1]))}' for t in x['trocas']) if x['trocas'] else ''))
        hs = e['arenas']['simulados']['hist']
        if self.grafico is not None:
            self.grafico.setVisible(bool(hs))
            self.vazio_g.setVisible(not hs)
            ae = ar = 0
            pe, pr = [(0, 0)], [(0, 0)]
            for i, h in enumerate(hs, 1):
                ae += h['p_est']
                ar += h['p_rede']
                pe.append((i, ae))
                pr.append((i, ar))
            self._series(self.grafico, [('Estatística', COR['ouro'], pe), ('Rede neural', COR['azul'], pr)], 'jogos pontuados', 'pontos')
        if self.perdas is not None:
            ss = []
            for a, cor, t in (('simulados', COR['azul'], 'jogos da IA'), ('usuario', '#9b7bff', 'seus jogos')):
                try:
                    perdas = (getattr(duelo.rede(a), 'extra', None) or {}).get('perdas') or []
                except Exception:  # noqa: BLE001
                    perdas = []
                if perdas:
                    ss.append((t, cor, [(i, p) for i, (_, p) in enumerate(perdas, 1)]))
            self.perdas.setVisible(bool(ss))
            self.vazio_p.setVisible(not ss)
            if ss:
                self._series(self.perdas, ss, 'treinos', 'perda')
        us = list(reversed(e['arenas']['usuario']['hist'][-15:]))
        pend = list(e['arenas']['usuario']['pend'].values())
        linhas = [(p, True) for p in pend] + [(h, False) for h in us]
        self.tab.setRowCount(len(linhas))
        pc = lambda s: f'{s[0]} x {s[1]}' if s else '—'
        for i, (h, futuro) in enumerate(linhas):
            vals = ['/'.join(str(x) for x in (h.get('data') or [])[::-1]), h.get('adv') or '',
                    'a jogar' if futuro else pc(h.get('real')),
                    pc(h.get('est')) + ('' if futuro else f'  (+{h.get("p_est")})'),
                    pc(h.get('rede')) + ('' if futuro else f'  (+{h.get("p_rede")})'),
                    {'estatistica': 'Estatística', 'rede': 'Rede neural'}.get(h.get('decidiu'), '—')]
            for c, v in enumerate(vals):
                it = QTableWidgetItem(v)
                it.setFlags(Qt.ItemFlag.ItemIsEnabled)
                self.tab.setItem(i, c, it)

    def estudar(self):
        if self.proc is not None:
            return
        from PySide6.QtCore import QProcess
        self.saida.clear()
        self.saida.show()
        self.b_estudar.setEnabled(False)
        self.proc = QProcess(self)
        self.proc.setWorkingDirectory(base.CEREBRO)
        self.proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.proc.readyReadStandardOutput.connect(lambda: self.saida.appendPlainText(bytes(self.proc.readAllStandardOutput()).decode('utf-8', 'replace').rstrip()))

        def fim(*_):
            self.proc = None
            self.b_estudar.setEnabled(True)
            import duelo
            duelo._REDES.clear()
            self.atualizar()
        self.proc.finished.connect(fim)
        env = __import__('PySide6.QtCore', fromlist=['QProcessEnvironment']).QProcessEnvironment.systemEnvironment()
        env.insert('PYTHONIOENCODING', 'utf-8')
        env.insert('MERCADO_IA_SEM_JANELA', '1')
        self.proc.setProcessEnvironment(env)
        self.proc.start(base.python_console(), ['-s', os.path.join(base.CEREBRO, 'pretreinar_rede.py')])


# ====================================================================== IA adversária
class PaginaIA(QWidget):
    def __init__(self, janela):
        super().__init__()
        v = QVBoxLayout(self)
        v.setContentsMargins(24, 20, 24, 20)
        v.setSpacing(12)
        v.addWidget(rotulo('IA adversária', 'titulo'))
        v.addWidget(rotulo('Antes de cada jogo seu, o técnico do computador estuda o seu time (olheiro), monta o plano dele dentro do '
                           'estilo do clube e aprende com o resultado. Nada de atributos turbinados: só tática.', 'sub'))
        self.resumo = rotulo('', rico=True)
        v.addWidget(cartao(rotulo('O que ela aprendeu contra você', 'h2'), self.resumo))
        self.tab = QTableWidget(0, 6)
        self.tab.setHorizontalHeaderLabels(['Data', 'Adversário', 'Técnico', 'Plano', 'Instruções', 'Resultado'])
        self.tab.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tab.verticalHeader().hide()
        v.addWidget(cartao(rotulo('Últimos jogos', 'h2'), self.tab), 1)

    def atualizar(self):
        e = ler_json(os.path.join(base.HIST, 'ia_adversaria.json'), {}) or {}
        r = e.get('resumo') or {}
        bom = ', '.join(f'{n} ({m:+.2f})' for n, m, _ in r.get('melhores') or []) or '—'
        ruim = ', '.join(f'{n} ({m:+.2f})' for n, m, _ in r.get('piores') or []) or '—'
        self.resumo.setText(f'{r.get("jogos", 0)} jogo(s) analisado(s).<br><b style="color:{COR["bom"]}">Funciona contra você:</b> {bom}'
                            f'<br><b style="color:{COR["ruim"]}">Não funciona:</b> {ruim}<br>'
                            f'<span style="color:{COR["mudo"]}">(saldo médio de gols a favor do adversário, acima do esperado)</span>')
        reg = list(reversed((e.get('registro') or [])[-25:]))
        self.tab.setRowCount(len(reg))
        for i, x in enumerate(reg):
            pl = x.get('plano') or {}
            plano = (f'{"posse" if pl.get("estilo_ofensivo") else "contra-ataque"}, linha {pl.get("linha_defensiva", "?")}, '
                     f'compactação {pl.get("compactacao", "?")}') if pl else x.get('escolha', '')
            vals = ['/'.join(str(v) for v in (x.get('data') or [])[::-1]), (x.get('adversario') or '').title(), x.get('tecnico') or '',
                    plano, ' · '.join(x.get('instrucoes') or []), (x.get('resultado') or 'a jogar')
                    + (f' ({x["recompensa"]:+.2f})' if 'recompensa' in x else '')]
            for c, v in enumerate(vals):
                it = QTableWidgetItem(v)
                it.setFlags(Qt.ItemFlag.ItemIsEnabled)
                it.setToolTip(x.get('motivo') or '')
                self.tab.setItem(i, c, it)


# ====================================================================== Configuração
class PaginaConfig(QWidget):
    def __init__(self, janela):
        super().__init__()
        self.j = janela
        area = QScrollArea()
        area.setWidgetResizable(True)
        dentro = QWidget()
        v = QVBoxLayout(dentro)
        v.setContentsMargins(24, 20, 24, 20)
        v.setSpacing(14)
        v.addWidget(rotulo('Configuração', 'titulo'))
        v.addWidget(rotulo('O Painel acha quase tudo sozinho. Confira as pastas, rode a verificação e corrija o que estiver em vermelho.', 'sub'))
        cfg = caminhos.config()
        self.campos = {}

        def linha_pasta(chave, titulo, valor, dica, detectar=None, arquivo=False):
            ed = QLineEdit(valor)
            ed.setPlaceholderText(dica)
            h = QHBoxLayout()
            h.addWidget(ed, 1)
            if detectar:
                b = QPushButton('Detectar')
                b.clicked.connect(lambda: detectar(ed))
                h.addWidget(b)
            b = QPushButton('Procurar...')

            def escolher():
                if arquivo:
                    p, _ = QFileDialog.getOpenFileName(self, titulo, ed.text() or base.TOOLS, 'Programas (*.exe)')
                else:
                    p = QFileDialog.getExistingDirectory(self, titulo, ed.text() or base.TOOLS)
                if p:
                    ed.setText(os.path.normpath(p))
            b.clicked.connect(escolher)
            h.addWidget(b)
            self.campos[chave] = ed
            return rotulo(titulo, 'h2'), h

        def det_jogo(ed):
            achados = caminhos.detectar_jogo()
            if achados:
                ed.setText(achados[0])
            else:
                QMessageBox.information(self, 'Pasta do jogo', 'Não achei o PES2021.exe automaticamente. Use "Procurar...".')

        def det_saves(ed):
            ps_ = caminhos.pastas_save()
            ed.setText(ps_[0] if ps_ else caminhos.raiz_saves())

        jogo0 = cfg.get('jogo') or (caminhos.GAME_DIR if os.path.isfile(os.path.join(caminhos.GAME_DIR, 'PES2021.exe'))
                                    else (caminhos.detectar_jogo() or [''])[0])   # 1ª vez: já vem detectado
        t, h = linha_pasta('jogo', 'Pasta do PES 2021 (onde fica o PES2021.exe e o sider.ini)', jogo0, 'ex.: C:\\Games\\eFootball PES 2021', det_jogo)
        v.addWidget(cartao(t, h, rotulo('O Sider é obrigatório: ele carrega o módulo MercadoIA.lua dentro do jogo (foto da memória, overlay e teclas).', 'sub')))
        t, h = linha_pasta('saves', 'Pasta dos saves (…\\KONAMI\\eFootball PES 2021 SEASON UPDATE\\<número>\\save)', cfg.get('saves') or ((caminhos.pastas_save() or [''])[0]), 'detectada automaticamente', det_saves)
        v.addWidget(cartao(t, h))
        t, h = linha_pasta('decrypter_pasta', 'Pasta do pesXdecrypter (decrypter21.exe e encrypter21.exe)', os.path.dirname(cfg.get('decrypter') or caminhos.DECRYPT), '')
        bb = QPushButton('Restaurar a versão oficial')
        bb.setToolTip('O pesXdecrypter já vem no pacote. Use só se os arquivos sumirem ou forem trocados (baixa a 6.0.0 do GitHub e confere).')
        bb.clicked.connect(self.baixar_decrypter)
        h.addWidget(bb)
        v.addWidget(cartao(t, h, rotulo('Ferramenta de terceiros (domínio público) que abre e fecha a criptografia do save. Já vem no pacote, '
                                        'na versão oficial 6.0.0; a verificação confere a impressão digital dos executáveis.', 'sub')))
        t, h = linha_pasta('lancador', 'Como abrir o jogo (opcional)', cfg.get('lancador') or '', 'vazio = WORLD LAUNCHER.exe, sider.exe ou PES2021.exe, nessa ordem', arquivo=True)
        v.addWidget(cartao(t, h))

        # verificação
        self.lista = QListWidget()
        self.lista.setMinimumHeight(250)
        self.lista.itemDoubleClicked.connect(self.corrigir)
        bv = QPushButton('Verificar de novo')
        bv.clicked.connect(self.verificar)
        bc = QPushButton('Corrigir o item selecionado')
        bc.clicked.connect(lambda: self.corrigir(self.lista.currentItem()))
        hb = QHBoxLayout()
        hb.addWidget(bv)
        hb.addWidget(bc)
        hb.addStretch(1)
        v.addWidget(cartao(rotulo('Verificação', 'h2'), self.lista, hb))

        # IA de texto
        ia = verificar.ia_config()
        self.ia_chave = QLineEdit('' if ia.get('chave') in (None, 'COLE_SUA_CHAVE_AQUI') else ia.get('chave'))
        self.ia_chave.setEchoMode(QLineEdit.EchoMode.Password)
        self.ia_chave.setPlaceholderText('cole aqui a chave do Google Gemini (começa com "AIza...")')
        self.ia_modelo = QComboBox()
        self.ia_modelo.setEditable(True)
        for m in dict.fromkeys([ia.get('modelo') or 'gemini-2.5-flash', 'gemini-2.5-flash', 'gemini-2.5-flash-lite', 'gemini-2.5-pro']):
            self.ia_modelo.addItem(m)
        self.ia_ligada = QCheckBox('Usar a IA do Google Gemini para reescrever os textos (jornais, Bola na Mesa, redes)')
        self.ia_ligada.setChecked(bool(ia.get('ligado')))
        ver = QPushButton('Mostrar')
        ver.setCheckable(True)
        ver.toggled.connect(lambda on: self.ia_chave.setEchoMode(QLineEdit.EchoMode.Normal if on else QLineEdit.EchoMode.Password))
        tst = QPushButton('Testar a chave')
        tst.clicked.connect(self.testar_ia)
        h = QHBoxLayout()
        h.addWidget(self.ia_chave, 1)
        h.addWidget(ver)
        h.addWidget(self.ia_modelo)
        h.addWidget(tst)
        v.addWidget(cartao(rotulo('IA de texto — Google Gemini (opcional)', 'h2'), self.ia_ligada, h,
                           rotulo(f'É o <b>Google Gemini</b>. A chave é sua e gratuita para uso pessoal: '
                                  f'<a style="color:{COR["ouro"]}" href="{verificar.GEMINI_CHAVES}">pegar uma chave no Google AI Studio</a>. '
                                  'Ela fica só neste PC (cerebro\\ia.json) e só é enviada ao Google. Sem chave, tudo funciona com os textos prontos.',
                                  'sub', rico=True)))

        # automações
        aut = ler_json(base.ARQ_AUTOMACAO, {}) or {}
        lan = ler_json(base.ARQ_REDE_LAN, {}) or {}
        self.chk = {}
        caixas = []
        for k, t, pad in (('ia_adversaria', 'IA adversária (o adversário estuda você e monta o plano dele)', True),
                          ('tecnico_ia', 'Técnico da IA nos jogos simulados (os clubes escalam os melhores e fazem rodízio)', True),
                          ('vigia_autoreinicio', 'Religar o vigia se ele travar com o jogo aberto', True),
                          ('mercado', 'Mercado de transferências da IA', True),
                          ('vestiario', 'Reunião do vestiário a cada save (moral, imprensa, momento)', True)):
            c = QCheckBox(t)
            c.setChecked(aut.get(k, pad) is not False)
            self.chk[k] = c
            caixas.append(c)
        self.lan = QCheckBox('Abrir a Central no celular pela rede Wi-Fi (protegida por PIN)')
        self.lan.setChecked(bool(lan.get('rede')))
        caixas.append(self.lan)
        v.addWidget(cartao(rotulo('Automações', 'h2'), *caixas))

        sv = QPushButton('Salvar configuração')
        sv.setObjectName('principal')
        sv.clicked.connect(self.salvar)
        hs = QHBoxLayout()
        hs.addStretch(1)
        hs.addWidget(sv)
        v.addLayout(hs)
        v.addStretch(1)
        area.setWidget(dentro)
        out = QVBoxLayout(self)
        out.setContentsMargins(0, 0, 0, 0)
        out.addWidget(area)

    def verificar(self):
        self.j.verificacao = verificar.tudo(self._cfg())
        self.lista.clear()
        simb = {'ok': '✔', 'aviso': '!', 'erro': '✖'}
        cor = {'ok': COR['bom'], 'aviso': COR['aviso'], 'erro': COR['ruim']}
        for i in self.j.verificacao:
            it = QListWidgetItem(f'{simb[i.estado]}  {i.titulo} — {i.detalhe}' + ('   (duplo clique para corrigir)' if i.acao else ''))
            it.setForeground(QColor(cor[i.estado]))
            it.setData(Qt.ItemDataRole.UserRole, i.acao)
            self.lista.addItem(it)

    def _cfg(self):
        c = {}
        for k in ('jogo', 'saves', 'lancador'):
            t = self.campos[k].text().strip()
            if t:
                c[k] = os.path.normpath(t)
        d = self.campos['decrypter_pasta'].text().strip()
        if d:
            c['decrypter'] = os.path.join(d, 'decrypter21.exe')
            c['encrypter'] = os.path.join(d, 'encrypter21.exe')
        return c

    def corrigir(self, it):
        if not it:
            return
        acao = it.data(Qt.ItemDataRole.UserRole)
        jogo = self._cfg().get('jogo') or caminhos.GAME_DIR
        try:
            if acao == 'instalar_modulo':
                if QMessageBox.question(self, 'Instalar no Sider', f'Copiar o MercadoIA.lua para {jogo}\\modules e acrescentar a linha no sider.ini?\n'
                                        'Um backup do sider.ini é guardado antes.') != QMessageBox.StandardButton.Yes:
                    return
                feito = verificar.instalar_modulo(jogo)
                QMessageBox.information(self, 'Sider', 'Pronto: ' + '; '.join(feito) + '.\nVale na próxima vez que o jogo abrir.')
            elif acao == 'baixar_decrypter':
                self.baixar_decrypter()
            elif acao == 'escolher_jogo':
                self.campos['jogo'].setFocus()
            elif acao == 'escolher_saves':
                self.campos['saves'].setFocus()
            elif acao == 'abrir_sider':
                webbrowser.open(verificar.SIDER_PAGINA)
        except Exception as e:  # noqa: BLE001
            QMessageBox.warning(self, 'Não deu certo', str(e))
        self.verificar()

    def baixar_decrypter(self):
        if QMessageBox.question(self, 'pesXdecrypter', 'Baixar de novo a versão oficial 6.0.0 do pesXdecrypter (GitHub, the4chancup) para a pasta do Mercado IA?') != QMessageBox.StandardButton.Yes:
            return
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            pasta = verificar.baixar_decrypter()
            self.campos['decrypter_pasta'].setText(pasta)
            QMessageBox.information(self, 'pesXdecrypter', f'Baixado em {pasta}.')
        except Exception as e:  # noqa: BLE001
            QMessageBox.warning(self, 'pesXdecrypter', f'Não consegui baixar ({e}).\nBaixe manualmente em {verificar.DECRYPTER_PAGINA}')
        finally:
            QApplication.restoreOverrideCursor()
        self.verificar()

    def testar_ia(self):
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            ok, msg = verificar.testar_gemini(self.ia_chave.text().strip(), self.ia_modelo.currentText().strip())
        finally:
            QApplication.restoreOverrideCursor()
        (QMessageBox.information if ok else QMessageBox.warning)(self, 'Google Gemini', msg)

    def salvar(self):
        c = self._cfg()
        caminhos.gravar_config(c)
        verificar.gravar_ia(chave=self.ia_chave.text(), ligado=self.ia_ligada.isChecked(), modelo=self.ia_modelo.currentText().strip())
        aut = ler_json(base.ARQ_AUTOMACAO, {}) or {}
        for k, chk in self.chk.items():
            aut[k] = chk.isChecked()
        with open(base.ARQ_AUTOMACAO, 'w', encoding='utf-8') as f:
            json.dump(aut, f, ensure_ascii=False, indent=2)
        lan = ler_json(base.ARQ_REDE_LAN, None)
        if lan is not None or self.lan.isChecked():
            lan = lan or {}
            lan['rede'] = self.lan.isChecked()
            with open(base.ARQ_REDE_LAN, 'w', encoding='utf-8') as f:
                json.dump(lan, f, ensure_ascii=False)
        self.verificar()
        if any(s.querer for s in self.j.serv.s.values()):
            if QMessageBox.question(self, 'Configuração salva', 'Salvo. Reiniciar o vigia e a Central agora para valer?') == QMessageBox.StandardButton.Yes:
                for s in self.j.serv.s.values():
                    s.reiniciar()
        else:
            QMessageBox.information(self, 'Configuração', 'Configuração salva.')


# ====================================================================== Registros
class PaginaRegistros(QWidget):
    def __init__(self, janela):
        super().__init__()
        self.j = janela
        v = QVBoxLayout(self)
        v.setContentsMargins(24, 20, 24, 20)
        v.addWidget(rotulo('Registros', 'titulo'))
        self.tabs = QTabWidget()
        self.txt = {}
        for n in ('vigia', 'central'):
            t = QPlainTextEdit()
            t.setReadOnly(True)
            t.setMaximumBlockCount(5000)
            t.setFont(QFont('Consolas', 9))
            self.txt[n] = t
            self.tabs.addTab(t, servicos.NOMES[n])
            for linha in janela.serv.s[n].log:
                t.appendPlainText(linha)
            janela.serv.s[n].linha.connect(self._linha)
        self.erros = QPlainTextEdit()
        self.erros.setReadOnly(True)
        self.erros.setFont(QFont('Consolas', 9))
        self.tabs.addTab(self.erros, 'Erros do vigia')
        v.addWidget(self.tabs, 1)
        h = QHBoxLayout()
        for t, f in (('Reiniciar vigia', lambda: janela.serv.s['vigia'].reiniciar()),
                     ('Reiniciar Central', lambda: janela.serv.s['central'].reiniciar()),
                     ('Abrir a pasta de dados', lambda: os.startfile(base.HIST))):
            b = QPushButton(t)
            b.clicked.connect(f)
            h.addWidget(b)
        h.addStretch(1)
        v.addLayout(h)

    def _linha(self, nome, txt):
        self.txt[nome].appendPlainText(txt)

    def atualizar(self):
        try:
            with open(os.path.join(base.HIST, 'vigia_erros.txt'), encoding='utf-8', errors='replace') as f:
                f.seek(max(0, os.path.getsize(f.name) - 60000))
                self.erros.setPlainText(f.read())
        except OSError:
            self.erros.setPlainText('Nenhum erro registrado.')


# ====================================================================== Manual
class PaginaManual(QWidget):
    def __init__(self, janela):
        super().__init__()
        v = QVBoxLayout(self)
        v.setContentsMargins(24, 20, 24, 20)
        t = QTextBrowser()
        t.setOpenExternalLinks(True)
        md = ''
        for c in (os.path.join(base.TOOLS, 'docs', 'MANUAL.md'), os.path.join(base.TOOLS, '..', 'eFootball PES 2021', 'mercado-ia-pes2021', 'docs', 'MANUAL.md')):
            if os.path.isfile(c):
                md = open(c, encoding='utf-8').read()
                break
        t.setMarkdown(md or '# Manual\n\nO manual (docs/MANUAL.md) não foi encontrado no pacote.')
        v.addWidget(t)


# ====================================================================== janela
class Janela(QMainWindow):
    PAGINAS = [('inicio', '🏠  Início', PaginaInicio), ('central', '📋  Central', PaginaCentral), ('rede', '🧠  Rede neural', PaginaRede),
               ('ia', '♟  IA adversária', PaginaIA), ('config', '⚙  Configuração', PaginaConfig),
               ('registros', '📜  Registros', PaginaRegistros), ('manual', '📖  Manual', PaginaManual)]

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f'Mercado IA — Painel {base.VERSAO}')
        self.setWindowIcon(icone_app())
        self.resize(1320, 860)
        self.serv = servicos.Servicos(self)
        self.central_ok = False
        self.rede_lan = None
        self.verificacao = verificar.tudo()
        self.sair_de_verdade = False
        raiz = QWidget()
        raiz.setObjectName('raiz')
        h = QHBoxLayout(raiz)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(0)
        self.menu = QListWidget()
        self.menu.setObjectName('menu')
        self.menu.setFixedWidth(200)
        self.pilha = QStackedWidget()
        self.pag = {}
        for k, t, cls in self.PAGINAS:
            self.menu.addItem(t)
            p = cls(self)
            self.pag[k] = p
            self.pilha.addWidget(p)
        self.menu.currentRowChanged.connect(self._trocou)
        h.addWidget(self.menu)
        h.addWidget(self.pilha, 1)
        self.setCentralWidget(raiz)
        self.net = QNetworkAccessManager(self)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tique)
        self.timer.start(4000)
        self._bandeja()
        self.pag['config'].verificar()
        self.ir('config' if any(i.estado == 'erro' for i in self.verificacao) or not os.path.isfile(caminhos.ARQ_CONFIG) else 'inicio')
        if not any(i.estado == 'erro' for i in self.verificacao) and '--captura' not in sys.argv and '--sem-servicos' not in sys.argv:
            self.serv.ligar_tudo()
        self.tique()

    def ir(self, k):
        self.menu.setCurrentRow([p[0] for p in self.PAGINAS].index(k))

    def _trocou(self, i):
        self.pilha.setCurrentIndex(i)
        k = self.PAGINAS[i][0]
        p = self.pag[k]
        if k == 'central':
            p.mostrar()
        elif hasattr(p, 'atualizar'):
            p.atualizar()

    def tique(self):
        r = self.net.get(QNetworkRequest(QUrl(URL_CENTRAL + 'api/rede')))
        r.setProperty('t0', time.time())

        def resposta():
            ok = r.error() == r.NetworkError.NoError or r.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute) in (200, 401, 403)
            antes = self.central_ok
            self.central_ok = bool(ok)
            if ok:
                try:
                    self.rede_lan = json.loads(bytes(r.readAll()).decode('utf-8') or 'null')
                except ValueError:
                    pass
            r.deleteLater()
            if self.central_ok and not antes and self.pilha.currentWidget() is self.pag['central']:
                self.pag['central'].carregar()
        r.finished.connect(resposta)
        atual = self.PAGINAS[self.menu.currentRow()][0]
        if atual in ('inicio', 'rede', 'ia', 'registros'):
            self.pag[atual].atualizar()

    def jogar(self):
        if any(i.estado == 'erro' for i in self.verificacao):
            QMessageBox.warning(self, 'Falta configurar', 'Corrija os itens em vermelho na Configuração antes de jogar.')
            self.ir('config')
            return
        self.serv.ligar_tudo()
        try:
            exe = sistema.abrir_jogo(caminhos.config().get('jogo') or caminhos.GAME_DIR, caminhos.config().get('lancador'))
            self.bandeja.showMessage('Mercado IA', f'Abrindo o jogo ({os.path.basename(exe)}). Bom jogo!', icone_app(), 4000)
        except Exception as e:  # noqa: BLE001
            QMessageBox.warning(self, 'Abrir o jogo', str(e))

    # ---------------------------------------------------------------- bandeja
    def _bandeja(self):
        self.bandeja = QSystemTrayIcon(icone_app(), self)
        m = QMenu()
        for t, f in (('Abrir o Painel', self.mostrar), ('Jogar', self.jogar), ('Abrir a Central no navegador', lambda: webbrowser.open(URL_CENTRAL))):
            a = QAction(t, m)
            a.triggered.connect(f)
            m.addAction(a)
        m.addSeparator()
        a = QAction('Sair (desliga os serviços)', m)
        a.triggered.connect(self.sair)
        m.addAction(a)
        self.bandeja.setContextMenu(m)
        self.bandeja.setToolTip('Mercado IA')
        self.bandeja.activated.connect(lambda motivo: self.mostrar() if motivo == QSystemTrayIcon.ActivationReason.Trigger else None)
        self.bandeja.show()

    def mostrar(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def closeEvent(self, ev):
        if self.sair_de_verdade or not QSystemTrayIcon.isSystemTrayAvailable():
            self.serv.desligar_tudo()
            ev.accept()
            return
        ev.ignore()
        self.hide()
        if not getattr(self, '_avisou', False):
            self.bandeja.showMessage('Mercado IA', 'O Painel continua na bandeja; os serviços seguem rodando. Botão direito para sair.', icone_app(), 5000)
            self._avisou = True

    def sair(self):
        self.sair_de_verdade = True
        self.close()
        QApplication.quit()


def main():
    os.environ.setdefault('QTWEBENGINE_CHROMIUM_FLAGS', '--disable-gpu-shader-disk-cache')
    app = QApplication(sys.argv)
    app.setApplicationName('Mercado IA')
    app.setQuitOnLastWindowClosed(False)
    app.setStyleSheet(QSS)
    # cópia única: a segunda abertura só traz a janela da primeira para frente
    nome = 'MercadoIA-Painel'
    s = QLocalSocket()
    s.connectToServer(nome)
    if s.waitForConnected(300):
        s.write(b'mostrar')
        s.flush()
        s.waitForBytesWritten(300)
        return 0
    QLocalServer.removeServer(nome)
    srv = QLocalServer()
    srv.listen(nome)
    j = Janela()
    srv.newConnection.connect(lambda: (srv.nextPendingConnection(), j.mostrar()))
    if '--captura' in sys.argv:      # teste visual: grava uma imagem de cada página e sai
        pasta = sys.argv[sys.argv.index('--captura') + 1]
        os.makedirs(pasta, exist_ok=True)
        j.show()

        def fotografar(i=0):
            if i >= len(Janela.PAGINAS):
                j.sair()
                return
            j.menu.setCurrentRow(i)
            QTimer.singleShot(1500, lambda: (j.grab().save(os.path.join(pasta, f'{i}_{Janela.PAGINAS[i][0]}.png')), fotografar(i + 1)))
        QTimer.singleShot(2500, fotografar)
    elif '--minimizado' not in sys.argv:
        j.show()
    return app.exec()


if __name__ == '__main__':
    sys.exit(main())
