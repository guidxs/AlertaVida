"""Cria conjuntos de validação e desenvolvimento com casos novos e gabaritos revisáveis.

Não altera o benchmark legado nem os casos de treino. As listas abaixo foram
montadas a partir das fontes citadas em base/fontes.csv.
"""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from alertavida.nucleo import prioridade_do_evento
EVENT_TYPES = {
    "colisao": "possivel_colisao",
    "moto": "possivel_queda_moto",
    "atropelamento": "possivel_atropelamento",
}


def caso(split, i, item):
    if item[0] == "no":
        _, tipo, obs, pergunta = item
        return {"id": f"{split}{i:02d}", "consta": False,
                "evento": {"camera_id": f"CAM-{i:02d}", "timestamp": f"2026-10-{(i % 27)+1:02d}T13:20:00",
                           "event_type": EVENT_TYPES[tipo], "confidence": 0.81, "observacao": obs},
                "pergunta": pergunta, "gabarito": {"recusa": True}}
    _, tipo, obs, pergunta, refs, passo, palavras = item
    prioridade = prioridade_do_evento({"observacao": obs})
    ocorrencia = {"colisao": "colisao_veiculos", "moto": "queda_motociclista", "atropelamento": "atropelamento"}[tipo]
    ausentes = ["endereco_exato", "numero_de_vitimas", "estado_das_vitimas"]
    if prioridade == "baixa":
        ausentes = ["endereco_exato"]
    elif prioridade == "alta":
        ausentes = ["endereco_exato", "estado_das_vitimas"]
    return {"id": f"{split}{i:02d}", "consta": True,
            "evento": {"camera_id": f"CAM-{i:02d}", "timestamp": f"2026-10-{(i % 27)+1:02d}T13:20:00",
                       "event_type": EVENT_TYPES[tipo], "confidence": 0.81, "observacao": obs},
            "pergunta": pergunta,
            "gabarito": {"tipo_provavel": ocorrencia, "prioridade_sugerida": prioridade,
                         "informacoes_ausentes": ausentes, "proximo_passo": passo,
                         "proximo_passo_contem": palavras, "trechos": refs}}


# Conjunto para calibrar recuperação e recusa; nunca usado no treino LoRA.
VALIDACAO = [
    ("sim", "colisao", "alerta de colisão ainda sem confirmação de feridos", "Que informação precisa ser confirmada antes de encaminhar o chamado?", ["T020", "T005"], "Confirmar com o operador a quantidade de vítimas, o estado de consciência e o endereço; seguir orientação do regulador.", ["vítimas"]),
    ("sim", "moto", "motociclista caiu e há suspeita de lesão", "É seguro tirar o capacete para ajudar?", ["T007"], "Não toque na vítima nem retire o capacete; ligue para o SAMU 192 e siga o regulador.", ["capacete"]),
    ("sim", "atropelamento", "operador confirma vítima consciente", "O atendimento do SAMU tem cobrança e funciona em qual horário?", ["T001"], "O SAMU 192 é gratuito e funciona 24 horas por dia, todos os dias.", ["gratuito"]),
    ("sim", "colisao", "há vítima com ferimento em ocorrência de trânsito", "Em quais situações relacionadas a acidentes devo acionar o 192?", ["T003"], "Acione o SAMU em acidentes ou traumas com vítimas e em acidentes com produtos perigosos.", ["vítimas"]),
    ("sim", "colisao", "evento em rodovia federal pública; há obstrução parcial", "O que informar à PRF ao pedir atendimento numa BR?", ["T022"], "Ligar para a PRF 191 e informar BR, quilômetro, pontos de referência, estado das vítimas e obstrução.", ["191"]),
    ("sim", "colisao", "acidente em trecho de rodovia federal concedida", "Além da PRF, quem atende a rodovia concedida?", ["T022"], "Acionar também o Serviço de Atendimento ao Usuário da concessionária, pelo número indicado na rodovia.", ["concessionária"]),
    ("sim", "colisao", "pessoa ferida em emergência médica", "Que localização ajuda a equipe do SAMU a encontrar a ocorrência?", ["T021"], "Informar o local exato e pontos de referência, responder ao regulador e permanecer no local.", ["referência"]),
    ("sim", "colisao", "operador relata ocupante preso nas ferragens", "Qual deve ser a prioridade sugerida pelo projeto?", ["T020"], "Classificar como prioridade alta e confirmar com o operador os dados da vítima antes de qualquer encaminhamento.", ["alta"]),
    ("sim", "colisao", "vazamento de produto perigoso em rodovia federal no Paraná", "Quais autoridades a PRF orienta acionar nesse cenário no Paraná?", ["T025"], "Manter distância e acionar PRF 191 e Corpo de Bombeiros 193, sem se aproximar do produto.", ["191"]),
    ("sim", "colisao", "emergência com produto perigoso confirmada em Santa Catarina", "Qual orientação estadual se aplica em Santa Catarina?", ["T024"], "Afastar-se com segurança e acionar Defesa Civil 199 e Bombeiros 193; não se aproximar para socorrer.", ["199"]),
    ("sim", "colisao", "operador confirma colisão sem vítimas e apenas danos materiais", "Qual prioridade o critério do AlertaVida atribui?", ["T020"], "Prioridade baixa conforme o critério interno; não acionar o SAMU por ausência de urgência médica confirmada.", ["baixa"]),
    ("sim", "colisao", "alerta de câmera sem confirmação de vítimas", "O alerta visual já confirma que houve acidente?", ["T020"], "Não. O alerta da câmera é uma suspeita; o operador precisa confirmar as informações.", ["confirma"]),
    ("no", "colisao", "sem informação sobre ocupantes", "Qual hospital receberá a pessoa ferida?"),
    ("no", "colisao", "alerta de colisão sem endereço no evento", "Qual é o endereço exato da ocorrência?"),
    ("no", "colisao", "evento com vítima, sem dados clínicos", "Qual diagnóstico médico foi confirmado?"),
    ("no", "colisao", "veículos parados após colisão", "Quem causou o acidente?"),
    ("no", "colisao", "ocorrência de trânsito em rodovia", "Qual será o horário de chegada da ambulância?"),
    ("no", "colisao", "sinistro com lesão relatada", "Qual é o valor exato da multa aplicada ao condutor?"),
    ("no", "colisao", "vazamento de produto não identificado", "Qual é o nome químico do produto derramado?"),
    ("no", "colisao", "alerta de acidente sem dados de testemunhas", "Qual o telefone das testemunhas?"),
    ("no", "colisao", "veículo envolvido em ocorrência", "Qual era a velocidade medida antes do impacto?"),
    ("no", "colisao", "ocorrência de trânsito sem identificação de envolvidos", "Qual é a placa do automóvel?"),
    ("no", "colisao", "possível acidente sem laudo", "O motorista estava sob efeito de álcool?"),
    ("no", "colisao", "vítima aguardando socorro", "Qual medicamento e dose devem ser administrados?")
]

