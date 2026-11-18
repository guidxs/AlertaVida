"""Executa as 3 configurações no conjunto de teste e gera avaliacao/placar.csv.
Uso: python -m alertavida.placar [sem_contexto rag rag_lora]"""
import gc
import json
import argparse
import sys
import time

import pandas as pd

from .metricas import julgar
from .nucleo import ADAPTADOR, RAIZ, Buscador, Gerador, carregar_jsonl, carregar_limiar, triar

AV = RAIZ / "avaliacao"


def rodar(config, casos, buscador, limiar, saida_prefix="", adaptador=None):
    gerador = Gerador((adaptador or ADAPTADOR) if config == "rag_lora" else None)
    ids_base = [t["id"] for t in buscador.trechos]
    linhas = []
    for c in casos:
        t0 = time.time()
        resp, bruto, achados = triar(c, config, buscador, gerador, limiar)
        j = julgar(c, resp, ids_base, [t["id"] for t, _ in achados] if config != "sem_contexto" else [])
        linhas.append({"id": c["id"], "config": config, **j, "segundos": round(time.time() - t0, 2),
                       "resposta": resp.model_dump() if resp else None, "bruto": bruto,
                       "recuperados": [t["id"] for t, _ in achados]})
    del gerador
    gc.collect()
    try:
        import torch
        torch.cuda.empty_cache()
    except Exception:
        pass
    with open(AV / f"resultados_{saida_prefix}{config}.jsonl", "w", encoding="utf-8") as f:
        for l in linhas:
            f.write(json.dumps(l, ensure_ascii=False) + "\n")
    return linhas


def montar_placar(todas, caminho=None):
    df = pd.DataFrame(todas)
    cols = ["acerto", "alucinacao", "json_valido", "citacao_correta", "recusa_correta"]
    placar = df.groupby("config")[cols + ["segundos"]].mean().round(3)
    placar["n_casos"] = df.groupby("config").size()
    placar.to_csv(caminho or AV / "placar.csv")
    return placar


def erros(config, n=10, casos_path=None, resultados_path=None):
    """Lista erros a partir do mesmo conjunto usado na rodada selecionada."""
    casos = {c["id"]: c for c in carregar_jsonl(casos_path or AV / "casos_teste.jsonl")}
    out = []
    for l in carregar_jsonl(resultados_path or AV / f"resultados_{config}.jsonl"):
        if not l["acerto"] or l["alucinacao"] or not l["json_valido"]:
            out.append({"id": l["id"], "pergunta": casos[l["id"]]["pergunta"], "acerto": l["acerto"],
                        "alucinacao": l["alucinacao"], "json_valido": l["json_valido"],
                        "recuperados": l["recuperados"], "gabarito": casos[l["id"]]["gabarito"],
                        "resposta": l["resposta"] or l["bruto"][:300]})
    return out[:n]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--casos", default=str(AV / "casos_teste.jsonl"))
    parser.add_argument("--saida-prefix", default="", help="prefixo para preservar resultados de outras rodadas")
    parser.add_argument("--adaptador", default=str(ADAPTADOR), help="diretório do adaptador usado no modo rag_lora")
    parser.add_argument("configs", nargs="*", default=["sem_contexto", "rag", "rag_lora"])
    op = parser.parse_args()
    casos = carregar_jsonl(op.casos)
    buscador, limiar = Buscador(), carregar_limiar()
    todas = []
    for cfg in op.configs:
        print(f"== {cfg}")
        todas += rodar(cfg, casos, buscador, limiar, op.saida_prefix, op.adaptador)
    placar_nome = op.saida_prefix.strip("_") if op.saida_prefix else "final"
    print(montar_placar(todas, AV / f"placar_{placar_nome}.csv"))
