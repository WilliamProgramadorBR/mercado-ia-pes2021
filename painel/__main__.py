# Mercado IA — autor: William (https://github.com/WilliamProgramadorBR)
"""python -m painel  (ou pythonw -m painel, sem console)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if os.path.isfile(os.path.join(os.path.dirname(sys.executable), f'python{sys.version_info[0]}{sys.version_info[1]}._pth')):
    # no pacote: só os módulos do próprio Mercado IA (nada do Python que o jogador tenha instalado)
    sys.path[:] = [p for p in sys.path if 'site-packages' not in p or p.startswith(os.path.dirname(sys.executable))]

from painel.app import main  # noqa: E402

sys.exit(main())
