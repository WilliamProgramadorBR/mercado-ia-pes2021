# Mercado IA — autor: William (https://github.com/WilliamProgramadorBR)
"""Os serviços do Mercado IA dentro do Painel: vigia (lê os saves e faz as reuniões) e Central (servidor local da
página + técnico da IA + IA adversária). Cada um roda como processo separado (QProcess, sem janela de console), com
o registro guardado para a aba Registros, e volta sozinho se cair (no máximo 5 vezes em 10 minutos).
"""
import collections
import os
import time

from PySide6.QtCore import QObject, QProcess, QProcessEnvironment, QTimer, Signal

from painel import base

SCRIPTS = {'vigia': 'vigia.py', 'central': 'central.py'}
NOMES = {'vigia': 'Vigia (saves e reuniões)', 'central': 'Central do Técnico (servidor)'}


class Servico(QObject):
    linha = Signal(str, str)        # (serviço, texto)
    mudou = Signal(str)

    def __init__(self, nome, parent=None):
        super().__init__(parent)
        self.nome = nome
        self.p = None
        self.log = collections.deque(maxlen=4000)
        self.quedas = collections.deque(maxlen=10)
        self.querer = False                     # o usuário quer o serviço ligado
        self.inicio = None
        self._buf = b''

    def rodando(self):
        return self.p is not None and self.p.state() != QProcess.ProcessState.NotRunning

    def ligar(self):
        self.querer = True
        if self.rodando():
            return
        self._matar_orfaos()
        self.p = QProcess(self)
        env = QProcessEnvironment.systemEnvironment()
        env.insert('PYTHONIOENCODING', 'utf-8')
        env.insert('PYTHONUNBUFFERED', '1')
        env.insert('MERCADO_IA_PAINEL', '1')           # o motor sabe que o Painel cuida dos processos
        env.insert('MERCADO_IA_SEM_JANELA', '1')       # programas auxiliares sem janela piscando
        env.insert('MERCADO_IA_TOOLS_DIR', base.TOOLS)
        env.insert('PYTHONNOUSERSITE', '1')
        self.p.setProcessEnvironment(env)
        self.p.setWorkingDirectory(base.TOOLS)
        self.p.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.p.readyReadStandardOutput.connect(self._ler)
        self.p.finished.connect(self._terminou)
        self.p.start(base.python_console(), ['-s', os.path.join(base.CEREBRO, SCRIPTS[self.nome])])   # -s: só os pacotes do Mercado IA
        self.inicio = time.time()
        self._registrar(f'— {NOMES[self.nome]} iniciado —')
        self.mudou.emit(self.nome)

    def desligar(self):
        self.querer = False
        if self.rodando():
            self.p.kill()
            self.p.waitForFinished(3000)
        self.mudou.emit(self.nome)

    def reiniciar(self):
        self.desligar()
        self.ligar()

    def _matar_orfaos(self):
        """Uma cópia aberta pelo .bat antigo (ou por um Painel que caiu) seguraria a trava de cópia única."""
        from painel import sistema
        sistema.matar_scripts(SCRIPTS[self.nome])

    def _ler(self):
        self._buf += bytes(self.p.readAllStandardOutput())
        *linhas, self._buf = self._buf.split(b'\n')
        for l in linhas:
            self._registrar(l.decode('utf-8', 'replace').rstrip('\r'))

    def _registrar(self, txt):
        txt = f'{time.strftime("%H:%M:%S")}  {txt}' if not txt[:2].isdigit() else txt
        self.log.append(txt)
        self.linha.emit(self.nome, txt)

    def _terminou(self, codigo, _status):
        self._registrar(f'— {NOMES[self.nome]} parou (código {codigo}) —')
        self.mudou.emit(self.nome)
        if self.querer:
            agora = time.time()
            self.quedas.append(agora)
            recentes = [t for t in self.quedas if agora - t < 600]
            if len(recentes) <= 5:
                QTimer.singleShot(3000, self.ligar)
            else:
                self._registrar('— caiu 5 vezes em 10 minutos: não vou religar sozinho (veja os registros) —')
                self.querer = False


class Servicos(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.s = {n: Servico(n, self) for n in SCRIPTS}

    def ligar_tudo(self):
        for s in self.s.values():
            s.ligar()

    def desligar_tudo(self):
        for s in self.s.values():
            s.desligar()
