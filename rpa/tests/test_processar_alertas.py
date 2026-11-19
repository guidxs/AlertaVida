import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from processar_alertas import calcular_prioridade, processar


class ProcessarAlertasTest(unittest.TestCase):
    def test_prioridade_alta(self) -> None:
        alerta = {"status": "PENDENTE", "confianca": 0.91}
        self.assertEqual(calcular_prioridade(alerta), "ALTA")

    def test_processa_colecao_e_rejeita_duplicado(self) -> None:
        alertas = [
            {"evento_id": "EVT-001", "tipo_ocorrencia": "Acidente", "status": "PENDENTE", "confianca": 0.82},
            {"evento_id": "EVT-001", "tipo_ocorrencia": "Acidente", "status": "PENDENTE", "confianca": 0.82},
            {"evento_id": "", "tipo_ocorrencia": "", "status": "PENDENTE", "confianca": 0.99},
        ]
        resultado = processar(alertas)

        self.assertEqual(resultado["total_processados"], 1)
        self.assertEqual(resultado["duplicados"], 1)
        self.assertEqual(resultado["invalidos"], 1)
        self.assertEqual(resultado["prioridades"]["MEDIA"], 1)

    def test_rejeita_confianca_fora_do_intervalo(self) -> None:
        resultado = processar([
            {"evento_id": "EVT-002", "tipo_ocorrencia": "Acidente", "status": "PENDENTE", "confianca": 1.4},
        ])
        self.assertEqual(resultado["total_processados"], 0)
        self.assertEqual(resultado["invalidos"], 1)

    def test_rejeita_status_desconhecido(self) -> None:
        resultado = processar([
            {"evento_id": "EVT-003", "tipo_ocorrencia": "Acidente", "status": "EM_ANALISE", "confianca": 0.95},
        ])
        self.assertEqual(resultado["total_processados"], 0)
        self.assertEqual(resultado["invalidos"], 1)

    def test_confianca_invalida_nao_causa_excecao(self) -> None:
        resultado = processar([
            {"evento_id": "EVT-004", "tipo_ocorrencia": "Acidente", "status": "PENDENTE", "confianca": "inválida"},
        ])
        self.assertEqual(resultado["total_processados"], 0)
        self.assertEqual(resultado["invalidos"], 1)


if __name__ == "__main__":
    unittest.main()
