# Mercado IA — autor: William (https://github.com/WilliamProgramadorBR)
"""Leitura e escrita da tabela de times no save DESCRIPTOGRAFADO da Master League (data.dat).

Formato (igual à cópia da memória, confirmado no save de 2033):
  registro de time a cada 1680 bytes; nome UTF-8 do 1º time em TEAM0_NAME
  nome +0 (70 bytes), sigla +70, elenco +328: 40 pares (u32 registro_ml, u32 id), vaga vazia = (0xFFFF, 0)
  números de camisa: u16[40] em +662 (vaga vazia = 0)
  QUANTIDADE de jogadores: u16 em +1058. O JOGO USA ESTE CONTADOR (entradas além dele são ignoradas).
    Teste de 30/09/2026: mover o par sem atualizar o contador deixou o jogador "sem time".
"""
import struct

STRIDE = 1680
ROSTER = 328
NUMBERS = 662
COUNT = 1058


class SaveML:
    def __init__(self, path):
        self.path = path
        self.d = bytearray(open(path, 'rb').read())
        self.base = self.d.index(b'ARSENAL\x00')  # 1º time da tabela

    def team_addr(self, idx):
        return self.base + idx * STRIDE

    def name(self, idx):
        a = self.team_addr(idx)
        return bytes(self.d[a:a + 70]).split(b'\x00')[0].decode('utf-8', 'replace')

    def count(self, idx):
        return struct.unpack_from('<H', self.d, self.team_addr(idx) + COUNT)[0]

    def squad(self, idx):
        """Elenco válido: só as primeiras `count` entradas (o que o jogo considera)."""
        a = self.team_addr(idx) + ROSTER
        return [struct.unpack_from('<II', self.d, a + i * 8) for i in range(self.count(idx))]

    def numbers(self, idx):
        a = self.team_addr(idx) + NUMBERS
        return list(struct.unpack_from('<40H', self.d, a))

    def find_team(self, name, max_teams=800):
        for i in range(max_teams):
            if self.name(i) == name:
                return i
        return None

    def move_last(self, src, dst, reg, pid):
        """Move o ÚLTIMO jogador do elenco src para a primeira vaga livre de dst (sem reordenar ninguém)."""
        sq_s, sq_d = self.squad(src), self.squad(dst)
        assert sq_s and sq_s[-1] == (reg, pid), f'{(reg, pid)} não é o último de {self.name(src)}'
        assert len(sq_d) < 40, 'destino sem vaga'
        num_s, num_d = self.numbers(src), self.numbers(dst)
        ns, nd = len(sq_s), len(sq_d)
        assert num_s[ns - 1], 'número de camisa da origem fora do esperado'
        assert nd == 0 or num_d[nd - 1], 'números de camisa do destino fora do esperado'
        shirt = num_s[ns - 1]
        used = set(num_d[:nd])
        if shirt in used:
            shirt = next(n for n in range(2, 100) if n not in used)
        a_s, a_d = self.team_addr(src), self.team_addr(dst)
        struct.pack_into('<II', self.d, a_d + ROSTER + nd * 8, reg, pid)
        struct.pack_into('<H', self.d, a_d + NUMBERS + nd * 2, shirt)
        struct.pack_into('<II', self.d, a_s + ROSTER + (ns - 1) * 8, 0xFFFF, 0)
        struct.pack_into('<H', self.d, a_s + NUMBERS + (ns - 1) * 2, 0)
        # contadores (o que o jogo realmente usa); a vaga nd do destino pode ter lixo antigo: foi sobrescrita acima
        struct.pack_into('<H', self.d, a_d + COUNT, nd + 1)
        struct.pack_into('<H', self.d, a_s + COUNT, ns - 1)
        # o que estava depois da última vaga do destino deve ser vazio
        if nd + 1 < 40:
            struct.pack_into('<II', self.d, a_d + ROSTER + (nd + 1) * 8, 0xFFFF, 0)
        return shirt

    def special_regs(self, idx):
        """Registros citados depois do contador (provável capitão/cobradores): u32 em +1076, +1080, +1084."""
        a = self.team_addr(idx)
        return {struct.unpack_from('<I', self.d, a + off)[0] for off in (1076, 1080, 1084)} - {0, 0xFFFF, 0xFFFFFFFF}

    def transfer(self, src, dst, reg, pid):
        """Move (reg, pid) de QUALQUER posição do elenco src para o fim do elenco dst.
        Os jogadores seguintes da origem sobem uma posição (lista e camisas); contadores atualizados."""
        sq_s, sq_d = self.squad(src), self.squad(dst)
        k = sq_s.index((reg, pid))
        ns, nd = len(sq_s), len(sq_d)
        assert nd < 40, 'destino sem vaga'
        assert reg not in self.special_regs(src), 'jogador tem função especial no time de origem (capitão/cobrador?)'
        a_s, a_d = self.team_addr(src), self.team_addr(dst)
        num_s, num_d = self.numbers(src), self.numbers(dst)
        shirt = num_s[k]
        used = set(num_d[:nd])
        if not shirt or shirt in used:
            shirt = next(n for n in range(2, 100) if n not in used)
        # escalações dos dois times acompanham a mudança de índices
        self._fix_lineup_after_add(dst, nd)
        self._fix_lineup_after_remove(src, k)
        # destino: acrescenta no fim
        struct.pack_into('<II', self.d, a_d + ROSTER + nd * 8, reg, pid)
        struct.pack_into('<H', self.d, a_d + NUMBERS + nd * 2, shirt)
        if nd + 1 < 40:
            struct.pack_into('<II', self.d, a_d + ROSTER + (nd + 1) * 8, 0xFFFF, 0)
        struct.pack_into('<H', self.d, a_d + COUNT, nd + 1)
        # origem: remove a posição k e sobe os seguintes
        rest = sq_s[:k] + sq_s[k + 1:]
        nums = num_s[:k] + num_s[k + 1:ns]
        for i in range(40):
            r, p = rest[i] if i < len(rest) else (0xFFFF, 0)
            struct.pack_into('<II', self.d, a_s + ROSTER + i * 8, r, p)
            struct.pack_into('<H', self.d, a_s + NUMBERS + i * 2, nums[i] if i < len(nums) else 0)
        struct.pack_into('<H', self.d, a_s + COUNT, ns - 1)
        return shirt

    # ----- escalações (táticas) -----
    # Uma lista por time, a cada LINEUP_STRIDE bytes, na ordem da tabela de times: índices do elenco
    # (11 titulares na ordem das vagas da formação + banco), terminada em 0xFF. As 3 formações do time
    # ficam antes da lista (PLANS_BEFORE bytes): 11 códigos de posição + 22 bytes de coordenadas.
    LINEUP_STRIDE = 600
    PLANS_BEFORE = 0x1E0

    def lineup_base(self):
        if getattr(self, '_lineup_base', None) is not None:
            return self._lineup_base
        d = self.d
        start = self.base + 730 * STRIDE
        sample = [t for t in range(0, 40) if self.count(t) >= 11]

        def valid(o, t):
            n = self.count(t)
            seg = d[o:o + n + 1]
            return len(seg) == n + 1 and seg[n] == 0xFF and sorted(seg[:n]) == list(range(n))

        n0 = self.count(sample[0])
        for o in range(start, min(len(d), start + 8_000_000)):
            if d[o] < n0 and valid(o - sample[0] * self.LINEUP_STRIDE, sample[0]):
                b = o - sample[0] * self.LINEUP_STRIDE
                ok = sum(valid(b + t * self.LINEUP_STRIDE, t) for t in sample)
                if ok >= 0.8 * len(sample):
                    self._lineup_base = b
                    return b
        raise RuntimeError('listas de escalação não encontradas')

    def lineup(self, idx):
        o = self.lineup_base() + idx * self.LINEUP_STRIDE
        out = []
        while len(out) < 40 and self.d[o + len(out)] != 0xFF:
            out.append(self.d[o + len(out)])
        return out

    def set_lineup(self, idx, order):
        assert sorted(order) == list(range(self.count(idx))), 'escalação precisa ter cada jogador do elenco uma vez'
        o = self.lineup_base() + idx * self.LINEUP_STRIDE
        for i in range(40):
            self.d[o + i] = order[i] if i < len(order) else 0xFF

    # Depois dos 40 índices da lista (mesmo layout no bloco do time do USUÁRIO, ver user_block):
    #   +40..+45 cobradores (6 índices do elenco: faltas/escanteios/pênalti), +46..+48 extras (0xFF = vazio),
    #   +49 CAPITÃO (índice do elenco).
    # CONFIRMADO em 09/10/2026 no time do usuário: trocar o capitão William (índice 4) -> Wallace (6) mudou só
    # esse byte. Nos times da IA o layout é o mesmo (valores coerentes com os elencos).
    TAKERS = 40
    CAPTAIN = 49

    def captain(self, idx):
        return self.d[self.lineup_base() + idx * self.LINEUP_STRIDE + self.CAPTAIN]

    def user_block(self, manager_name):
        """Posição da lista de escalação do time do USUÁRIO (bloco próprio, depois da tabela de 730 listas).

        O time do usuário NÃO usa a lista da tabela geral (lá fica uma cópia velha). O bloco tem as 3 formações,
        a lista (40 bytes), cobradores, capitão em +49 e, em +0x40, o nome do técnico (UTF-8).
        """
        nm = manager_name.encode('utf-8') + b'\x00'
        i = self.d.find(nm, self.lineup_base() + 730 * self.LINEUP_STRIDE)
        if i < 0:
            raise RuntimeError('bloco do técnico não encontrado')
        return i - 0x40

    def formation(self, idx, plan=0):
        """Códigos de posição das 11 vagas (0=GK 1=CB 2=LB 3=RB 4=DMF 5=CMF 6=LMF 7=RMF 8=AMF 9=LWF 10=RWF 11=SS 12=CF)."""
        o = self.lineup_base() + idx * self.LINEUP_STRIDE - self.PLANS_BEFORE + plan * 0xA0
        return list(self.d[o:o + 11])

    def _fix_lineup_after_remove(self, idx, k):
        """Tira o índice k da escalação e renumera os seguintes (o elenco 'subiu' uma posição)."""
        try:
            old = self.lineup(idx)
        except RuntimeError:
            return
        if sorted(old) != list(range(len(old))):
            return  # lista já estava incoerente (o jogo reconstrói)
        new = [i - 1 if i > k else i for i in old if i != k]
        o = self.lineup_base() + idx * self.LINEUP_STRIDE
        for i in range(40):
            self.d[o + i] = new[i] if i < len(new) else 0xFF

    def _fix_lineup_after_add(self, idx, n_before):
        try:
            old = self.lineup(idx)
        except RuntimeError:
            return
        if sorted(old) != list(range(n_before)):
            return
        new = old + [n_before]  # novo jogador entra no fim do banco
        o = self.lineup_base() + idx * self.LINEUP_STRIDE
        for i in range(40):
            self.d[o + i] = new[i] if i < len(new) else 0xFF

    def save(self, path=None):
        open(path or self.path, 'wb').write(self.d)
