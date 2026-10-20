# Mercado IA — autor: William (https://github.com/WilliamProgramadorBR)
"""ÍCONES E ATALHOS dos aplicativos do Mercado IA (20/10/2026).

Um .bat não aceita ícone; por isso criamos atalhos do Windows (.lnk) numerados, cada um com o seu ícone, ao lado dos
.bat. Mesma identidade do ícone do Painel (quadrado arredondado, dourado #f5c542), uma cor e um desenho por app:
  1 Mercado IA (Painel)      verde, "M" dourado         o app principal: liga tudo e abre o jogo (▶ Jogar)
  2 Jogar direto             verde, "play" dourado      vigia + Central + jogo, sem o Painel
  3 Central do Técnico       azul-noite, prancheta      só a Central no navegador
    Reiniciar vigia          âmbar, seta circular       se o vigia travar (com o jogo aberto)
    Instalar EDIT corrigido  cinza, seta para baixo     ferramenta de uma vez só
Uso (na pasta que tem os .bat):  python empacotar\\icones.py            (ícones em icones\\ e os atalhos)
                                 python empacotar\\icones.py --so-icones
Desenhado com o Qt (PySide6), um desenho por tamanho (16..256 px) para ficar nítido também no tamanho pequeno;
o .ico com vários tamanhos é montado com o Pillow.
"""
import io
import os
import subprocess
import sys

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QGuiApplication, QImage, QLinearGradient, QPainter, QPainterPath, QPen, QPolygonF

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PASTA = os.path.join(RAIZ, 'icones')
TAMANHOS = (16, 24, 32, 48, 64, 128, 256)
OURO, BRANCO = QColor('#f5c542'), QColor('#ffffff')

# (arquivo, nome do atalho, .bat, descrição, cores do fundo (cima, baixo), desenho, janela: 1 normal / 7 minimizada)
APPS = [
    ('mercado_ia', '1. Mercado IA (Painel)', 'ABRIR_PAINEL.bat',
     'O app principal: liga o vigia e a Central e abre o jogo pelo botão Jogar', ('#1f7a43', '#14532d'), 'm', 7),
    ('jogar', '2. Jogar direto (sem o Painel)', 'JOGAR_COM_MERCADO_IA.bat',
     'Abre o vigia, a Central do Técnico e o jogo, sem o Painel', ('#1f7a43', '#14532d'), 'play', 7),
    ('central', '3. Central do Técnico', 'ABRIR_CENTRAL.bat',
     'Abre só a Central do Técnico no navegador', ('#1e3a6e', '#0b1426'), 'prancheta', 7),
    ('vigia', 'Reiniciar vigia (se travar)', 'REINICIAR_VIGIA.bat',
     'Fecha o vigia travado e abre de novo (com o jogo aberto)', ('#d97706', '#92400e'), 'reiniciar', 1),
    ('edit', 'Instalar EDIT corrigido (uma vez só)', 'INSTALAR_EDIT_CORRIGIDO.bat',
     'Instala o EDIT corrigido no save (feche o jogo antes)', ('#64748b', '#334155'), 'instalar', 1),
]


def caneta(cor, w):
    c = QPen(cor, w)
    c.setCapStyle(Qt.PenCapStyle.RoundCap)
    c.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    return c


def _fundo(p, cores):
    g = QLinearGradient(0, 0, 0, 256)
    g.setColorAt(0, QColor(cores[0]))
    g.setColorAt(1, QColor(cores[1]))
    p.setBrush(QBrush(g))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawRoundedRect(QRectF(8, 8, 240, 240), 56, 56)
    p.setBrush(Qt.BrushStyle.NoBrush)   # brilho discreto na borda de cima
    p.setPen(QPen(QColor(255, 255, 255, 40), 6))
    p.drawRoundedRect(QRectF(11, 11, 234, 234), 53, 53)


def _m(p, tam):
    p.setPen(QPen(OURO))
    f = QFont('Segoe UI', 1, QFont.Weight.Black)
    f.setPixelSize(150)
    p.setFont(f)
    p.drawText(QRectF(0, 0, 256, 256), Qt.AlignmentFlag.AlignCenter, 'M')


def _play(p, tam):
    p.setPen(QPen(OURO, 16))
    p.setBrush(Qt.BrushStyle.NoBrush)
    if tam >= 32:
        p.drawEllipse(QPointF(128, 128), 84, 84)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(OURO))
    s = 1.0 if tam >= 32 else 1.35
    p.drawPolygon(QPolygonF([QPointF(128 - 30 * s + 8, 128 - 48 * s), QPointF(128 - 30 * s + 8, 128 + 48 * s),
                             QPointF(128 + 50 * s + 8, 128)]))


