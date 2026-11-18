"""Gera avaliacao/casos_teste.jsonl e casos_treino.jsonl a partir de modelos (templates) com semente fixa.
Teste e treino usam perguntas e descrições de observação DIFERENTES. Revise os casos manualmente antes de usar.
Uso: python scripts/gerar_casos.py"""
import json, random
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
rnd = random.Random(2026)

TIPO = {"possivel_colisao": "colisao_veiculos", "possivel_queda_moto": "queda_motociclista",
        "possivel_atropelamento": "atropelamento"}
OBS = {  # chave: (texto, prioridade, trechos_ouro_base, palavras_do_proximo_passo, passo, ausentes)
 "O1": ("sem informação sobre vítimas", "media", ["T020"], ["vitima"],
        "Confirmar com o operador se há vítimas, quantas e o estado de consciência; acionar o 192 se houver vítimas.",
        ["numero_de_vitimas", "estado_das_vitimas", "endereco_exato"]),
 "O2": ("operador relata pessoa presa nas ferragens", "alta", ["T020", "T005"], ["192", "samu"],
        "Acionar o SAMU (192) e informar que há pessoa presa às ferragens; seguir as orientações do Médico Regulador.",
        ["numero_de_vitimas", "estado_de_consciencia", "endereco_exato"]),
 "O3": ("operador relata pessoa caída no chão", "alta", ["T020"], ["192", "samu"],
        "Acionar o SAMU (192) e orientar a não movimentar a vítima até a chegada da equipe.",
        ["numero_de_vitimas", "estado_de_consciencia", "endereco_exato"]),
 "O4": ("operador confirma apenas danos materiais, sem vítimas", "baixa", ["T020", "T004"], ["sem vitima", "registr"],
        "Sem vítimas: não é caso para o SAMU; registrar a ocorrência e acompanhar.",
        ["endereco_exato"]),
 "O5": ("operador relata produto perigoso visível no local", "alta", ["T020", "T003"], ["192", "193", "bombeiros"],
        "Acionar o SAMU (192) e o Corpo de Bombeiros (193) informando o produto perigoso; manter distância.",
        ["numero_de_vitimas", "tipo_do_produto", "endereco_exato"]),
}
OBS_TEXTO = {
 "teste": {key: value[0] for key, value in OBS.items()},
 "treino": {
  "O1": "alerta sem confirmação visual de pessoas feridas",
  "O2": "há relato de ocupante retido entre partes do veículo",
  "O3": "pessoa caída próxima ao veículo após a ocorrência",
  "O4": "operador informa colisão sem feridos, apenas avarias nos veículos",
  "O5": "há recipiente danificado com possível vazamento junto à pista",
 },
}
COMBOS = ([("possivel_colisao", o) for o in OBS] + [("possivel_queda_moto", o) for o in ("O1", "O3")]
          + [("possivel_atropelamento", o) for o in ("O1", "O3")])

PERG_TRIAGEM = {
 "teste": ["Classifique a ocorrência e indique o próximo passo do operador.",
           "Faça a triagem deste alerta de possível acidente.",
           "Qual a prioridade sugerida e o que o operador deve fazer agora?"],
 "treino": ["Triagem do alerta abaixo: tipo, prioridade e próximo passo.",
            "Resuma a ocorrência e diga o que confirmar com o operador.",
            "Classifique este evento detectado pela câmera."]}

# procedural: (pergunta, evento_tipo, ouro, palavras, passo)
PROC = {
 "teste": [
  ("Devo dar água à vítima enquanto o socorro não chega?", "possivel_colisao", ["T006"], ["agua"], "Não dar água à vítima; aguardar o socorro e seguir as orientações do Médico Regulador."),
  ("Posso retirar o capacete do motociclista caído?", "possivel_queda_moto", ["T007"], ["capacete"], "Não tocar na vítima nem retirar o capacete; acionar o SAMU (192)."),
  ("Quais informações devo passar sobre as vítimas ao ligar para o 192?", "possivel_colisao", ["T005", "T002"], ["consciencia", "quantidade"], "Informar a quantidade de vítimas, o estado de consciência, se alguma está presa às ferragens e a localização."),
  ("Qual número ligar para um acidente em rodovia federal?", "possivel_colisao", ["T018", "T019"], ["191"], "Em rodovia federal ligar para a PRF (191); para atendimento médico, SAMU (192)."),
  ("O condutor envolvido pode ir embora sem prestar socorro?", "possivel_colisao", ["T010", "T016"], ["socorro"], "Não: o condutor envolvido deve prestar ou providenciar socorro à vítima, podendo fazê-lo, sob pena de infração e de crime de omissão de socorro."),
  ("O condutor precisa se identificar e dar informações à polícia?", "possivel_colisao", ["T014"], ["identific"], "Sim: o condutor envolvido deve se identificar ao policial e prestar as informações necessárias ao boletim de ocorrência."),
  ("O SAMU cobra pelo atendimento?", "possivel_atropelamento", ["T001"], ["gratuit"], "Não: o SAMU 192 é gratuito e funciona 24 horas por dia."),
 ],
 "treino": [
  ("Quando o SAMU não deve ser acionado?", "possivel_colisao", ["T004"], ["ubs", "upa", "posto"], "Não acionar o SAMU em casos sem urgência (ex.: entorse, corte com pouco sangramento); orientar para posto de saúde ou UPA."),
  ("Em que casos não devo ligar para o 192?", "possivel_colisao", ["T004"], ["ubs", "upa", "posto"], "Não acionar o SAMU em casos sem urgência (ex.: entorse, corte com pouco sangramento); orientar para posto de saúde ou UPA."),
  ("Quem decide enviar a ambulância depois do chamado?", "possivel_colisao", ["T002", "T017"], ["regulador"], "O Médico Regulador decide, após a coleta das informações pelo técnico do atendimento telefônico, e aciona as ambulâncias quando necessário."),
  ("Qual o papel do médico regulador no SAMU?", "possivel_atropelamento", ["T002", "T017"], ["regulador"], "O Médico Regulador orienta o socorro às vítimas e aciona as ambulâncias quando necessário."),
  ("Como sinalizar o local do acidente?", "possivel_colisao", ["T008"], ["triangulo"], "Sinalizar a via com triângulo de sinalização e galhos de árvore e ligar para o 192."),
  ("O que fazer para sinalizar a via antes de o socorro chegar?", "possivel_queda_moto", ["T008"], ["triangulo"], "Sinalizar a via com triângulo de sinalização e galhos de árvore e ligar para o 192."),
  ("Que tipos de veículo o SAMU pode enviar?", "possivel_colisao", ["T009"], ["ambulancia"], "O SAMU pode enviar ambulâncias, motolâncias, ambulanchas ou aeromédicos, conforme a necessidade."),
  ("Qual a prioridade do SAMU ao receber um chamado?", "possivel_atropelamento", ["T009"], ["menor tempo", "atendimento"], "Prestar o atendimento à vítima no menor tempo possível, com envio de médicos conforme a gravidade."),
 ]}

