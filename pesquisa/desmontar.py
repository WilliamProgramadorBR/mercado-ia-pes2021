"""Desmonta trechos do PES2021.exe direto do arquivo (sem o jogo). Só leitura.
Uso: python desmontar.py <endereço hex> [antes] [depois]   ex.: python desmontar.py 141332E19 120 40
     python desmontar.py funcao <endereço hex>   -> acha o início da função (padding CC antes) e desmonta até o ret"""
import struct
import sys

import capstone

sys.stdout.reconfigure(encoding='utf-8')
EXE = r'F:\Pro Evolution Soccer 2026\eFootball PES 2021\PES2021.exe'
f = open(EXE, 'rb')
mz = f.read(0x1000)
pe = struct.unpack_from('<I', mz, 0x3C)[0]
nsec = struct.unpack_from('<H', mz, pe + 6)[0]
optsz = struct.unpack_from('<H', mz, pe + 20)[0]
BASE = struct.unpack_from('<Q', mz, pe + 24 + 24)[0]
secs = []
for i in range(nsec):
    o = pe + 24 + optsz + 40 * i
    nome = mz[o:o + 8].rstrip(b'\0').decode()
    vsz, va, rsz, raw = struct.unpack_from('<IIII', mz, o + 8)
    secs.append((nome, BASE + va, vsz, raw, rsz))


def ler(va, n):
    for nome, sva, vsz, raw, rsz in secs:
        if sva <= va < sva + vsz:
            f.seek(raw + (va - sva))
            return f.read(n)
    raise ValueError(f'{va:#x} fora das seções')


md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)


def mostrar(ini, fim, marca=None):
    for ins in md.disasm(ler(ini, fim - ini), ini):
        seta = '>>' if marca and ins.address <= marca < ins.address + ins.size else '  '
        print(f'{seta} {ins.address:X}  {ins.mnemonic:8s} {ins.op_str}')


def inicio_funcao(va, limite=0x4000):
    x = ler(va - limite, limite)
    i = x.rfind(b'\xcc\xcc')
    while i > 0 and x[i - 1] == 0xCC:
        i -= 1
    return va - limite + x.rfind(b'\xcc', 0, len(x)) + 1 if i < 0 else va - limite + x.find(b'\xcc\xcc', i) + 2 + len(x[x.find(b'\xcc\xcc', i) + 2:].split(b'\xcc')[0]) * 0


if __name__ == '__main__':
    print('seções:', [(n, hex(v), hex(s)) for n, v, s, _, _ in secs])
    if sys.argv[1] == 'funcao':
        va = int(sys.argv[2], 16)
        x = ler(va - 0x3000, 0x3000)
        j = x.rfind(b'\xcc\xcc\xcc')
        ini = va - 0x3000 + j + 3
        while ler(ini, 1) == b'\xcc':
            ini += 1
        print(f'início provável da função: {ini:X}')
        mostrar(ini, va + int(sys.argv[3], 16) if len(sys.argv) > 3 else va + 0x40, marca=va)
    else:
        va = int(sys.argv[1], 16)
        antes = int(sys.argv[2]) if len(sys.argv) > 2 else 80
        depois = int(sys.argv[3]) if len(sys.argv) > 3 else 40
        mostrar(va - antes, va + depois, marca=va)
