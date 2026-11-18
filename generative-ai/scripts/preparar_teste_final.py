"""Prepara um teste por paráfrases dos fatos já documentados.
Execute uma única vez depois de congelar regras e limiar; não ajuste com base nos resultados.
"""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
QUESTOES={
"x01":"Ao solicitar o 192, que informações sobre as vítimas devo transmitir?",
"x02":"Em um acidente de moto, é recomendado tirar o capacete da pessoa?",
"x03":"A imagem detectada pela câmera confirma por si só que houve um acidente?",
"x04":"Se alguém ficou preso no veículo, que prioridade o critério do projeto indica?",
"x05":"Que serviço atende urgências médicas e qual número devo ligar?",
"x06":"Numa BR, para comunicar um acidente à PRF, qual telefone usar e que referências passar?",
"x07":"Qual declaração de acidente pode ser preenchida pela internet e qual o prazo?",
"x08":"Quem avalia o chamado e decide se envia uma equipe?",
"x09":"Com danos somente nos veículos e sem feridos, que nível de prioridade aplicar?",
"x10":"Segundo a orientação da PRF para rodovias federais do Paraná, quais contatos acionar e como se proteger?",
"x11":"Em Santa Catarina, quais telefones usar diante de uma emergência com produto perigoso?",
"x12":"Enquanto o Médico Regulador conduz a ligação, como devo colaborar?",
"x13":"O SAMU tem custo para quem liga?",
"x14":"O que o motorista envolvido deve informar ao policial para o boletim?",
"x15":"O CTB exige prestar ou providenciar socorro à vítima?",
"x16":"Como sinalizar a via para evitar perigo de outro acidente?",
"x17":"Qual o endereço e o quilômetro exatos do alerta?",
"x18":"A vítima teve lesão na coluna cervical?",
"x19":"Qual oficina fará o reparo do veículo?",
"x20":"O motorista que aparece no vídeo tem carteira de habilitação válida?",
"x21":"Em quantos minutos a ambulância chegará ao local?",
"x22":"Como conter com segurança o produto químico que vazou?",
"x23":"Qual será o valor pago pela seguradora pela perda do veículo?",
"x24":"Qual o nome completo da pessoa acidentada?",
"x25":"Quem presenciou a colisão e pode servir de testemunha?",
"x26":"Qual é a condição do tempo neste ponto da rodovia agora?",
"x27":"A que velocidade cada carro trafegava antes do choque?",
"x28":"Que medicamento devo administrar e em qual dose?",
"x29":"Qual pena o juiz aplicará ao condutor neste processo?",
"x30":"Para qual hospital a vítima será encaminhada?",
"x31":"Qual a placa do carro envolvido no acidente?",
"x32":"A pessoa ferida vai precisar de cirurgia?"}
source=ROOT/"avaliacao"/"casos_teste_desenvolvimento.jsonl"
rows=[json.loads(x) for x in source.read_text(encoding="utf8").splitlines() if x.strip()]
for row in rows:
    row["id"]="z"+row["id"][1:]
    row["pergunta"]=QUESTOES[row["id"].replace("z","x",1)]
    if row["id"]=="zx13": row["gabarito"]["proximo_passo_contem"]=["gratuitos","custo"]
dest=ROOT/"avaliacao"/"casos_teste_parafrase.jsonl"
dest.write_text("".join(json.dumps(r,ensure_ascii=False)+"\n" for r in rows),encoding="utf8")
print(f"{dest.name}: {len(rows)} exemplos; {sum(r['consta'] for r in rows)} respondíveis e {sum(not r['consta'] for r in rows)} sem suporte")
