"""Métricas: recall@k, escolha de limiar e julgamento de cada resposta."""
import unicodedata

import numpy as np
from .nucleo import consulta_do_caso


def recall_at_k(casos, buscador, ks=(1, 3)):
    hits = {k: [] for k in ks}
    ok, no = [], []
    for c in casos:
        r = buscador.buscar(consulta_do_caso(c), max(ks))
        if c["consta"]:
            ouro = set(c["gabarito"]["trechos"])
            ok.append(r[0][1])
            for k in ks:
                hits[k].append(any(t["id"] in ouro for t, _ in r[:k]))
        else:
            no.append(r[0][1])
    return {f"recall@{k}": float(np.mean(v)) for k, v in hits.items()}, ok, no


def escolher_limiar(scores_consta, scores_nao_consta):
    """Varre limiares e maximiza a acurácia balanceada (aceita o que consta, recusa o que não consta)."""
    todos = sorted(set(scores_consta) | set(scores_nao_consta))
    tabela = []
    for l in [todos[0] - 1e-3] + todos:
        tpr = np.mean([s >= l for s in scores_consta]) if scores_consta else 0.0
        tnr = np.mean([s < l for s in scores_nao_consta]) if scores_nao_consta else 0.0
        tabela.append({"limiar": round(float(l), 4), "aceita_o_que_consta": float(tpr),
                       "recusa_o_que_nao_consta": float(tnr), "acuracia_balanceada": float((tpr + tnr) / 2)})
    melhor = max(tabela, key=lambda x: (x["acuracia_balanceada"], x["limiar"]))
    return melhor["limiar"], tabela


def _norm(t):
    return "".join(c for c in unicodedata.normalize("NFD", (t or "").lower()) if unicodedata.category(c) != "Mn")


def julgar(caso, resp, ids_base, ids_recuperados):
    """Critérios (documente no relatório):
    - json_valido: saída parseável e aderente ao schema.
    - acerto: se consta -> tipo e prioridade iguais ao gabarito, próximo passo com ao menos uma palavra-chave do gabarito e sem recusa; se não consta -> recusou.
    - citacao_correta: se consta -> cita ao menos um trecho do gabarito; se não consta -> nenhuma referência.
    - recusa_correta: recusa == (não consta).
    - alucinacao: (a) respondeu sem recusar algo que não consta, (b) citou id inexistente ou não recuperado,
      (c) listou como 'identificada' uma informação que o evento não contém.
    JSON inválido NÃO conta como alucinação (aparece em json_valido)."""
    if resp is None:
        return dict(json_valido=False, acerto=False, citacao_correta=False, recusa_correta=False, alucinacao=False)
    g, consta = caso["gabarito"], caso["consta"]
    refs = set(resp.referencias)
    if consta:
        kw = g.get("proximo_passo_contem")
        passo_ok = not kw or any(_norm(k) in _norm(resp.proximo_passo) for k in kw)
        acerto = (not resp.recusa and resp.tipo_provavel == g["tipo_provavel"]
                  and resp.prioridade_sugerida == g["prioridade_sugerida"] and passo_ok)
        citacao = bool(refs & set(g["trechos"])) and refs <= set(ids_base)
    else:
        acerto = resp.recusa
        citacao = not refs
    alucin = ((not consta and not resp.recusa)
              or not refs <= (set(ids_base) & set(ids_recuperados))
              or not set(resp.informacoes_identificadas) <= set(caso["evento"].keys()))
    return dict(json_valido=True, acerto=bool(acerto), citacao_correta=bool(citacao),
                recusa_correta=bool(resp.recusa == (not consta)), alucinacao=bool(alucin))
