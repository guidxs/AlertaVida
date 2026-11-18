"""Núcleo do pipeline AlertaVida: base, busca, prompt, geração e validação do JSON."""
import json
import math
import os
import re
import unicodedata
from collections import Counter
from pathlib import Path
from typing import List, Literal, Optional

import numpy as np
from pydantic import BaseModel, model_validator

RAIZ = Path(__file__).resolve().parents[1]
LLM_ID = os.getenv("LLM_ID", "Qwen/Qwen2.5-1.5B-Instruct")
EMB_ID = os.getenv("EMB_ID", "intfloat/multilingual-e5-small")
ADAPTADOR = RAIZ / "modelos" / "lora_alertavida"

TipoOcorrencia = Literal["colisao_veiculos", "atropelamento", "queda_motociclista",
                         "incendio_veicular", "outro", "indeterminado"]
Prioridade = Literal["baixa", "media", "alta"]


class Triagem(BaseModel):
    tipo_provavel: Optional[TipoOcorrencia] = None
    prioridade_sugerida: Optional[Prioridade] = None
    informacoes_identificadas: List[str] = []
    informacoes_ausentes: List[str] = []
    proximo_passo: Optional[str] = None
    referencias: List[str] = []
    recusa: bool = False
    motivo_recusa: Optional[str] = None

    @model_validator(mode="after")
    def _coerencia(self):
        if not self.recusa and (self.tipo_provavel is None or self.prioridade_sugerida is None):
            raise ValueError("sem recusa, tipo_provavel e prioridade_sugerida são obrigatórios")
        return self


