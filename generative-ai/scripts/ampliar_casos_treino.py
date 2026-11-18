"""Acrescenta exemplos inéditos e revisáveis sem sobrescrever o treino original."""
import json
import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
helpers = runpy.run_path(str(ROOT / "scripts" / "gerar_avaliacao_ampliada.py"))
caso = helpers["caso"]

NOVOS = [
    ("sim", "colisao", "operador relata vítima e pede orientação ao 192", "Quais dados sobre os ocupantes a central costuma perguntar?", ["T005", "T002"], "Informar a quantidade de vítimas, o estado de consciência e se alguém ficou preso às ferragens.", ["quantidade"]),
    ("sim", "colisao", "pessoa aguarda atendimento médico em via urbana", "Como explicar o endereço ao atendente do SAMU?", ["T021"], "Informar o local exato, pontos de referência, descrever a situação e responder às perguntas do Médico Regulador.", ["referência"]),
    ("sim", "atropelamento", "pessoa ferida confirmada pelo operador", "O 192 é tarifado e atende também durante a madrugada?", ["T001"], "O SAMU 192 é gratuito e funciona 24 horas por dia, todos os dias da semana.", ["gratuito"]),
    ("sim", "colisao", "central recebeu chamado de possível trauma", "Quem avalia o chamado e define o envio de ambulância?", ["T002", "T017"], "O Médico Regulador avalia o caso, orienta por telefone e decide a resposta necessária, incluindo envio de equipe.", ["Médico Regulador"]),
    ("sim", "colisao", "operador confirma vítimas em colisão", "Cite exemplos de ocorrências de trânsito para ligar ao SAMU.", ["T003"], "Acidentes ou traumas com vítimas e acidentes com produtos perigosos estão entre as situações para chamar o SAMU 192.", ["vítimas"]),
    ("sim", "colisao", "pessoa sofreu corte leve sem sangramento importante", "O SAMU deve ser acionado para todo corte pequeno?", ["T004"], "Não para situações sem urgência, como corte com pouco sangramento; procure posto de saúde ou UPA.", ["pouco sangramento"]),
    ("sim", "colisao", "acidentado pede algo para beber enquanto aguarda", "Que orientação a página do SAMU dá sobre água?", ["T006"], "Não dê água a pessoas acidentadas enquanto o socorro não chega.", ["água"]),
    ("sim", "moto", "motociclista permanece caído com capacete", "Devo retirar o equipamento da cabeça para examinar?", ["T007"], "Não toque na vítima nem retire o capacete; ligue para o SAMU 192.", ["capacete"]),
    ("sim", "colisao", "carros parados em trecho com tráfego ativo", "Como sinalizar a via conforme a orientação do SAMU?", ["T008"], "Sinalizar a via com triângulo e galhos, ligar para o 192 e seguir o Médico Regulador.", ["triângulo"]),
    ("sim", "colisao", "múltiplas vítimas e necessidade de suporte", "Que tipos de unidade móvel podem ser enviados pelo SAMU?", ["T009"], "Conforme necessidade e disponibilidade, podem ser enviados ambulância, motolância, ambulancha ou aeromédico.", ["ambulância"]),
    ("sim", "colisao", "condutor envolvido em sinistro com vítima", "O que o artigo 176 exige do motorista quando pode ajudar?", ["T010"], "Prestar ou providenciar socorro à vítima e tomar providências para evitar perigo ao trânsito, quando puder fazê-lo.", ["socorro"]),
    ("sim", "colisao", "motorista percebeu vítima após colisão", "Se não puder prestar socorro diretamente por justa causa, o que prevê o CTB?", ["T016"], "Solicitar auxílio da autoridade pública quando não puder prestar socorro diretamente por justa causa.", ["auxílio"]),
    ("sim", "colisao", "sinistro com vítima em estrada federal", "Qual número de emergência da PRF devo usar?", ["T018"], "Ligue para a PRF pelo telefone de emergência 191.", ["191"]),
    ("sim", "colisao", "acidente em BR com faixa bloqueada", "Que referência quilométrica ajuda a PRF?", ["T022"], "Informar a BR, o quilômetro, pontos de referência, condição das vítimas e obstrução da pista ao ligar para 191.", ["quilômetro"]),
    ("sim", "colisao", "ocorrência em rodovia federal concedida", "Há um serviço da concessionária para pedir assistência na rodovia?", ["T022"], "Sim. Acione também o Serviço de Atendimento ao Usuário da concessionária pelo número indicado na rodovia.", ["concessionária"]),
    ("sim", "colisao", "acidente sem vítimas em rodovia federal pública", "Qual é o registro online para uma ocorrência sem vítimas?", ["T026"], "A Declaração de Acidente de Trânsito pode ser preenchida online em até 180 dias por maiores de 18 anos ou emancipados.", ["Declaração"]),
    ("sim", "colisao", "alerta de acidente ainda sem confirmação pelo operador", "Qual é o significado da prioridade média no protocolo interno?", ["T020"], "Prioridade média: o alerta veio da câmera sem informação sobre vítimas e precisa ser confirmado pelo operador.", ["média"]),
    ("sim", "colisao", "operador confirmou exclusivamente avarias materiais", "O critério do projeto sugere qual prioridade para este evento?", ["T020"], "Prioridade baixa, pois o operador confirmou apenas danos materiais e ausência de vítimas.", ["baixa"]),
    ("sim", "colisao", "ocupante imobilizado entre partes do veículo", "Como o projeto classifica pessoa presa nas ferragens?", ["T020"], "O critério interno indica prioridade alta quando há pessoa presa às ferragens.", ["alta"]),
    ("sim", "colisao", "derramamento perigoso em rodovia federal do Paraná", "Que cuidados a PRF orienta antes de falar com as equipes?", ["T025"], "Mantenha distância e não se aproxime; acione PRF 191 e Bombeiros 193 e informe os riscos observados.", ["distância"]),
    ("sim", "colisao", "acidente químico confirmado em Santa Catarina", "Quais órgãos aparecem na orientação da Defesa Civil estadual?", ["T024"], "A orientação de Santa Catarina é afastar-se e acionar Defesa Civil 199 e Bombeiros 193.", ["199"]),
    ("sim", "colisao", "condutor permaneceu no sinistro com vítima", "O que o art. 176, inciso V, diz sobre a identificação do motorista?", ["T014"], "O condutor deve identificar-se ao policial e prestar informações necessárias ao boletim de ocorrência.", ["identificar-se"]),
    ("sim", "colisao", "autoridade solicitou socorro à vítima", "Que obrigação consta no artigo 177 do CTB?", ["T015"], "O condutor não deve deixar de prestar socorro quando solicitado pela autoridade ou seus agentes.", ["socorro"]),
    ("sim", "colisao", "sinistro com vítima e trânsito oferecendo risco", "Quais providências de segurança e preservação aparecem no art. 176?", ["T011", "T012", "T013"], "Evitar perigo para o trânsito, preservar o local e remover o veículo quando uma autoridade determinar.", ["preservar"]),
    ("no", "colisao", "acidente recém-detectado sem atendimento médico registrado", "Em quantos minutos a ambulância vai chegar?"),
    ("no", "colisao", "alerta sem identificação das pessoas envolvidas", "Qual é o CPF do condutor?"),
    ("no", "colisao", "ocorrência sem relatório técnico", "Qual motorista foi culpado?"),
    ("no", "colisao", "vítima aguardando equipe", "Qual hospital foi escolhido pelo Médico Regulador?"),
    ("no", "colisao", "veículo com avarias", "Quanto a seguradora vai pagar?"),
    ("no", "colisao", "acidente em via sem estação meteorológica", "Qual a previsão de chuva para as próximas duas horas?"),
    ("no", "colisao", "ocorrência sem perícia concluída", "Qual era a velocidade exata do automóvel?"),
    ("no", "colisao", "vítima ainda sem avaliação clínica", "Qual analgésico e dose devo dar à pessoa?"),
    ("no", "colisao", "sinistro sem placa visível", "Qual o nome do proprietário do veículo?"),
    ("no", "colisao", "vazamento relatado sem rótulo legível", "Qual é a fórmula química do material?"),
    ("no", "colisao", "condutor deixou o local antes da chegada policial", "Qual condenação o juiz vai definir?"),
    ("no", "colisao", "alerta sem comunicação de terceiros", "Quem são as testemunhas e seus telefones?"),
    ("no", "colisao", "vítima sem histórico clínico registrado", "A pessoa precisa de transfusão de sangue?"),
    ("no", "colisao", "acidente em rodovia sem placa legível", "Qual era o limite de velocidade no trecho?"),
    ("no", "colisao", "ocorrência sem dados cadastrais", "Qual é o telefone pessoal da vítima?"),
]


def main():
    original = [json.loads(x) for x in (ROOT / "avaliacao" / "casos_treino.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    novos = [caso("tra", i, item) for i, item in enumerate(NOVOS, 1)]
    todos = original + novos
    out = ROOT / "avaliacao" / "casos_treino_ampliado.jsonl"
    out.write_text("".join(json.dumps(c, ensure_ascii=False) + "\n" for c in todos), encoding="utf-8")
    print(f"{out.name}: {len(todos)} casos; {sum(c['consta'] for c in todos)} respondíveis e {sum(not c['consta'] for c in todos)} recusas")


if __name__ == "__main__":
    main()
