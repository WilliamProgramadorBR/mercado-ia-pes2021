# Mercado IA — autor: William (https://github.com/WilliamProgramadorBR)
"""CLÁSSICOS (11/10/2026): rivalidades reais, com o nome que a imprensa usa. O PES tem cenas próprias de clássico na
Liga Master; a Central passa a tratar esses jogos como especiais (coletiva, imprensa, Bola na Mesa, redes).
Os nomes dos times vêm do save (MAIÚSCULAS, às vezes abreviados); a comparação é por nome normalizado.
"""
import unicodedata

# (time A, time B, nome do clássico) — fatos reais do futebol
DERBIES = [
    ('MANCHESTER UNITED', 'MANCHESTER CITY', 'Derby de Manchester'),
    ('MANCHESTER UNITED', 'LIVERPOOL', 'North West Derby'),
    ('MANCHESTER UNITED', 'LEEDS UNITED', 'Roses Derby'),
    ('MANCHESTER UNITED', 'ARSENAL', 'clássico Manchester United x Arsenal'),
    ('LIVERPOOL', 'EVERTON', 'Merseyside Derby'),
    ('ARSENAL', 'TOTTENHAM HOTSPUR', 'North London Derby'),
    ('CHELSEA', 'TOTTENHAM HOTSPUR', 'clássico de Londres'),
    ('CHELSEA', 'ARSENAL', 'clássico de Londres'),
    ('NEWCASTLE', 'SUNDERLAND', 'Tyne-Wear Derby'),
    ('ASTON VILLA', 'BIRMINGHAM CITY', 'Second City Derby'),
    ('SHEFFIELD UNITED', 'SHEFFIELD WEDNESDAY', 'Steel City Derby'),
    ('REAL MADRID', 'BARCELONA', 'El Clásico'),
    ('REAL MADRID', 'ATLETICO DE MADRID', 'Derbi Madrileño'),
    ('BARCELONA', 'ESPANYOL', 'Derbi Barceloní'),
    ('SEVILLA', 'REAL BETIS', 'Derbi Sevillano'),
    ('MILAN', 'INTERNAZIONALE', 'Derby della Madonnina'),
    ('JUVENTUS', 'INTERNAZIONALE', "Derby d'Italia"),
    ('JUVENTUS', 'TORINO', 'Derby della Mole'),
    ('ROMA', 'LAZIO', 'Derby della Capitale'),
    ('BAYERN MUNCHEN', 'BORUSSIA DORTMUND', 'Der Klassiker'),
    ('BORUSSIA DORTMUND', 'SCHALKE 04', 'Revierderby'),
    ('PARIS SAINT-GERMAIN', 'OLYMPIQUE DE MARSEILLE', 'Le Classique'),
    ('PARIS SAINT-GERMAIN', 'PARIS', 'clássico de Paris'),
    ('OLYMPIQUE DE MARSEILLE', 'OLYMPIQUE LYONNAIS', 'Choc des Olympiques'),
    ('BORUSSIA DORTMUND', 'BORUSSIA MÖNCHENGLADBACH', 'Borussen-Derby'),
    ('BRISTOL CITY', 'BRISTOL ROVERS', 'Bristol Derby'),
    ('BENFICA', 'PORTO', 'O Clássico'),
    ('BENFICA', 'SPORTING', 'Derby de Lisboa'),
    ('AJAX', 'FEYENOORD', 'De Klassieker'),
    ('CELTIC', 'RANGERS', 'Old Firm'),
    ('GALATASARAY', 'FENERBAHCE', 'Derby Intercontinental'),
    ('BOCA JUNIORS', 'RIVER PLATE', 'Superclásico'),
    ('FLAMENGO', 'FLUMINENSE', 'Fla-Flu'),
    ('FLAMENGO', 'VASCO DA GAMA', 'Clássico dos Milhões'),
    ('FLAMENGO', 'BOTAFOGO', 'clássico Flamengo x Botafogo'),
    ('FLUMINENSE', 'BOTAFOGO', 'Clássico Vovô'),
    ('FLUMINENSE', 'VASCO DA GAMA', 'Clássico dos Gigantes'),
    ('CORINTHIANS', 'PALMEIRAS', 'Derby Paulista'),
    ('CORINTHIANS', 'SAO PAULO', 'Majestoso'),
    ('PALMEIRAS', 'SAO PAULO', 'Choque-Rei'),
    ('SANTOS', 'SAO PAULO', 'San-São'),
    ('SANTOS', 'CORINTHIANS', 'clássico Alvinegro'),
    ('SANTOS', 'PALMEIRAS', 'Clássico da Saudade'),
    ('GREMIO', 'INTERNACIONAL', 'Grenal'),
    ('ATLETICO MINEIRO', 'CRUZEIRO', 'Clássico Mineiro'),
    ('BAHIA', 'VITORIA', 'Ba-Vi'),
    ('ATHLETICO PARANAENSE', 'CORITIBA', 'Atletiba'),
    ('SPORT RECIFE', 'NAUTICO', 'Clássico dos Clássicos'),
    ('CEARA', 'FORTALEZA', 'Clássico-Rei'),
    ('REMO', 'PAYSANDU', 'Re-Pa'),
]


def _norm(t):
    t = unicodedata.normalize('NFKD', t or '').encode('ascii', 'ignore').decode().upper().strip()
    return ' '.join(t.replace('-', ' ').split())


ALIAS = {'PARIS SAINT GERMAIN': {'PARIS SAINT GERMAIN', 'PARIS SG', 'PSG'}, 'BAYERN MUNCHEN': {'BAYERN MUNCHEN', 'FC BAYERN'},
         'ATLETICO DE MADRID': {'ATLETICO DE MADRID', 'ATLETICO MADRID', 'ATL. MADRID'},
         'OLYMPIQUE DE MARSEILLE': {'OLYMPIQUE DE MARSEILLE', 'MARSEILLE', 'OLYMPIQUE MARSEILLE'},
         'VASCO DA GAMA': {'VASCO DA GAMA', 'VASCO'}, 'ATHLETICO PARANAENSE': {'ATHLETICO PARANAENSE', 'ATHLETICO PR', 'ATHLETICO'},
         'FENERBAHCE': {'FENERBAHCE'}, 'INTERNAZIONALE': {'INTERNAZIONALE', 'INTER', 'INTER DE MILAO'}}


def _bate(nome, alvo):
    """Nome EXATO (normalizado) ou apelido conhecido: 'LIVERPOOL MONTEVIDEO' não é o Liverpool."""
    a, b = _norm(nome), _norm(alvo)
    return a == b or a in ALIAS.get(b, ())


def nome(time_a, time_b):
    """Nome do clássico entre os dois times, ou None. Times da mesma cidade (MANCHESTER x MANCHESTER) também valem."""
    for a, b, n in DERBIES:
        if (_bate(time_a, a) and _bate(time_b, b)) or (_bate(time_a, b) and _bate(time_b, a)):
            return n
    return None
