import json
import os
import sys
import tempfile
import unittest
from types import SimpleNamespace

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'cerebro'))

import dados
import encaixe
import janela
import memoria_clubes


class CoreTests(unittest.TestCase):
    def test_formacao_real(self):
        team = dados.Team(0, 'TESTE', 'TST', [], [], [0, 1, 1, 1, 4, 4, 7, 6, 11, 11, 12])
        slots = [position for position, _accepted in encaixe.formation_slots(team)]
        self.assertEqual(slots, ['GK', 'CB', 'CB', 'CB', 'DMF', 'DMF', 'RMF', 'LMF', 'SS', 'SS', 'CF'])

    def test_formacao_invalida_recua_para_padrao(self):
        team = dados.Team(0, 'TESTE', 'TST', [], [], [1] * 11)
        self.assertEqual(encaixe.formation_slots(team), encaixe.SLOTS)

    def test_janelas(self):
        self.assertEqual(janela.window_of((2033, 8, 4)), ('2033-verao', 'verao'))
        self.assertEqual(janela.window_of((2033, 12, 20)), ('2034-inverno', 'inverno'))
        self.assertEqual(janela.window_of((2034, 3, 1)), (None, 'fora'))

    def test_perfil_deterministico(self):
        players = [SimpleNamespace(age=20) for _ in range(10)] + [SimpleNamespace(age=26) for _ in range(12)]
        team = SimpleNamespace(name='CLUBE TESTE', players=players)
        evaluation = {'forca': 78.0}
        self.assertEqual(memoria_clubes.make_profile(team, evaluation),
                         memoria_clubes.make_profile(team, evaluation))

    def test_livro_caixa_persistente(self):
        career = {
            'clubes': {'A': {'orcamento': 50.0}, 'B': {'orcamento': 10.0}},
            'historico': [],
        }
        move = SimpleNamespace(jogador='Jogador', de='B', para='A', valor=12.5, motivo='teste')
        memoria_clubes.record(career, [(move, 8)], 2033, '2033-verao')
        self.assertEqual(career['clubes']['A']['orcamento'], 37.5)
        self.assertEqual(career['clubes']['B']['orcamento'], 22.5)
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, 'memoria.json')
            data = {'schema': 1, 'carreiras': {'teste': career}}
            memoria_clubes.save(data, path)
            with open(path, encoding='utf-8') as saved:
                self.assertEqual(memoria_clubes.load(path), json.load(saved))


if __name__ == '__main__':
    unittest.main()
