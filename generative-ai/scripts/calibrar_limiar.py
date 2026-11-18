"""Calibra apenas o portão de recusa no conjunto de validação separado."""
import json
from pathlib import Path

from alertavida.nucleo import RAIZ, Buscador, carregar_jsonl, consulta_do_caso, _motivo_sem_suporte


def main():
    casos = carregar_jsonl(RAIZ / "avaliacao" / "casos_validacao.jsonl")
    buscador = Buscador()
    scores = [(c, buscador.buscar(consulta_do_caso(c), 1)[0][1]) for c in casos]
    positivos = [(c, s) for c, s in scores if c["consta"]]
    negativos = [(c, s) for c, s in scores if not c["consta"]]
    candidatos = sorted({s for _, s in scores})
    tabela = []
    for limiar in [candidatos[0] - 1e-6] + candidatos:
        tpr = sum(s >= limiar for _, s in positivos) / max(len(positivos), 1)
        # Perguntas que solicitam fatos ausentes são recusadas por regra de escopo,
        # sem depender da similaridade de um trecho apenas relacionado.
        tnr = sum(bool(_motivo_sem_suporte(c)) or s < limiar for c, s in negativos) / max(len(negativos), 1)
        tabela.append((float((tpr + tnr) / 2), float(limiar), tpr, tnr))
    bal, limiar, tpr, tnr = max(tabela, key=lambda row: (row[0], row[1]))
    recall = {}
    for k in (1, 3):
        hits = []
        for c in casos:
            if not c["consta"]:
                continue
            ids = {t["id"] for t, _ in buscador.buscar(consulta_do_caso(c), k)}
            hits.append(bool(ids & set(c["gabarito"]["trechos"])))
        recall[f"recall@{k}"] = round(sum(hits) / len(hits), 3)
    out = {"limiar": limiar, "recall_validacao": recall,
           "n_validacao": len(casos), "n_respondiveis": len(positivos), "n_sem_suporte": len(negativos),
           "sensibilidade_respondiveis": round(tpr, 3), "especificidade_sem_suporte": round(tnr, 3),
           "acuracia_balanceada_validacao": round(bal, 3),
           "criterio": "maior acuracia balanceada na validacao, incluindo recusas explicitas de fatos ausentes; desempate pelo maior limiar"}
    (RAIZ / "avaliacao" / "limiar.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=2))
    print("Acurácia balanceada na validação:", round(bal, 3))


if __name__ == "__main__":
    main()