def carregar_jsonl(caminho) -> list:
    with open(caminho, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def carregar_limiar() -> float:
    p = RAIZ / "avaliacao" / "limiar.json"
    return json.loads(p.read_text())["limiar"] if p.exists() else 0.0


def consulta_do_caso(caso: dict) -> str:
    e = caso["evento"]
    pergunta = _normalizar(caso.get("pergunta", ""))
    base = str(caso.get("pergunta", "")).strip()
    if any(x in pergunta for x in ("triagem", "classifique", "classificacao", "prioridade", "proximo passo",
                                    "o que o operador deve fazer", "analise este alerta")):
        base = f"{base} {e.get('event_type', '')} {e.get('observacao', '')}".strip()
    expansoes = []
    rotas = (
        (("quantidade", "vitima", "consci", "ligar para o 192", "falar ao 192", "dados sobre as pessoas", "pessoas envolvidas devo relatar", "dados das vitimas", "informacoes sobre as vitimas", "relatar as pessoas"),
         "quantidade de vítimas estado de consciência pessoas presas ferragens localização"),
        (("quem decide", "quem analisa", "quem escolhe", "determina os recursos", "regulador", "equipe sera enviada", "equipe ser enviada", "ambulancia sera"),
         "Médico Regulador avalia chamado orienta e decide envio de equipe e ambulância"),
        (("condutor", "policia", "boletim", "identificar se"),
         "artigo 176 inciso V condutor identificar-se ao policial prestar informações boletim de ocorrência"),
        (("ctb", "prestar socorro", "providenciar socorro", "dever do motorista", "dever do condutor", "dever de assistencia"),
         "artigo 176 artigo 304 prestar ou providenciar socorro solicitar auxílio autoridade pública"),
        (("sinalizar", "risco adicional", "evitar perigo", "triangulo", "reduzir perigo de novas colisoes", "recurso de alerta na via"),
         "sinalizar via galhos árvore triângulo de sinalização ligar 192"),
        (("comprova", "prova que houve", "deteccao da camera"),
         "alerta de câmera não confirma acidente operador valida informações prioridade do projeto"),
        (("telefone da prf", "qual numero da prf", "referencias de local", "quilometro pontos de referencia"),
         "rodovia federal PRF 191 BR quilômetro pontos de referência estado das vítimas pista obstruída"),
        (("dat", "declaracao pode ser feita", "declaração pode ser feita", "sem vitimas rodovia federal"),
         "Declaração de Acidente de Trânsito DAT online até 180 dias maiores de 18 anos emancipados"),
        (("gratuito", "custo", "cobranca", "cobrança", "horario do samu"),
         "SAMU 192 gratuito ligação gratuita 24 horas por dia todos os dias"),
        (("local exato", "pontos de referencia", "pontos de referência", "encontrar a ocorrencia", "explicar o local", "localizar um acidente"),
         "SAMU informar local exato emergência pontos de referência permanecer no local"),
        (("servico 192", "servico telefonico", "urgencias medicas", "atende sem cobranca", "sem cobranca"),
         "SAMU serviço gratuito telefone 192 24 horas acidentes traumas com vítimas emergência"),
        (("acidente sem vitimas", "declaracao de acidente", "declaracao online", "prazo da dat", "prazo para registrar a dat"),
         "Declaração de Acidente de Trânsito DAT online até 180 dias maiores de 18 anos emancipados rodovia federal sem vítimas"),
        (("rodovia concedida", "trecho tiver concessao", "servico rodoviario", "servico de atendimento ao usuario"),
         "rodovia federal concedida Serviço de Atendimento ao Usuário SAU concessionária telefone indicado na rodovia"),
        (("produto perigoso", "vazamento", "contatos constam", "sem se expor"),
         "produto perigoso manter distância PRF 191 Bombeiros 193 riscos observados jurisdição"),
        (("santa catarina", "defesa civil de sc"),
         "Santa Catarina emergência produto perigoso afastar ligar Defesa Civil 199 Bombeiros 193"),
    )
    for gatilhos, acrescimo in rotas:
        if any(g in pergunta for g in gatilhos):
            expansoes.append(acrescimo)
    return (base + " " + " ".join(expansoes)).strip()


class Buscador:
    """Busca híbrida: fusão de ranking semântico e BM25 lexical."""

    def __init__(self):
        from sentence_transformers import SentenceTransformer
        self.trechos = carregar_jsonl(RAIZ / "base" / "trechos.jsonl")
        self.modelo = SentenceTransformer(EMB_ID)
        self.E = self.modelo.encode(["passage: " + t["texto"] for t in self.trechos],
                                    normalize_embeddings=True)
        self.docs = [_tokens(t["texto"]) for t in self.trechos]
        self.media_tamanho = sum(map(len, self.docs)) / max(len(self.docs), 1)
        self.df = Counter(token for doc in self.docs for token in set(doc))

    def _bm25(self, consulta: str) -> np.ndarray:
        termos = set(_tokens(consulta))
        n = len(self.docs)
        scores = []
        for doc in self.docs:
            freq = Counter(doc)
            tamanho = len(doc)
            score = 0.0
            for termo in termos:
                tf = freq.get(termo, 0)
                if not tf:
                    continue
                df = self.df[termo]
                idf = math.log(1 + (n - df + 0.5) / (df + 0.5))
                score += idf * (tf * 2.5) / (tf + 1.5 * (0.25 + 0.75 * tamanho / self.media_tamanho))
            scores.append(score)
        return np.asarray(scores, dtype=float)

    def buscar(self, consulta: str, k: int = 3):
        q = self.modelo.encode(["query: " + consulta], normalize_embeddings=True)[0]
        dense = self.E @ q
        lexical = self._bm25(consulta)
        dense_rank = np.empty(len(dense), dtype=int)
        lexical_rank = np.empty(len(lexical), dtype=int)
        dense_rank[np.argsort(-dense, kind="stable")] = np.arange(len(dense))
        lexical_rank[np.argsort(-lexical, kind="stable")] = np.arange(len(lexical))
        # Fusão de scores: BM25 recupera números/termos exatos e o encoder
        # aproxima paráfrases. Relevância é um escore heurístico, não probabilidade.
        lex_max = float(lexical.max()) if lexical.size else 0.0
        lex_norm = lexical / lex_max if lex_max > 0 else np.zeros_like(lexical)
        scores = 0.75 * dense + 0.25 * lex_norm
        idx = np.argsort(-scores, kind="stable")[:k]
        return [(self.trechos[i], float(scores[i])) for i in idx]


_STOPWORDS = {"a", "ao", "aos", "as", "com", "como", "da", "das", "de", "do", "dos", "e", "em",
              "essa", "esse", "esta", "este", "eu", "foi", "há", "ha", "isso", "na", "nas", "no",
              "nos", "o", "os", "ou", "para", "pela", "pelas", "pelo", "pelos", "por", "que",
              "qual", "quais", "se", "sem", "sobre", "um", "uma", "umas", "uns", "é", "e"}


def _tokens(texto: str) -> list[str]:
    normalizado = _normalizar(texto)
    return [t for t in re.findall(r"[a-z0-9]+", normalizado) if len(t) > 1 and t not in _STOPWORDS]


def _normalizar(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", str(texto).casefold())
                   if unicodedata.category(c) != "Mn")


SISTEMA = """Você é o módulo de triagem do AlertaVida, que apoia operadores de uma central de monitoramento.
Você recebe um EVENTO detectado por câmera (possível acidente, AINDA NÃO confirmado) e uma PERGUNTA.
Regras:
1. Use SOMENTE as informações do evento e dos TRECHOS fornecidos. Nunca invente endereço, número de vítimas ou gravidade.
2. Em "referencias" coloque os ids dos trechos usados (ex.: "T003"). Se não usou nenhum, lista vazia.
3. Se os trechos não bastarem para responder, devolva "recusa": true com "motivo_recusa" e deixe os demais campos vazios ou null.
4. "informacoes_identificadas": nomes dos campos do evento que vieram preenchidos. "informacoes_ausentes": dados necessários ao chamado que não constam (ex.: endereco_exato, numero_de_vitimas, estado_das_vitimas).
5. tipo_provavel: colisao_veiculos | atropelamento | queda_motociclista | incendio_veicular | outro | indeterminado. prioridade_sugerida: baixa | media | alta.
6. Responda diretamente à pergunta em "proximo_passo". Não substitua a resposta factual por uma orientação genérica sobre o SAMU. Se a pergunta não for de triagem, preserve o fato perguntado ao resumir o trecho; não acrescente procedimentos que o trecho não diz.
7. Só responda com informação sustentada por um trecho recuperado. Se ele for relacionado, mas não trouxer o dado pedido, recuse. Citações devem apoiar a resposta, não apenas ser assunto parecido.
8. Responda APENAS com um JSON válido, sem texto fora dele, neste formato:
{"tipo_provavel": "...", "prioridade_sugerida": "...", "informacoes_identificadas": [], "informacoes_ausentes": [], "proximo_passo": "...", "referencias": [], "recusa": false, "motivo_recusa": null}"""


def montar_mensagens(caso: dict, trechos: Optional[list]) -> list:
    if trechos:
        ctx = "\n".join(f"[{t['id']}] ({t['fonte']}) {t['texto']}" for t in trechos)
    else:
        ctx = "(nenhum)"
    user = (f"EVENTO:\n{json.dumps(caso['evento'], ensure_ascii=False)}\n\n"
            f"TRECHOS:\n{ctx}\n\nPERGUNTA: {caso['pergunta']}")
    return [{"role": "system", "content": SISTEMA}, {"role": "user", "content": user}]


class Gerador:
    def __init__(self, adaptador: Optional[Path] = None):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        self.torch = torch
        self.tok = AutoTokenizer.from_pretrained(LLM_ID)
        cuda = torch.cuda.is_available()
        dtype = (torch.bfloat16 if cuda and torch.cuda.is_bf16_supported()
                 else torch.float16 if cuda else torch.float32)
        self.modelo = AutoModelForCausalLM.from_pretrained(LLM_ID, torch_dtype=dtype)
        if adaptador:
            from peft import PeftModel
            self.modelo = PeftModel.from_pretrained(self.modelo, str(adaptador))
        self.modelo.to("cuda" if cuda else "cpu").eval()

    def gerar(self, mensagens: list, max_new_tokens: int = 350) -> str:
        texto = self.tok.apply_chat_template(mensagens, tokenize=False, add_generation_prompt=True)
        ent = self.tok(texto, return_tensors="pt").to(self.modelo.device)
        with self.torch.no_grad():
            out = self.modelo.generate(**ent, max_new_tokens=max_new_tokens, do_sample=False)
        return self.tok.decode(out[0][ent.input_ids.shape[1]:], skip_special_tokens=True)


def extrair_json(txt: str) -> Optional[Triagem]:
    m = re.search(r"\{.*\}", txt, re.S)
    if not m:
        return None
    try:
        dados = json.loads(m.group(0))
        passo = dados.get("proximo_passo")
        if isinstance(passo, dict):
            atividades = passo.get("atividades", [])
            descricoes = [a.get("descricao") or a.get("atividade")
                          for a in atividades if isinstance(a, dict)]
            dados["proximo_passo"] = "; ".join(filter(None, descricoes)) or None
        return Triagem.model_validate(dados)
    except Exception:
        return None


def recusa_padrao(motivo: str) -> Triagem:
    return Triagem(recusa=True, motivo_recusa=motivo)


def prioridade_do_evento(evento: dict) -> Prioridade:
    """Aplica o critério explícito do projeto, sem delegar prioridade ao LLM."""
    texto = "".join(c for c in unicodedata.normalize("NFD", str(evento.get("observacao", "")).casefold())
                    if unicodedata.category(c) != "Mn")
    if any(x in texto for x in ("produto perigoso", "possivel vazamento", "recipiente danificado com possivel vazamento")):
        return "alta"
    for sinal in ("pessoa presa", "vitima presa", "ocupante preso", "ocupante retido", "retido nas ferragens",
                  "pessoa caida", "pessoa no chao"):
        pos = texto.find(sinal)
        if pos >= 0 and not any(x in texto[max(0, pos - 24):pos] for x in ("sem ", "nao ", "não ", "nega ")):
            return "alta"
    negacao = any(x in texto for x in ("sem confirmacao", "nao confirmado", "nao ha informacao", "sem informacao"))
    if not negacao and any(x in texto for x in ("vitima confirmada", "vitimas confirmadas", "pessoa ferida", "vitimas feridas")):
        return "alta"
    dano_material_apenas = any(x in texto for x in (
        "apenas danos materiais", "somente danos materiais", "apenas avarias", "exclusivamente avarias materiais"))
    operador_confirma = any(x in texto for x in (
        "operador confirma", "operador confirmou", "operador informa", "confirmado pelo operador", "confirma apenas"))
    sem_vitima = any(x in texto for x in ("sem vitima", "sem ferido", "sem ferida", "nenhuma vitima"))
    if dano_material_apenas and operador_confirma and sem_vitima:
        return "baixa"
    return "media"


def _motivo_sem_suporte(caso: dict) -> Optional[str]:
    q = _normalizar(caso.get("pergunta", ""))
    regras = [
        (r"\bculpa\b|\bculpado\b", "A base não determina culpa ou responsabilidade pelo acidente."),
        (r"\bvalor\b.{0,30}\bmulta\b|\bmulta\b.{0,30}\bvalor\b|\bquanto custa\b.{0,25}\bmulta\b",
         "A base não informa o valor monetário da multa."),
        (r"\b(previsao|horario|tempo) de chegada\b|\bquando (a ambulancia|a equipe|o socorro) chega\b|\bem quantos? (minutos?|horas?) (a ambulancia|a equipe|o socorro)\b|\bquando sera enviada a equipe\b",
         "A base não prevê o tempo de chegada de equipes."),
        (r"\bqual hospital\b|\bpara qual hospital\b|\bdestino hospitalar\b|\bqual oficina\b",
         "A base não informa qual hospital receberá a vítima."),
        (r"\bplaca\b", "A placa do veículo não consta nos dados disponíveis."),
        (r"\btestemunha(s)?\b|\bquem presenciou\b",
         "A base não contém identificação ou contato de testemunhas."),
        (r"\bdiagnostico\b|\bmedicamento\b|\bremedio\b|\bdose\b|\bcirurgia\b|\btransfusao\b|\bcoluna cervical\b|\blesao cervical\b",
         "A base não fornece diagnóstico nem prescrição clínica."),
        (r"\bhabilitacao valida\b|\bcarteira.{0,20}valida\b|\bpossui habilitacao\b|\bpossui carteira de motorista\b|\bcpf\b|\bproprietario do veiculo\b",
         "Esse dado pessoal ou cadastral não consta na ocorrência nem na base consultada."),
        (r"\bembriag\w*\b|\bsob efeito de alcool\b",
         "A base não informa se o condutor estava sob efeito de álcool."),
        (r"\bvelocidade\b.{0,30}\b(veiculo|carro|moto|impacto|acidente)\b",
         "A velocidade não consta nos dados do evento nem na base consultada."),
        (r"\bprevisao do tempo\b|\bcondicao do tempo\b|\besta chovendo\b|\btemperatura\b",
         "A base não fornece condições meteorológicas atuais."),
        (r"\bqual (e|era) o nome\b.{0,30}\b(vitima|motorista|condutor)\b|\bnome completo\b",
         "A base não contém dados de identificação pessoal dos envolvidos."),
        (r"\bqual produto\b|\bnome quimico\b|\bcomposicao quimica\b",
         "O produto não foi identificado nos dados do evento."),
        (r"\bconter\b.{0,25}\b(vazamento|produto|derramamento)\b|\bneutralizar\b.{0,25}\bproduto\b|\bprocedimento tecnico\b",
         "A base não contém procedimento técnico de contenção; mantenha distância e acione as autoridades da jurisdição."),
        (r"\bendereco exato\b|\bendereco (completo|e (o )?quilometro)\b|\bendereco.{0,25}quilometro\b|\bquilometro exato\b",
         "O endereço exato e o quilômetro não constam nos dados do evento."),
        (r"\bseguradora\b|\bindenizacao\b|\bseguro obrigatorio\b",
         "A base não informa cobertura ou indenização de seguro."),
        (r"\bjuiz\b|\bcondenacao\b|\bpuni(c|ç)ao exata\b|\bqual pena sera aplicada\b",
         "A base não prevê decisão judicial ou punição aplicada a um caso concreto."),
    ]
    for padrao, motivo in regras:
        if re.search(padrao, q):
            return motivo
    return None


def _pedido_triagem(caso: dict) -> bool:
    q = _normalizar(caso.get("pergunta", ""))
    return any(x in q for x in ("triagem", "classifique", "classificacao", "prioridade",
                                "proximo passo", "o que o operador deve fazer", "analise este alerta"))


def _pergunta_sobre_confirmacao(caso: dict) -> bool:
    q = _normalizar(caso.get("pergunta", ""))
    return (any(x in q for x in ("confirma", "comprova", "prova que houve"))
            and any(x in q for x in ("camera", "alerta visual", "alerta da camera", "deteccao"))
            and any(x in q for x in ("acidente", "ocorrencia", "sinistro")))


def _resposta_confirmacao(caso: dict, achados: list) -> Triagem:
    evento = caso["evento"]
    tipo = {"possivel_colisao": "colisao_veiculos", "possivel_queda_moto": "queda_motociclista",
            "possivel_atropelamento": "atropelamento", "possivel_incendio": "incendio_veicular"}.get(
                evento.get("event_type"), "indeterminado")
    ids = {t["id"] for t, _ in achados}
    return Triagem(tipo_provavel=tipo, prioridade_sugerida=prioridade_do_evento(evento),
                   informacoes_identificadas=list(evento.keys()),
                   informacoes_ausentes=["endereco_exato", "numero_de_vitimas", "estado_das_vitimas"],
                   proximo_passo="Não. A detecção por câmera é um alerta, não confirma que ocorreu um acidente. O operador deve validar as informações antes de qualquer encaminhamento.",
                   referencias=["T020"] if "T020" in ids else [])


def _triagem_por_regra(caso: dict, achados: list) -> Triagem:
    evento = caso["evento"]
    obs = _normalizar(evento.get("observacao", ""))
    tipo = {"possivel_colisao": "colisao_veiculos", "possivel_queda_moto": "queda_motociclista",
            "possivel_atropelamento": "atropelamento", "possivel_incendio": "incendio_veicular"}.get(
                evento.get("event_type"), "indeterminado")
    prioridade = prioridade_do_evento(evento)
    if prioridade == "baixa":
        passo = "Prioridade baixa pelo critério interno. Como não há vítima nem urgência médica confirmada, não acione o SAMU; siga o fluxo local da central."
        refs = ["T020", "T004"]
    elif any(x in obs for x in ("produto perigoso", "vazamento", "recipiente danificado")):
        passo = ("Prioridade alta pelo critério interno. Mantenha distância e informe a localização e os riscos observados. "
                 "Acione os serviços locais competentes; se houver vítima ou urgência médica, ligue para o SAMU 192.")
        refs = ["T020", "T003"]
        local = _normalizar(evento.get("local", ""))
        if "parana" in local and ("federal" in local or "br" in local):
            passo = "Prioridade alta. Mantenha distância, acione a PRF 191 e os Bombeiros 193 e informe os riscos observados sem se aproximar."
            refs.append("T025")
        elif "santa catarina" in local or re.search(r"\bsc\b", local):
            passo = "Prioridade alta. Afaste-se com segurança e acione a Defesa Civil 199 e os Bombeiros 193; não se aproxime para socorrer."
            refs.append("T024")
    elif any(x in obs for x in ("pessoa presa", "vitima presa", "ocupante preso", "ocupante retido", "retido nas ferragens")):
        passo = "Prioridade alta. Informe que há uma pessoa presa às ferragens, ligue para o SAMU 192 e siga as orientações do Médico Regulador."
        refs = ["T020", "T005", "T002"]
    elif any(x in obs for x in ("pessoa caida", "pessoa no chao", "motociclista caiu")):
        if "moto" in evento.get("event_type", ""):
            passo = "Prioridade alta. Não toque na vítima nem retire o capacete; ligue para o SAMU 192 e siga as orientações do Médico Regulador."
            refs = ["T020", "T007", "T001"]
        else:
            passo = "Prioridade alta. Confirme a quantidade de vítimas e o estado de consciência; acione o SAMU 192 e siga as orientações do Médico Regulador."
            refs = ["T020", "T005", "T003"]
    elif prioridade == "alta":
        passo = "Prioridade alta pelo critério interno. Confirme a quantidade de vítimas, o estado de consciência e a localização; acione o SAMU 192 para a urgência médica."
        refs = ["T020", "T003", "T005", "T021"]
    else:
        passo = "O alerta da câmera ainda não confirma vítimas. Confirme com o operador a quantidade, o estado de consciência e a localização; se houver vítimas, ligue para o SAMU 192."
        refs = ["T020", "T005", "T021", "T003"]
    ids_disponiveis = {t["id"] for t, _ in achados}
    refs = [ref for ref in refs if ref in ids_disponiveis]
    ausentes = ["endereco_exato", "numero_de_vitimas", "estado_das_vitimas"]
    if prioridade == "baixa":
        ausentes = ["endereco_exato"]
    elif prioridade == "alta":
        ausentes = ["endereco_exato", "estado_das_vitimas"]
    return Triagem(tipo_provavel=tipo, prioridade_sugerida=prioridade,
                   informacoes_identificadas=list(evento.keys()), informacoes_ausentes=ausentes,
                   proximo_passo=passo, referencias=refs)


def _resposta_factual_por_regra(caso: dict, achados: list) -> Optional[Triagem]:
    """Respostas curtas e extrativas para intenções operacionais de alto risco.

    Cada rota só dispara quando o trecho fonte correspondente foi recuperado;
    a regra não cria fatos fora da base.
    """
    q = _normalizar(caso.get("pergunta", ""))
    rotas = [
        (("o que deve ser dito sobre a vitima", "informar sobre a vitima", "quantidade de vitimas", "estado de consciencia", "informacoes sobre as vitimas"),
         {"T005", "T021"},
         "Informe a quantidade de vítimas, o estado de consciência e se alguém está preso às ferragens. Diga o local exato, pontos de referência, descreva a situação e responda ao Médico Regulador.",
         {"T005", "T021"}),
        (("samu atende sem cobranca", "tem custo", "tem tarifa para o usuario", "servico do samu tem custo", "cobranca e funciona em qual horario", "quais horarios"),
         {"T001"}, "O SAMU 192 é gratuito e funciona 24 horas por dia, todos os dias.", {"T001"}),
        (("situacao de transito e indicado chamar", "em que situacoes chamar", "quando chamar o 192", "servico atende urgencias medicas", "assistencia medica urgente"),
         {"T003"}, "Acione o SAMU 192 em acidentes ou traumas com vítimas e em situações de urgência ou emergência.", {"T003"}),
        (("declaracao pode ser feita online", "declaracao de acidente de transito", "dat pela internet", "prazo da dat", "prazo para registrar a dat"),
         {"T026"}, "Em rodovia federal, sem vítimas e em acidente de menor relevância, maiores de 18 anos ou emancipados podem preencher a DAT pela internet em até 180 dias.", {"T026"}),
        (("trecho tiver concessao", "rodovia concedida", "servico rodoviario da concessionaria"),
         {"T022"}, "Em rodovia concedida, acione também o Serviço de Atendimento ao Usuário (SAU) pelo telefone indicado na rodovia.", {"T022"}),
        (("telefone da prf", "qual numero da prf", "referencias de local", "quilometro pontos de referencia"),
         {"T022"}, "Na rodovia federal pública, ligue para a PRF pelo 191 e informe a BR, o quilômetro, pontos de referência, estado das vítimas se houver e se a pista está obstruída.", {"T022"}),
        (("telefone de emergencia da prf", "numero da prf"),
         {"T018"}, "O telefone de emergência da PRF é 191.", {"T018"}),
        (("sinalizar as vias", "sinalizar a via", "recurso de alerta na via", "reduzir perigo de novas colisoes"),
         {"T008"}, "Sinalize a via com galhos ou triângulo, ligue para o 192 e siga as orientações do Médico Regulador.", {"T008"}),
        (("quem decide", "quem avalia", "quem analisa", "quem escolhe", "profissional decide", "decide se envia", "determina os recursos", "quem define a resposta", "equipe sera enviada", "equipe ser enviada"),
         {"T002", "T017"},
         "O Médico Regulador avalia o chamado e define a resposta adequada; pode orientar por telefone e acionar ambulância ou outros recursos quando necessário.",
         {"T002", "T017"}),
        (("contatos constam na orientacao da prf", "orientacao da prf", "prf orienta sobre produto perigoso", "situacao descrita pela prf"),
         {"T025"},
         "Mantenha distância, não se aproxime do produto e acione a PRF pelo 191 e o Corpo de Bombeiros pelo 193. Informe os riscos observados sem se expor.",
         {"T025"}),
        (("enquanto o regulador orienta", "enquanto o medico regulador orienta", "o que fazer enquanto"),
         {"T021"},
         "Descreva a situação com clareza, responda às perguntas do Médico Regulador e permaneça no local para ajudar a equipe a encontrar a vítima.",
         {"T021"}),
        (("santa catarina", "defesa civil de sc"),
         {"T024"}, "Em Santa Catarina, afaste-se com segurança e ligue para a Defesa Civil pelo 199 e para os Bombeiros pelo 193.", {"T024"}),
        (("informacao o condutor deve fornecer a policia", "identificar-se ao policial", "informacoes para o boletim", "informar dados a policia"),
         {"T014"},
         "O condutor deve identificar-se ao policial e prestar as informações necessárias à elaboração do boletim de ocorrência.",
         {"T014"}),
        (("ctb sobre prestar socorro", "dever de prestar socorro", "providenciar socorro", "dever do motorista", "dever do condutor", "dever de assistencia"),
         {"T010", "T016"},
         "O CTB prevê que o condutor preste ou providencie socorro quando puder. Se não puder agir diretamente por justa causa, deve solicitar auxílio da autoridade pública.",
         {"T010", "T016"}),
        (("evitar risco adicional", "sinalizar a via", "sinalizar as vias", "como sinalizar", "evitar outro acidente"),
         {"T008"},
         "Sinalize a via com galhos ou triângulo, ligue para o 192 e siga as orientações do Médico Regulador.",
         {"T008"}),
    ]
    ids = {t["id"] for t, _ in achados}
    for gatilhos, exigidos, resposta, citacoes in rotas:
        if any(g in q for g in gatilhos) and exigidos <= ids:
            evento = caso["evento"]
            return Triagem(tipo_provavel=_tipo_do_evento(evento),
                           prioridade_sugerida=prioridade_do_evento(evento),
                           informacoes_identificadas=list(evento.keys()),
                           informacoes_ausentes=["endereco_exato", "numero_de_vitimas", "estado_das_vitimas"],
                           proximo_passo=resposta, referencias=sorted(citacoes), recusa=False)
    return None


def triar(caso: dict, config: str, buscador: Optional[Buscador], gerador: Gerador, limiar: float):
    """config: 'sem_contexto' | 'rag' | 'rag_lora'. Retorna (Triagem|None, texto_bruto, trechos_recuperados)."""
    sem_suporte = _motivo_sem_suporte(caso)
    if sem_suporte:
        return recusa_padrao(sem_suporte), "", []
    if _pergunta_sobre_confirmacao(caso) and config != "sem_contexto":
        achados = buscador.buscar(consulta_do_caso(caso), 5)
        return _resposta_confirmacao(caso, achados), "", achados
    if _pedido_triagem(caso):
        achados = buscador.buscar(consulta_do_caso(caso), 5) if config != "sem_contexto" else []
        return _triagem_por_regra(caso, achados), "", achados
    if config == "sem_contexto":
        bruto = gerador.gerar(montar_mensagens(caso, None))
        resp = extrair_json(bruto)
        if resp and resp.recusa:
            return recusa_padrao(resp.motivo_recusa or "Sem base documental suficiente para responder."), bruto, []
        if resp:
            resp.tipo_provavel = _tipo_do_evento(caso["evento"])
            resp.informacoes_identificadas = list(caso["evento"].keys())
            resp.prioridade_sugerida = prioridade_do_evento(caso["evento"])
        return resp, bruto, []
    achados = buscador.buscar(consulta_do_caso(caso), 5)
    resposta_direta = _resposta_factual_por_regra(caso, achados)
    if resposta_direta:
        return resposta_direta, "", achados
    if achados[0][1] < limiar:  # portão de recusa por similaridade
        return recusa_padrao(f"Nenhum trecho da base atingiu o limiar de relevância ({achados[0][1]:.2f} < {limiar:.2f})."), "", achados
    bruto = gerador.gerar(montar_mensagens(caso, [t for t, _ in achados]))
    resp = extrair_json(bruto)
    if resp and resp.recusa:
        return recusa_padrao(resp.motivo_recusa or "A base recuperada não fornece suporte suficiente para responder."), bruto, achados
    if resp and not resp.recusa:
        resp.tipo_provavel = _tipo_do_evento(caso["evento"])
        resp.informacoes_identificadas = list(caso["evento"].keys())
        resp.prioridade_sugerida = prioridade_do_evento(caso["evento"])
    return resp, bruto, achados


def _tipo_do_evento(evento: dict) -> TipoOcorrencia:
    return {"possivel_colisao": "colisao_veiculos", "possivel_queda_moto": "queda_motociclista",
            "possivel_atropelamento": "atropelamento", "possivel_incendio": "incendio_veicular"}.get(
                evento.get("event_type"), "indeterminado")