def _prancheta(p, tam):
    # campo visto de cima: gramado, linhas brancas e (no tamanho grande) jogadores dourados com uma seta
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(QColor('#1f7a43')))
    campo = QRectF(52, 40, 152, 176) if tam >= 32 else QRectF(44, 36, 168, 184)
    p.drawRoundedRect(campo, 10, 10)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(QPen(BRANCO, 10 if tam >= 32 else 16))
    p.drawRoundedRect(campo.adjusted(12, 12, -12, -12), 4, 4)
    p.drawLine(QPointF(campo.left() + 12, campo.center().y()), QPointF(campo.right() - 12, campo.center().y()))
    if tam >= 32:
        p.drawEllipse(campo.center(), 22, 22)
    if tam >= 48:
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(OURO))
        for x, y in ((96, 170), (160, 170), (128, 196)):
            p.drawEllipse(QPointF(x, y), 11, 11)
        p.setPen(caneta(OURO, 8))
        p.drawLine(QPointF(128, 150), QPointF(128, 92))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawPolygon(QPolygonF([QPointF(112, 98), QPointF(144, 98), QPointF(128, 72)]))


def _reiniciar(p, tam):
    w = 26 if tam >= 32 else 36
    p.setPen(caneta(BRANCO, w))
    p.setBrush(Qt.BrushStyle.NoBrush)
    r = QRectF(60, 60, 136, 136)
    p.drawArc(r, 60 * 16, 290 * 16)            # quase um círculo inteiro, aberto em cima à direita
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(BRANCO))
    k = 1.0 if tam >= 32 else 1.3
    p.drawPolygon(QPolygonF([QPointF(160, 30 + (1 - k) * 20), QPointF(160 + 70 * k, 66), QPointF(150, 104 * k - (k - 1) * 30)]))
    if tam >= 32:
        p.setBrush(QBrush(OURO))
        p.drawEllipse(QPointF(128, 128), 18, 18)


def _instalar(p, tam):
    w = 24 if tam >= 32 else 34
    p.setPen(caneta(BRANCO, w))
    p.drawLine(QPointF(128, 48), QPointF(128, 150))
    path = QPainterPath(QPointF(84, 112))
    path.lineTo(QPointF(128, 156))
    path.lineTo(QPointF(172, 112))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawPath(path)
    p.setPen(caneta(OURO, w))
    tray = QPainterPath(QPointF(60, 168))
    tray.lineTo(QPointF(60, 204))
    tray.lineTo(QPointF(196, 204))
    tray.lineTo(QPointF(196, 168))
    p.drawPath(tray)


DESENHOS = {'m': _m, 'play': _play, 'prancheta': _prancheta, 'reiniciar': _reiniciar, 'instalar': _instalar}


def desenhar(tam, cores, desenho):
    img = QImage(tam, tam, QImage.Format.Format_ARGB32)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
    p.scale(tam / 256, tam / 256)
    _fundo(p, cores)
    DESENHOS[desenho](p, tam)
    p.end()
    return img


def _pil(img):
    from PIL import Image
    from PySide6.QtCore import QBuffer, QIODevice
    buf = QBuffer()
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    img.save(buf, 'PNG')
    return Image.open(io.BytesIO(bytes(buf.data()))).convert('RGBA')


def gerar_icones():
    os.makedirs(PASTA, exist_ok=True)
    feitos = {}
    for nome, _, _, _, cores, desenho, _ in APPS:
        imgs = [_pil(desenhar(t, cores, desenho)) for t in TAMANHOS]
        destino = os.path.join(PASTA, nome + '.ico')
        imgs[-1].save(destino, format='ICO', sizes=[(t, t) for t in TAMANHOS], append_images=imgs[:-1])
        imgs[-1].save(os.path.join(PASTA, nome + '.png'))
        feitos[nome] = destino
    return feitos


def criar_atalhos(icones, pasta=RAIZ):
    """Atalhos .lnk ao lado dos .bat que existirem nesta pasta (WScript.Shell, sem dependência extra)."""
    criados = []
    for nome, titulo, bat, desc, _, _, janela in APPS:
        alvo = os.path.join(pasta, bat)
        if not os.path.isfile(alvo):
            continue
        lnk = os.path.join(pasta, titulo + '.lnk')
        ps = ("$s=(New-Object -ComObject WScript.Shell).CreateShortcut($env:LNK);"
              "$s.TargetPath=$env:ALVO;$s.WorkingDirectory=$env:PASTA;$s.IconLocation=$env:ICONE+',0';"
              "$s.Description=$env:DESC;$s.WindowStyle=[int]$env:JANELA;$s.Save()")
        env = dict(os.environ, LNK=lnk, ALVO=alvo, PASTA=pasta, ICONE=icones[nome], DESC=desc, JANELA=str(janela))
        subprocess.run(['powershell', '-NoProfile', '-Command', ps], env=env, check=True,
                       creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        criados.append(titulo)
    return criados


if __name__ == '__main__':
    app = QGuiApplication.instance() or QGuiApplication(sys.argv[:1])
    ic = gerar_icones()
    print('ícones:', ', '.join(os.path.basename(v) for v in ic.values()), '->', PASTA)
    if '--so-icones' not in sys.argv:
        print('atalhos:', '; '.join(criar_atalhos(ic)) or 'nenhum .bat nesta pasta')
