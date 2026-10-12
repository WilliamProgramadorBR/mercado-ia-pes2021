"""Leitura do estado de uma Master League do PES 2021 (qualquer save).

Fontes:
  - ml_snap_N.bin : foto da memória feita pelo ML_Scanner (tecla 7). Contém as fichas de jogador
                    da carreira (380 bytes cada) com os atributos ATUAIS.
  - ml_teams_N.txt: elencos de todos os times (ML_Scanner, tecla 8).

Formato da ficha (descoberto comparando a cópia base da memória com o EDIT, acerto de 100%):
  +4  u32 0xFFFFFFFF, +8 u32 0, +12 data (u16 ano, u8 mês, u8 dia)
  +124 u32 registro na ML (0x40A90000 = cópia base, não é jogador da carreira)
  +128 u32 id do jogador, +136 nome UTF-8
  bits a partir do início da ficha (little-endian): ver FIELDS / STYLE / SKILL_BITS
"""
import re
import struct
from dataclasses import dataclass, field

SNAP_BASE = 0x7FF4D7E00000
REC_LEN = 380
BASE_COPY_REG = 0x40A90000

FIELDS = {
    'atk': (664, 7), 'ball_ctrl': (693, 7), 'tight_pos': (704, 7), 'lowpass': (718, 7), 'loftpass': (725, 7),
    'finish': (711, 7), 'place_kick': (757, 7), 'curl': (768, 7), 'speed': (807, 7), 'accel': (839, 7),
    'jump': (846, 7), 'phys_cont': (814, 7), 'balance': (821, 7), 'stamina': (853, 7), 'ball_win': (743, 7),
    'aggres': (750, 7), 'gk': (679, 7), 'catching': (775, 7), 'gk_reach': (800, 7), 'def': (672, 7),
    'clearing': (782, 7), 'header': (736, 7), 'drib': (686, 7), 'reflex': (789, 7), 'kick_pwr': (832, 7),
    'age': (864, 6), 'reg_pos': (700, 4), 'weak_use': (920, 2), 'weak_acc': (916, 2), 'form': (828, 3),
    'injury': (918, 2), 'star': (860, 3), 'height': (640, 8), 'weight': (648, 8),
    'pp_GK': (914, 2), 'pp_CB': (908, 2), 'pp_LB': (910, 2), 'pp_RB': (912, 2), 'pp_DMF': (900, 2),
    'pp_CMF': (902, 2), 'pp_LMF': (904, 2), 'pp_RMF': (906, 2), 'pp_AMF': (898, 2), 'pp_LWF': (893, 2),
    'pp_RWF': (896, 2), 'pp_SS': (891, 2), 'pp_CF': (889, 2),
}
# estilo de jogo: 5 bits no bit 875, numeração interna -> numeração do EDIT/4ccEditor
STYLE_BIT = 875
STYLE_MAP = {0: 0, 1: 1, 2: 2, 3: 3, 4: 6, 5: 9, 6: 10, 7: 11, 8: 14, 9: 12, 10: 19, 11: 15, 12: 17, 13: 4,
             14: 5, 15: 18, 16: 20, 17: 21, 18: 7, 19: 8, 20: 13, 21: 16}
SKILL_BITS = {0: 931, 1: 932, 2: 933, 3: 934, 4: 935, 5: 936, 6: 937, 7: 938, 8: 939, 9: 940, 10: 941, 11: 942,
              12: 943, 13: 944, 14: 945, 15: 946, 16: 947, 17: 948, 18: 949, 19: 950, 20: 951, 21: 952, 22: 953,
              23: 954, 24: 955, 25: 956, 26: 957, 27: 958, 28: 968, 29: 969, 30: 963, 31: 962, 32: 964, 33: 965,
              34: 959, 35: 966, 36: 960, 37: 961, 38: 967, 39: 970, 40: 971}

POS = ["GK", "CB", "LB", "RB", "DMF", "CMF", "LMF", "RMF", "AMF", "LWF", "RWF", "SS", "CF"]
STYLES = ["None", "Goal Poacher", "Dummy Runner", "Fox in the Box", "Target Man", "Creative Playmaker",
          "Prolific Winger", "Roaming Flank", "Crossing Specialist", "Classic No. 10", "Hole Player", "Box to Box",
          "The Destroyer", "Orchestrator", "Anchor Man", "Offensive Fullback", "Fullback Finisher",
          "Defensive Fullback", "Build Up", "Extra Frontman", "Offensive Goalkeeper", "Defensive Goalkeeper"]
SKILLS = {0: "Scissors Feint", 1: "Flip Flap", 2: "Marseille Turn", 3: "Sombrero", 4: "Cut Behind & Turn",
          5: "Scotch Move", 6: "Heading", 7: "Long Range Drive", 8: "Knuckle Shot", 9: "Acrobatic Finishing",
          10: "Heel Trick", 11: "First-time Shot", 12: "One-touch Pass", 13: "Weighted Pass",
          14: "Pinpoint Crossing", 15: "Outside Curler", 16: "Rabona", 17: "Low Lofted Pass",
          18: "Low Punt Trajectory", 19: "Long Throw", 20: "GK Long Throw", 21: "Malicia", 22: "Man Marking",
          23: "Track Back", 24: "Acrobatic Clear", 25: "Captaincy", 26: "Super-sub", 27: "Fighting Spirit",
          28: "Double Touch", 29: "Crossover Turn", 30: "Step On Skill", 31: "Chip Shot", 32: "Dipping Shot",
          33: "Rising Shot", 34: "No Look Pass", 35: "GK High Punt", 36: "Penalty Specialist",
          37: "GK Penalty Saver", 38: "Interception", 39: "Long Range Shooting", 40: "Through Passing"}


