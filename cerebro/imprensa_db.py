"""Banco da IMPRENSA (11/10/2026): historico/imprensa.db (SQLite). A Central lê daqui e atualiza a tela.

Tabelas:
  materias      uma matéria por frente e assunto (chave única): pré-jogo, jogo da rodada (4 x 4), pós-jogo, temporada,
                mercado. corpo = lista de parágrafos (JSON); dados = números para a tela (enquete, escalações, notas...).
  negocios      transferências feitas pelo Mercado IA (aplicar.py grava; a reunião vira matéria e marca materia_id).
  estatisticas  foto das estatísticas da temporada do nosso elenco a cada reunião: a diferença entre duas fotos dá os
                números de UM jogo (passes, chutes, desarmes...) para o pós-jogo.
"""
import datetime as dt
import json
import os
import sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
ARQ = os.path.abspath(os.environ.get('IMPRENSA_DB') or os.path.join(HERE, 'historico', 'imprensa.db'))
FRENTES = ('pre_jogo', 'jogo_da_rodada', 'pos_jogo', 'temporada', 'mercado', 'bola_na_mesa', 'redes', 'premios', 'revelacao')

_ESQUEMA = """
CREATE TABLE IF NOT EXISTS materias (
  id INTEGER PRIMARY KEY, carreira TEXT NOT NULL, chave TEXT NOT NULL UNIQUE, frente TEXT NOT NULL,
  data TEXT NOT NULL, titulo TEXT, linha_fina TEXT, corpo TEXT, dados TEXT, autor TEXT, ia INTEGER DEFAULT 0,
  criado_em TEXT);
CREATE INDEX IF NOT EXISTS materias_carreira ON materias (carreira, frente, data);
CREATE TABLE IF NOT EXISTS negocios (
  id INTEGER PRIMARY KEY, carreira TEXT NOT NULL, data TEXT, janela TEXT, jogador TEXT, idade INTEGER, pos TEXT,
  estilo TEXT, nota REAL, de TEXT, para TEXT, valor REAL, motivo TEXT, perfil TEXT, materia_id INTEGER,
  criado_em TEXT);
CREATE TABLE IF NOT EXISTS premios (
  carreira TEXT NOT NULL, ano INTEGER NOT NULL, categoria TEXT NOT NULL, posicao INTEGER NOT NULL,
  reg INTEGER, pid INTEGER, nome TEXT, clube TEXT, votos INTEGER, fonte TEXT,
  PRIMARY KEY (carreira, ano, categoria, posicao));
CREATE TABLE IF NOT EXISTS diario (
  carreira TEXT NOT NULL, reg INTEGER NOT NULL, pid INTEGER NOT NULL, nome TEXT, data TEXT NOT NULL, tipo INTEGER,
  comp INTEGER, premio TEXT, titulo INTEGER, melhor INTEGER, artilheiro INTEGER, assistencias INTEGER, time_torneio INTEGER,
  PRIMARY KEY (carreira, reg, pid, data, tipo, comp, premio, titulo, melhor, artilheiro, assistencias, time_torneio));
CREATE TABLE IF NOT EXISTS titulos (
  carreira TEXT NOT NULL, temporada TEXT NOT NULL, comp TEXT NOT NULL, campeao TEXT, vice TEXT, placar TEXT,
  data TEXT, elenco_campeao TEXT, elenco_vice TEXT, fonte TEXT,
  PRIMARY KEY (carreira, temporada, comp));
CREATE TABLE IF NOT EXISTS premios_comp (
  carreira TEXT NOT NULL, comp INTEGER NOT NULL, ano INTEGER NOT NULL, tipo INTEGER NOT NULL, ordem INTEGER NOT NULL,
  reg INTEGER, pid INTEGER, nome TEXT, pos TEXT, clube TEXT, valor INTEGER, PRIMARY KEY (carreira, comp, ano, tipo, ordem));
CREATE TABLE IF NOT EXISTS hist_temporada (
  carreira TEXT NOT NULL, temporada TEXT NOT NULL, dados TEXT, atualizado TEXT, PRIMARY KEY (carreira, temporada));
CREATE TABLE IF NOT EXISTS hist_jogador (
  carreira TEXT NOT NULL, temporada TEXT NOT NULL, reg INTEGER NOT NULL, pid INTEGER NOT NULL, nome TEXT, pos TEXT,
  jogos INTEGER, gols INTEGER, assist INTEGER, media REAL, minutos INTEGER, PRIMARY KEY (carreira, temporada, reg, pid));
CREATE TABLE IF NOT EXISTS hist_marcos (
  carreira TEXT NOT NULL, chave TEXT NOT NULL, data TEXT, texto TEXT, PRIMARY KEY (carreira, chave));
CREATE TABLE IF NOT EXISTS estatisticas (
  carreira TEXT NOT NULL, data TEXT NOT NULL, reg INTEGER NOT NULL, pid INTEGER NOT NULL, dados TEXT,
  PRIMARY KEY (carreira, data, reg, pid));
"""


def conectar():
    os.makedirs(os.path.dirname(ARQ), exist_ok=True)
    c = sqlite3.connect(ARQ, timeout=15)
    c.row_factory = sqlite3.Row
    c.executescript(_ESQUEMA)
    return c


