"""Leitor do EDIT00000000 descriptografado (data.dat) do PES 2021.

Adaptação em Python das rotinas de leitura do 4ccEditor, modificada para uso
somente leitura neste projeto. O 4ccEditor original é Copyright (c) 2020 The
4chan Cup e distribuído sob a licença zlib. Consulte THIRD_PARTY_NOTICES.md.
"""
import sys


class Reader:
    def __init__(self, data, pos=0):
        self.d = data
        self.pos = pos

    def rd(self, start_bit, nbits):
        # porta exata de read_data() do 4ccEditor (data_util.cpp)
        out = 0
        bit = start_bit
        adv = 0
        for ii in range(nbits):
            if bit == 8:
                bit = 0
                self.pos += 1
            if ii % 8 == 0 and ii > 0:
                adv += 1
            shift = bit - (ii % 8)
            b = self.d[self.pos]
            if shift >= 0:
                out += ((b >> shift) & (1 << (ii % 8))) << (adv * 8)
            else:
                out += ((b << -shift) & (1 << (ii % 8))) << (adv * 8)
            bit += 1
        if bit == 8:
            self.pos += 1
        return out

    def skip(self, n):
        self.pos += n

    def cstr(self, n):
        s = self.d[self.pos:self.pos + n].split(b"\x00")[0].decode("utf-8", "replace")
        self.pos += n
        return s


POS = ["GK", "CB", "LB", "RB", "DMF", "CMF", "LMF", "RMF", "AMF", "LWF", "RWF", "SS", "CF"]


def read_player(r):
    p = {}
    p["id"] = r.rd(0, 32)
    r.skip(4)
    p["nation"] = r.rd(0, 16)
    p["height"] = r.rd(0, 8)
    p["weight"] = r.rd(0, 8)
    r.rd(0, 8); r.rd(0, 8)  # gc1, gc2
    seq = [
        ("atk", 0, 7), ("ball_ctrl", 7, 7), ("weak_use", 6, 2), ("tight_pos", 0, 7), ("lowpass", 7, 7),
        ("loftpass", 6, 7), ("finish", 5, 7), ("mo_armd", 4, 4), ("place_kick", 0, 7), ("curl", 7, 7),
        ("speed", 6, 7), ("accel", 5, 7), ("mo_armr", 4, 4), ("jump", 0, 7), ("phys_cont", 7, 7),
        ("balance", 6, 7), ("stamina", 5, 7), ("mo_ck", 4, 4), ("ball_win", 0, 7), ("aggres", 7, 7),
        ("gk", 6, 7), ("catching", 5, 7), ("form", 4, 3), ("b_edit_player", 7, 1), ("gk_reach", 0, 7),
        ("age", 7, 6), ("reg_pos", 5, 4), ("play_style", 2, 5), ("mo_fk", 7, 5), ("star", 4, 3),
        ("b_edit_basicset", 7, 1), ("def", 0, 7), ("clearing", 7, 7), ("header", 6, 7), ("mo_hunchd", 5, 3),
        ("mo_hunchr", 0, 3), ("mo_pk", 3, 3), ("weak_acc", 6, 2), ("drib", 0, 7), ("injury", 7, 2),
        ("play_attit", 1, 2), ("mo_drib", 3, 2),
        ("pp_GK", 5, 2), ("pp_CB", 7, 2), ("pp_LB", 1, 2), ("pp_RB", 3, 2), ("pp_DMF", 5, 2), ("pp_CMF", 7, 2),
        ("pp_LMF", 1, 2), ("pp_RMF", 3, 2), ("pp_AMF", 5, 2), ("b_edit_regpos", 7, 1), ("pp_RWF", 0, 2),
        ("pp_SS", 2, 2), ("pp_CF", 4, 2), ("reflex", 6, 7), ("kick_pwr", 5, 7), ("pp_LWF", 4, 2),
    ]
    for name, sb, nb in seq:
        p[name] = r.rd(sb, nb)
    # flags de edição, pé/mão, estilos COM e 41 habilidades: só avançamos o cursor
    for sb, nb in [(6, 1), (7, 1), (0, 1), (1, 1), (2, 1), (3, 1), (5, 1), (6, 1)]:
        r.rd(sb, nb)
    for sb in [7, 0, 1, 2, 3, 4, 5]:
        r.rd(sb, 1)
    skills = [6, 7, 0, 1, 2, 3, 4, 5, 6, 7, 0, 1, 2, 3, 4, 5, 6, 7, 0, 1, 2, 3, 4, 5, 6, 7, 0, 1, 2, 3, 4, 5, 6, 7, 0, 1, 2, 3, 4, 5, 6]
    for sb in skills:
        r.rd(sb, 1)
    r.skip(1)
    p["name"] = r.cstr(61)
    p["shirt_name"] = r.cstr(61)
    r.skip(64)
    # aparência
    r.skip(4)
    for sb, nb in [(0, 1), (1, 1), (2, 1), (3, 1), (4, 14), (2, 14), (0, 32)]:
        r.rd(sb, nb)
    for _ in range(8):
        r.rd(0, 4); r.rd(4, 4)
    for sb, nb in [(0, 3), (3, 3), (6, 2), (0, 3), (3, 3), (6, 2), (0, 2), (2, 2), (4, 2), (6, 1), (7, 1), (0, 1), (1, 3)]:
        r.rd(sb, nb)
    r.skip(23)
    r.rd(0, 3)
    r.skip(19)
    r.rd(0, 4)
    r.skip(8)
    p["pos"] = POS[p["reg_pos"]] if p["reg_pos"] < len(POS) else str(p["reg_pos"])
    p["ovr"] = approx_overall(p)
    return p