NAO_CONSTA = {
 "teste": ["Qual o endereço exato onde ocorreu o acidente?", "Quantas pessoas ficaram feridas?",
           "Qual a gravidade clínica das vítimas?", "Qual o valor da multa por deixar de prestar socorro?",
           "De quem foi a culpa pelo acidente?", "Qual o protocolo de contenção do produto químico derramado?",
           "Como realizar massagem cardíaca na vítima?", "Qual a placa dos veículos envolvidos?",
           "Em quanto tempo a ambulância vai chegar?", "Qual o limite de velocidade da via?",
           "Qual o nome do motorista envolvido?"],
 "treino": ["Qual o nome e o telefone das testemunhas?", "Qual era a velocidade dos veículos no momento do impacto?",
            "A vítima precisa de transfusão de sangue?", "Qual hospital vai receber o paciente?",
            "Como solicitar a indenização do seguro obrigatório?", "Quantos veículos estavam envolvidos?",
            "Qual medicamento deve ser dado à vítima para a dor?", "O motorista estava embriagado?",
            "Qual é o CEP do local da ocorrência?", "Qual a previsão do tempo para esta região?"]}


def evento(tipo, obs_txt, i, split):
    cam = f"CAM-{rnd.randint(1, 20) + (0 if split == 'teste' else 20):02d}"
    ts = f"2026-11-{rnd.randint(1, 12):02d}T{rnd.randint(6, 22):02d}:{rnd.randint(0, 59):02d}:{rnd.randint(0, 59):02d}"
    return {"camera_id": cam, "timestamp": ts, "event_type": tipo,
            "confidence": round(rnd.uniform(0.62, 0.96), 2), "observacao": obs_txt}


def texto_observacao(split, chave):
    return OBS_TEXTO[split][chave]


def montar(split, n_triagem):
    casos, p = [], "t" if split == "teste" else "tr"
    n = 0
    def nid():
        nonlocal n; n += 1; return f"{p}{n:02d}"
    combos = COMBOS * 3; rnd.shuffle(combos)
    for tipo, o in combos[:n_triagem]:
        _, prio, ouro, kw, passo, aus = OBS[o]
        txt = texto_observacao(split, o)
        ouro = list(ouro) + (["T007"] if tipo == "possivel_queda_moto" and o == "O3" else [])
        casos.append({"id": nid(), "consta": True, "evento": evento(tipo, txt, n, split),
                      "pergunta": rnd.choice(PERG_TRIAGEM[split]),
                      "gabarito": {"tipo_provavel": TIPO[tipo], "prioridade_sugerida": prio,
                                   "informacoes_ausentes": aus, "proximo_passo": passo,
                                   "proximo_passo_contem": kw, "trechos": ouro}})
    for perg, tipo, ouro, kw, passo in PROC[split]:
        _, prio, _, _, _, aus = OBS["O1"]
        txt = texto_observacao(split, "O1")
        casos.append({"id": nid(), "consta": True, "evento": evento(tipo, txt, n, split), "pergunta": perg,
                      "gabarito": {"tipo_provavel": TIPO[tipo], "prioridade_sugerida": prio,
                                   "informacoes_ausentes": aus, "proximo_passo": passo,
                                   "proximo_passo_contem": kw, "trechos": ouro}})
    for perg in NAO_CONSTA[split]:
        tipo, o = rnd.choice(COMBOS)
        casos.append({"id": nid(), "consta": False, "evento": evento(tipo, texto_observacao(split, o), n, split),
                      "pergunta": perg, "gabarito": {"recusa": True}})
    rnd.shuffle(casos)
    for k, c in enumerate(casos, 1):
        c["id"] = f"{p}{k:02d}"
    return casos


if __name__ == "__main__":
    for split, n, nome in (("teste", 14, "casos_teste.jsonl"), ("treino", 24, "casos_treino.jsonl")):
        casos = montar(split, n)
        with open(RAIZ / "avaliacao" / nome, "w", encoding="utf-8") as f:
            for c in casos:
                f.write(json.dumps(c, ensure_ascii=False) + "\n")
        print(nome, len(casos), "casos |", sum(not c["consta"] for c in casos), "não consta")
