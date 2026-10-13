# Mercado IA — autor: William (https://github.com/WilliamProgramadorBR)
"""Consultas rápidas ao Windows sem bibliotecas externas: processos abertos, linha de comando, abrir o jogo."""
import ctypes
import os
import subprocess
from ctypes import wintypes

TH32CS_SNAPPROCESS = 0x2
SEM_JANELA = 0x08000000


class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [('dwSize', wintypes.DWORD), ('cntUsage', wintypes.DWORD), ('th32ProcessID', wintypes.DWORD),
                ('th32DefaultHeapID', ctypes.c_size_t), ('th32ModuleID', wintypes.DWORD), ('cntThreads', wintypes.DWORD),
                ('th32ParentProcessID', wintypes.DWORD), ('pcPriClassBase', ctypes.c_long), ('dwFlags', wintypes.DWORD),
                ('szExeFile', ctypes.c_wchar * 260)]


def processos():
    """{pid: nome do executável} — leva milissegundos (o tasklist leva ~0,3 s)."""
    k = ctypes.windll.kernel32
    k.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    h = k.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    out = {}
    e = PROCESSENTRY32W()
    e.dwSize = ctypes.sizeof(e)
    ok = k.Process32FirstW(h, ctypes.byref(e))
    while ok:
        out[e.th32ProcessID] = e.szExeFile
        ok = k.Process32NextW(h, ctypes.byref(e))
    k.CloseHandle(h)
    return out


def jogo_aberto():
    return any(n.lower() == 'pes2021.exe' for n in processos().values())


def matar_scripts(script):
    """Fecha processos python que estejam rodando `script` (ex.: vigia.py aberto pelo .bat antigo)."""
    cmd = (f"Get-CimInstance Win32_Process -Filter \"Name like 'python%'\" | Where-Object {{ $_.CommandLine -like '*{script}*' }}"
           " | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }")
    try:
        subprocess.run(['powershell', '-NoProfile', '-Command', cmd], capture_output=True, timeout=30, creationflags=SEM_JANELA)
    except Exception:  # noqa: BLE001
        pass


def abrir_jogo(jogo, lancador=None):
    """Abre o jogo pelo lançador configurado (WORLD LAUNCHER do patch, sider.exe...) ou o padrão encontrado."""
    exe = lancador if lancador and os.path.isfile(lancador) else None
    if not exe:
        for n in ('WORLD LAUNCHER.exe', 'sider.exe', 'PES2021.exe'):
            if os.path.isfile(os.path.join(jogo, n)):
                exe = os.path.join(jogo, n)
                break
    if not exe:
        raise FileNotFoundError('nenhum lançador do jogo encontrado')
    os.startfile(exe, cwd=os.path.dirname(exe)) if hasattr(os, 'startfile') else subprocess.Popen([exe])
    if os.path.basename(exe).lower() == 'sider.exe':   # o Sider precisa estar aberto antes do jogo
        import time
        time.sleep(2)
        pes = os.path.join(jogo, 'PES2021.exe')
        if os.path.isfile(pes):
            os.startfile(pes, cwd=jogo)
    return exe
