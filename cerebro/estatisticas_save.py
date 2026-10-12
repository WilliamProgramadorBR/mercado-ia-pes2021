"""Estatísticas detalhadas dos jogadores guardadas no save da Master League (SOMENTE LEITURA).

Descoberto em 09/10/2026 no save de 03/01/2034, conferido com as telas "Estatíst. dos jogadores" (2033-2034),
"Desarme" e "Ranking" do jogo (William, Wallace, KAIO: 100% dos campos batendo).
Registro de 108 bytes = 27 u32 por jogador:
"""
import struct

REC = 108
CAMPOS = ['reg', 'pid', 'jogos', 'gols', 'assist', 'titular', 'minutos',
          'chutes', 'chutes_gol', 'dribles', 'dribles_ok', 'recebidos', 'recebidos_ok', 'aereas', 'aereas_ok',
          'passe_rasteiro', 'passe_rasteiro_ok', 'passe_alto', 'passe_alto_ok', 'passe_profundidade',
          'passe_profundidade_ok', 'cruzamentos', 'cruzamentos_ok',
          'interceptacoes', 'carrinhos', 'desarmes', 'bloqueios']
__doc__ += '  ' + ', '.join(f'+{4 * i} {c}' for i, c in enumerate(CAMPOS)) + '\n'


def _plausivel(v):
    """Coerência interna: acertos <= tentativas, minutos <= 120 por jogo etc."""
    return (v['jogos'] <= 80 and v['minutos'] <= 125 * max(1, v['jogos']) and v['titular'] <= v['jogos'] and
            v['chutes_gol'] <= v['chutes'] and v['dribles_ok'] <= v['dribles'] and
            v['recebidos_ok'] <= v['recebidos'] and v['aereas_ok'] <= v['aereas'] and
            v['passe_rasteiro_ok'] <= v['passe_rasteiro'] and v['passe_alto_ok'] <= v['passe_alto'] and
            v['passe_profundidade_ok'] <= v['passe_profundidade'] and v['cruzamentos_ok'] <= v['cruzamentos'] and
            v['gols'] <= 150 and v['chutes'] <= 2000)


def ler(d, o):
    v = dict(zip(CAMPOS, struct.unpack_from('<27I', d, o)))
    v['passes'] = v['passe_rasteiro'] + v['passe_alto'] + v['passe_profundidade'] + v['cruzamentos']
    v['passes_ok'] = (v['passe_rasteiro_ok'] + v['passe_alto_ok'] + v['passe_profundidade_ok'] +
                      v['cruzamentos_ok'])
    return v


def tabelas(d, chaves, ini=0x900000, fim=0x1100000, minimo=50):
    """Acha as tabelas de estatísticas: sequências de registros de 108 bytes cujo (reg, id) é um jogador
    conhecido (`chaves` = conjunto de (reg, id) da carreira) e com números coerentes.
    Devolve [(início, n_registros)]."""
    achadas = []
    o = ini
    while o < fim - REC:
        k = struct.unpack_from('<II', d, o)
        if k in chaves and _plausivel(ler(d, o)):
            a = o
            n = 0
            while a + REC <= len(d):
                k2 = struct.unpack_from('<II', d, a)
                if k2 not in chaves or not _plausivel(ler(d, a)):
                    break
                n += 1
                a += REC
            if n >= minimo:
                achadas.append((o, n))
                o = a
                continue
        o += 4
    return achadas


def por_jogador(d, inicio, n):
    out = {}
    for i in range(n):
        v = ler(d, inicio + i * REC)
        out[(v['reg'], v['pid'])] = v
    return out