def data_txt(d):
    return f'{d[0]:04d}-{d[1]:02d}-{d[2]:02d}'


def _agora():
    return dt.datetime.now().isoformat(timespec='seconds')


def existe(carreira, chave):
    with conectar() as c:
        return c.execute('SELECT 1 FROM materias WHERE carreira = ? AND chave = ?', (carreira, chave)).fetchone() is not None


def data_de(carreira, chave):
    """Data (tupla) da matéria com essa chave, ou None."""
    with conectar() as c:
        r = c.execute('SELECT data FROM materias WHERE carreira = ? AND chave = ?', (carreira, chave)).fetchone()
    return tuple(int(x) for x in r[0].split('-')) if r else None


def gravar(carreira, m):
    """m = {chave, frente, data (tupla), titulo, linha_fina, corpo [parágrafos], dados {}, autor, ia}. Mesma chave = atualiza."""
    with conectar() as c:
        c.execute("""INSERT INTO materias (carreira, chave, frente, data, titulo, linha_fina, corpo, dados, autor, ia, criado_em)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                     ON CONFLICT(chave) DO UPDATE SET titulo = excluded.titulo, linha_fina = excluded.linha_fina,
                       corpo = excluded.corpo, dados = excluded.dados, autor = excluded.autor, ia = excluded.ia,
                       data = excluded.data""",
                  (carreira, m['chave'], m['frente'], data_txt(m['data']), m.get('titulo'), m.get('linha_fina'),
                   json.dumps(m.get('corpo') or [], ensure_ascii=False), json.dumps(m.get('dados') or {}, ensure_ascii=False),
                   m.get('autor'), int(bool(m.get('ia'))), _agora()))
        return c.execute('SELECT id FROM materias WHERE chave = ?', (m['chave'],)).fetchone()[0]


def ultimas(carreira, por_frente=None):
    """{frente: [matérias, mais nova primeiro]} para a Central."""
    por_frente = por_frente or {'pre_jogo': 3, 'jogo_da_rodada': 3, 'pos_jogo': 12, 'temporada': 6, 'mercado': 6,
                                'bola_na_mesa': 8, 'redes': 8, 'premios': 4, 'revelacao': 6, 'rodada': 6, 'selecoes': 4}
    out = {}
    if not os.path.exists(ARQ):
        return out
    with conectar() as c:
        for f, n in por_frente.items():
            rows = c.execute('SELECT * FROM materias WHERE carreira = ? AND frente = ? ORDER BY data DESC, id DESC LIMIT ?',
                             (carreira, f, n)).fetchall()
            out[f] = [{'id': r['id'], 'frente': r['frente'], 'data': [int(x) for x in r['data'].split('-')],
                       'titulo': r['titulo'], 'linha_fina': r['linha_fina'], 'corpo': json.loads(r['corpo'] or '[]'),
                       'dados': json.loads(r['dados'] or '{}'), 'autor': r['autor'], 'ia': bool(r['ia'])} for r in rows]
    return out


# ---------------------------------------------------------------- mercado
def registrar_negocios(carreira, data, janela, moves):
    """moves = [{jogador, idade, pos, estilo, nota, de, para, valor, motivo, perfil}] (aplicar.py, depois do save)."""
    with conectar() as c:
        c.executemany("""INSERT INTO negocios (carreira, data, janela, jogador, idade, pos, estilo, nota, de, para, valor,
                         motivo, perfil, criado_em) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                      [(carreira, data_txt(data) if data else None, janela, m['jogador'], m['idade'], m['pos'], m['estilo'],
                        m['nota'], m['de'], m['para'], m['valor'], m['motivo'], m['perfil'], _agora()) for m in moves])


def negocios_pendentes(carreira):
    with conectar() as c:
        return [dict(r) for r in c.execute('SELECT * FROM negocios WHERE carreira = ? AND materia_id IS NULL ORDER BY valor DESC',
                                           (carreira,))]


def marcar_negocios(ids, materia_id):
    with conectar() as c:
        c.executemany('UPDATE negocios SET materia_id = ? WHERE id = ?', [(materia_id, i) for i in ids])


# ---------------------------------------------------------------- estatísticas por jogo
def foto_estatisticas(carreira, data, por_jogador):
    """por_jogador = {(reg, pid): {campos da temporada}}."""
    with conectar() as c:
        c.executemany('INSERT OR REPLACE INTO estatisticas (carreira, data, reg, pid, dados) VALUES (?, ?, ?, ?, ?)',
                      [(carreira, data_txt(data), k[0], k[1], json.dumps(v)) for k, v in por_jogador.items() if v])


def foto_anterior(carreira, antes_de):
    """A foto mais recente com data < antes_de: (data, {(reg, pid): campos}) ou (None, {})."""
    with conectar() as c:
        r = c.execute('SELECT MAX(data) FROM estatisticas WHERE carreira = ? AND data < ?',
                      (carreira, data_txt(antes_de))).fetchone()
        if not r or not r[0]:
            return None, {}
        rows = c.execute('SELECT reg, pid, dados FROM estatisticas WHERE carreira = ? AND data = ?', (carreira, r[0])).fetchall()
        return tuple(int(x) for x in r[0].split('-')), {(x['reg'], x['pid']): json.loads(x['dados']) for x in rows}