# Conjunto final de avaliação, separado da calibração. Manter sem uso para
# escolher limiar, pesos, prompts ou regras após a primeira execução.
TESTE = [
    ("sim", "colisao", "operador relata fratura possível após colisão", "O que deve ser dito sobre a vítima ao ligar para o 192?", ["T005", "T021"], "Informar quantidade de vítimas, consciência e localização; seguir as perguntas do Médico Regulador.", ["vítimas"]),
    ("sim", "moto", "pessoa caída ao lado da motocicleta", "Qual cuidado com a vítima e o capacete?", ["T007"], "Não tocar na vítima nem retirar o capacete; chamar o SAMU 192.", ["capacete"]),
    ("sim", "colisao", "alerta de colisão sem confirmação de pessoa ferida", "O que o operador deve confirmar primeiro?", ["T020", "T005"], "Confirmar quantidade e estado de consciência das vítimas e localização antes do encaminhamento.", ["vítimas"]),
    ("sim", "colisao", "acidente com vítima presa dentro de veículo", "Como classificar a prioridade deste alerta?", ["T020"], "Prioridade alta pelo critério interno; confirmar os dados com o operador.", ["alta"]),
    ("sim", "atropelamento", "vítima confirmada após atropelamento", "Que serviço atende urgências médicas e qual o telefone?", ["T001", "T003"], "Acionar o SAMU pelo 192 para acidente com vítima.", ["192"]),
    ("sim", "colisao", "acidente na BR com pista parcialmente bloqueada", "Qual número da PRF e que dados de localização passar?", ["T018", "T022"], "Ligar para 191 e informar BR, quilômetro, pontos de referência e obstrução.", ["191"]),
    ("sim", "colisao", "acidente sem feridos em rodovia federal pública", "Qual declaração pode ser feita online e em quanto tempo?", ["T026"], "A DAT pode ser preenchida online em até 180 dias por pessoa maior de 18 anos ou emancipada.", ["DAT"]),
    ("sim", "colisao", "chamada de emergência para o SAMU", "Quem decide se uma equipe será enviada?", ["T002", "T017"], "O Médico Regulador avalia a chamada, orienta e decide a resposta necessária.", ["Regulador"]),
    ("sim", "colisao", "operador confirma apenas danos materiais, sem vítimas", "Que prioridade interna deve ser atribuída?", ["T020"], "Prioridade baixa conforme o critério interno.", ["baixa"]),
    ("sim", "colisao", "queda de carga perigosa com vazamento em BR no Paraná", "Como agir sem se expor e quais contatos constam na orientação da PRF?", ["T025"], "Manter distância, acionar PRF 191 e Bombeiros 193 e informar riscos observados sem aproximação.", ["distância"]),
    ("sim", "colisao", "acidente em estrada estadual de Santa Catarina com produto perigoso", "Que números aparecem na orientação da Defesa Civil de SC?", ["T024"], "Afastar-se e ligar para Defesa Civil 199 e Bombeiros 193; não tentar socorrer perto do produto.", ["193"]),
    ("sim", "colisao", "pessoa ferida em acidente e chamada feita ao 192", "O que fazer enquanto o regulador orienta?", ["T002", "T021"], "Descrever a situação, responder às perguntas e permanecer no local para recepcionar a equipe.", ["local"]),
    ("sim", "colisao", "acidente confirmado com vítima", "O atendimento do SAMU tem custo para quem liga?", ["T001"], "Não. A ligação e o serviço SAMU 192 são gratuitos.", ["gratuitos"]),
    ("sim", "colisao", "motorista envolvido em sinistro com vítima", "Que informação o condutor deve fornecer à polícia?", ["T014"], "O condutor deve identificar-se ao policial e prestar informações para o boletim de ocorrência.", ["identificar"]),
    ("sim", "colisao", "condutor encontra vítima em acidente de trânsito", "O que prevê o CTB sobre prestar socorro?", ["T010", "T016"], "Prestar ou providenciar socorro quando possível; se não puder diretamente por justa causa, solicitar auxílio público.", ["socorro"]),
    ("sim", "colisao", "pessoa ferida em sinistro rodoviário", "O que o SAMU orienta para evitar risco adicional no local?", ["T008"], "Sinalizar a via, ligar para o 192 e seguir as orientações do Médico Regulador.", ["sinalizar"]),
    ("no", "colisao", "alerta de acidente sem localização informada", "Qual endereço e quilômetro exatos devem ser registrados?"),
    ("no", "moto", "motociclista envolvido, estado ainda desconhecido", "A vítima tem lesão na coluna cervical?"),
    ("no", "colisao", "carro imobilizado após sinistro", "Qual oficina vai receber o veículo?"),
    ("no", "colisao", "acidente sem informação sobre o condutor", "O motorista possui habilitação válida?"),
    ("no", "colisao", "vítima aguardando atendimento", "Em quantos minutos a equipe estará no endereço?"),
    ("no", "colisao", "produto perigoso sem identificação legível", "Qual procedimento técnico de contenção deve ser executado?"),
    ("no", "colisao", "veículos envolvidos em acidente", "A seguradora pagará indenização e qual será o valor?"),
    ("no", "atropelamento", "alerta de pessoa caída sem dados pessoais", "Qual é o nome completo da vítima?"),
    ("no", "colisao", "ocorrência sem testemunhas identificadas", "Quem presenciou o acidente?"),
    ("no", "colisao", "alerta em via sem sensor meteorológico", "Está chovendo no local neste momento?"),
    ("no", "colisao", "acidente sem relatório policial", "Qual foi a velocidade de cada veículo?"),
    ("no", "colisao", "vítima sem avaliação clínica", "Qual remédio deve ser dado para dor?"),
    ("no", "colisao", "condutor envolvido em sinistro", "Qual punição exata o juiz aplicará ao motorista?"),
    ("no", "colisao", "pessoa ferida em rodovia sem destino hospitalar registrado", "Em qual hospital a ambulância deixará a vítima?"),
    ("no", "colisao", "alerta sem leitura de placa", "Qual é a placa do veículo?"),
    ("no", "colisao", "acidente sem confirmação de vítimas", "A pessoa precisa de cirurgia?"),
]


def gravar(nome, itens, split):
    destino = ROOT / "avaliacao" / nome
    registros = [caso(split, i, item) for i, item in enumerate(itens, 1)]
    destino.write_text("".join(json.dumps(c, ensure_ascii=False) + "\n" for c in registros), encoding="utf-8")
    respondiveis = sum(c["consta"] for c in registros)
    print(f"{destino.name}: {len(registros)} casos ({respondiveis} respondíveis, {len(registros)-respondiveis} sem suporte)")


if __name__ == "__main__":
    gravar("casos_validacao.jsonl", VALIDACAO, "v")
    gravar("casos_teste_desenvolvimento.jsonl", TESTE, "x")