@dataclass
class Player:
    reg: int
    pid: int
    name: str
    attrs: dict
    style: str
    skills: set
    pos: str = ""
    age: int = 0
    teams: list = field(default_factory=list)

    def __getitem__(self, k):
        return self.attrs[k]


@dataclass
class Team:
    idx: int
    name: str
    short: str
    squad: list  # (reg, pid)
    players: list = field(default_factory=list)
    # Códigos das 11 posições da formação realmente usada pelo clube no save.
    # Fica vazio em fotos antigas/exportações que não carregam os planos táticos.
    formation: list = field(default_factory=list)


def decode(rec: bytes) -> dict:
    v = int.from_bytes(rec, 'little')
    a = {k: (v >> b) & ((1 << n) - 1) for k, (b, n) in FIELDS.items()}
    a['style'] = STYLE_MAP.get((v >> STYLE_BIT) & 31, 0)
    a['skills'] = {s for s, b in SKILL_BITS.items() if (v >> b) & 1}
    return a


class Fichas(dict):
    """{(reg, pid): Player} que também acha o jogador só pelo id (fichas da base, registro 0x40A90000).
    Numa carreira recém-criada as fichas na memória ainda são as da base: o save tem (registro, id) da carreira,
    mas a ficha só tem o id certo (10/10/2026)."""
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.por_id = {}

    def _alt(self, k):
        return self.por_id.get(k[1]) if isinstance(k, tuple) and len(k) == 2 else None

    def __missing__(self, k):
        p = self._alt(k)
        if p is None:
            raise KeyError(k)
        return p

    def get(self, k, padrao=None):
        if dict.__contains__(self, k):
            return dict.__getitem__(self, k)
        p = self._alt(k)
        return padrao if p is None else p

    def __contains__(self, k):
        return dict.__contains__(self, k) or self._alt(k) is not None


_CACHE = {}


def load_players(snap_path: str) -> dict:
    """Retorna {(reg, pid): Player} com as fichas da carreira encontradas na foto de memória.
    12/10/2026: a reunião lia a mesma foto ~12 vezes (quase 2 s cada). Agora fica em memória enquanto o arquivo não
    muda (mesmo caminho, tamanho e data de modificação). Quem usa só lê as fichas."""
    import os
    try:
        st = os.stat(snap_path)
        chave = (os.path.abspath(snap_path), st.st_size, st.st_mtime_ns)
    except OSError:
        chave = None
    if chave and chave in _CACHE:
        return _CACHE[chave]
    out = _load_players(snap_path)
    if chave:
        _CACHE.clear()
        _CACHE[chave] = out
    return out


def _load_players(snap_path: str) -> dict:
    data = open(snap_path, 'rb').read()
    # 1) acha fichas "típicas" (0xFFFFFFFF, 0, data válida) só para descobrir onde a tabela está
    seeds = []
    for m in re.finditer(rb'\xff\xff\xff\xff\x00\x00\x00\x00', data):
        o = m.start() - 4
        if o < 0 or o + REC_LEN > len(data):
            continue
        y, mo, d = struct.unpack_from('<HBB', data, o + 12)
        if 2015 <= y <= 2080 and 1 <= mo <= 12 and 1 <= d <= 31:
            if struct.unpack_from('<I', data, o + 124)[0] != BASE_COPY_REG:
                seeds.append(o)
    base_so = False
    if len(seeds) < 1000:   # carreira recém-criada: só existem as fichas da base
        base_so = True
        seeds = []
        for m in re.finditer(rb'\xff\xff\xff\xff\x00\x00\x00\x00', data):
            o = m.start() - 4
            if o >= 0 and o + REC_LEN <= len(data):
                y, mo, d = struct.unpack_from('<HBB', data, o + 12)
                if 2015 <= y <= 2080 and 1 <= mo <= 12 and 1 <= d <= 31:
                    seeds.append(o)
    if not seeds:
        return Fichas()
    # 2) as fichas ficam em sequência a cada 380 bytes: percorre a tabela no mesmo "passo"
    phase = max(set(o % REC_LEN for o in seeds), key=lambda ph: sum(1 for o in seeds if o % REC_LEN == ph))
    in_phase = [o for o in seeds if o % REC_LEN == phase]
    out = Fichas()
    for o in range(min(in_phase), max(in_phase) + REC_LEN, REC_LEN):
        if o + REC_LEN > len(data):
            break
        reg, pid = struct.unpack_from('<II', data, o + 124)
        if pid == 0 or (reg == BASE_COPY_REG and not base_so):
            continue
        raw_name = data[o + 136:o + 198].split(b'\x00')[0]
        try:
            name = raw_name.decode('utf-8')
        except UnicodeDecodeError:
            continue
        if len(name) < 2:
            continue
        a = decode(data[o:o + REC_LEN])
        p = Player(reg, pid, name, a, STYLES[a['style']], a['skills'])
        p.pos = POS[a['reg_pos']] if a['reg_pos'] < len(POS) else '?'
        p.age = a['age']
        out[(reg, pid)] = p
        out.por_id.setdefault(pid, p)
    return out


def load_teams(teams_path: str) -> list:
    teams = []
    for line in open(teams_path, encoding='utf-8'):
        if line.startswith('#'):
            continue
        i, _addr, name, short, _n, rest = line.rstrip('\n').split('|')
        squad = [tuple(map(int, x.split(':'))) for x in rest.split(',') if x]
        teams.append(Team(int(i), name, short, squad))
    return teams


def load_career(snap_path: str, teams_path: str):
    players = load_players(snap_path)
    teams = load_teams(teams_path)
    for t in teams:
        for key in t.squad:
            p = players.get(key)
            if p:
                t.players.append(p)
                p.teams.append(t.name)
    return players, teams