def approx_overall(p):
    """Nota aproximada (não é a fórmula oficial): média dos atributos-chave da posição."""
    keys = {
        "GK": ["gk", "catching", "clearing", "reflex", "gk_reach", "jump"],
        "CB": ["def", "ball_win", "header", "jump", "phys_cont", "aggres", "speed"],
        "LB": ["def", "ball_win", "speed", "stamina", "lowpass", "loftpass", "accel"],
        "RB": ["def", "ball_win", "speed", "stamina", "lowpass", "loftpass", "accel"],
        "DMF": ["def", "ball_win", "lowpass", "loftpass", "stamina", "phys_cont", "aggres"],
        "CMF": ["lowpass", "loftpass", "ball_ctrl", "stamina", "drib", "ball_win", "atk"],
        "LMF": ["lowpass", "loftpass", "drib", "speed", "stamina", "ball_ctrl", "accel"],
        "RMF": ["lowpass", "loftpass", "drib", "speed", "stamina", "ball_ctrl", "accel"],
        "AMF": ["atk", "ball_ctrl", "drib", "lowpass", "finish", "tight_pos", "balance"],
        "LWF": ["atk", "drib", "speed", "accel", "finish", "ball_ctrl", "tight_pos"],
        "RWF": ["atk", "drib", "speed", "accel", "finish", "ball_ctrl", "tight_pos"],
        "SS": ["atk", "finish", "ball_ctrl", "drib", "tight_pos", "accel", "lowpass"],
        "CF": ["atk", "finish", "header", "phys_cont", "ball_ctrl", "kick_pwr", "speed"],
    }.get(p["pos"], ["atk", "def", "ball_ctrl", "speed"])
    return round(sum(p[k] for k in keys) / len(keys))


def read_team(r):
    start = r.pos
    t = {"id": r.rd(0, 32), "manager_id": r.rd(0, 32)}
    r.skip(2)
    t["stadium_id"] = r.rd(0, 16)
    r.skip(0xA)
    r.rd(2, 6); r.rd(0, 6); r.rd(6, 1); r.skip(1)
    r.rd(0, 6); r.rd(6, 6); r.skip(2); r.rd(6, 1); r.skip(1); r.skip(2)
    r.rd(0, 6); r.rd(6, 6)
    r.skip(0x39 + 16)
    t["name"] = r.cstr(0x46)
    t["short"] = r.cstr(4)
    r.skip(181 + 64 + 165)
    return t


def load(path):
    d = open(path, "rb").read()
    n_players = d[96] + d[97] * 256
    n_teams = d[100] + d[101] * 256
    players = [read_player(Reader(d, 0x7C + i * 312)) for i in range(n_players)]
    end_players = 0x7C + n_players * 312
    r = Reader(d, 0x8ED2FC)
    teams = [read_team(r) for _ in range(n_teams)]
    tsize = (r.pos - 0x8ED2FC) // max(n_teams, 1)
    r = Reader(d, 0x9D4648)
    rosters = {}
    for _ in range(n_teams):
        tid = r.rd(0, 32)
        ids = [r.rd(0, 32) for _ in range(40)]
        nums = [r.rd(0, 16) for _ in range(40)]
        r.skip(40)
        rosters[tid] = [(pid, num) for pid, num in zip(ids, nums) if pid]
    return {"players": players, "teams": teams, "rosters": rosters,
            "meta": {"n_players": n_players, "n_teams": n_teams, "end_players": hex(end_players), "team_size": tsize}}


if __name__ == "__main__":
    db = load(sys.argv[1])
    print(db["meta"])
    for p in db["players"][:5]:
        print(p["id"], p["name"], p["pos"], p["age"], p["ovr"])
