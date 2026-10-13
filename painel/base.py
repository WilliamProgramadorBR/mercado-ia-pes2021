# Mercado IA — autor: William (https://github.com/WilliamProgramadorBR)
"""Pastas do Painel e do motor (vale no desenvolvimento e no pacote instalado).

Layout do pacote:                       Layout de desenvolvimento:
  MercadoIA\\                              Ferramentas\\
    runtime\\  (Python embutido)             painel\\
    app\\                                    cerebro\\
      painel\\                               ...
      cerebro\\
      sider\\MercadoIA.lua
      config.json
"""
import os
import sys

PAINEL = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.normpath(os.environ.get('MERCADO_IA_TOOLS_DIR') or os.path.join(PAINEL, '..'))
CEREBRO = os.path.join(TOOLS, 'cerebro')
HIST = os.path.join(CEREBRO, 'historico')
ARQ_IA = os.path.join(CEREBRO, 'ia.json')
ARQ_AUTOMACAO = os.path.join(CEREBRO, 'automacao.json')
ARQ_REDE_LAN = os.path.join(HIST, 'central_rede.json')
VERSAO = '0.9.2'


def _modulo_lua():
    for c in (os.path.join(TOOLS, 'sider', 'MercadoIA.lua'),
              os.path.join(TOOLS, '..', 'eFootball PES 2021', 'mercado-ia-pes2021', 'sider', 'MercadoIA.lua')):
        if os.path.isfile(c):
            return os.path.normpath(c)
    return os.path.join(TOOLS, 'sider', 'MercadoIA.lua')


MODULO_LUA = _modulo_lua()

if CEREBRO not in sys.path:      # o Painel usa os módulos do motor (caminhos, duelo...)
    sys.path.insert(0, CEREBRO)
os.makedirs(HIST, exist_ok=True)


def python_console():
    """python.exe ao lado do executável atual (o Painel roda em pythonw.exe; os serviços, em python.exe)."""
    d = os.path.dirname(sys.executable)
    p = os.path.join(d, 'python.exe')
    return p if os.path.isfile(p) else sys.executable
