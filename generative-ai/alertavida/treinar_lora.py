"""Fine-tuning LoRA (formato de saída + recusa) usando casos sintéticos.
Os casos de treino NÃO podem se repetir no conjunto de teste (evitar vazamento).
Uso: python -m alertavida.treinar_lora"""
import json
import argparse
from pathlib import Path

import torch
from peft import LoraConfig, get_peft_model
from transformers import AutoModelForCausalLM, AutoTokenizer, Trainer, TrainingArguments

from .nucleo import ADAPTADOR, LLM_ID, RAIZ, Buscador, carregar_jsonl, consulta_do_caso, montar_mensagens

MAXLEN = 1024


def alvo_json(c: dict) -> str:
    g = c["gabarito"]
    if c["consta"]:
        d = {"tipo_provavel": g["tipo_provavel"], "prioridade_sugerida": g["prioridade_sugerida"],
             "informacoes_identificadas": list(c["evento"].keys()),
             "informacoes_ausentes": g["informacoes_ausentes"], "proximo_passo": g["proximo_passo"],
             "referencias": g["trechos"], "recusa": False, "motivo_recusa": None}
    else:
        d = {"tipo_provavel": None, "prioridade_sugerida": None, "informacoes_identificadas": [],
             "informacoes_ausentes": [], "proximo_passo": None, "referencias": [], "recusa": True,
             "motivo_recusa": "A base de conhecimento não contém informação suficiente para responder."}
    return json.dumps(d, ensure_ascii=False)


def main(caminho_dados=None, caminho_saida=None, epocas=3, taxa_aprendizado=2e-4):
    tok = AutoTokenizer.from_pretrained(LLM_ID)
    buscador = Buscador()
    casos = carregar_jsonl(caminho_dados or RAIZ / "avaliacao" / "casos_treino.jsonl")
    dados = []
    for c in casos:
        encontrados = [t for t, _ in buscador.buscar(consulta_do_caso(c), 3)]
        ids = {t["id"] for t in encontrados}
        ouro = {t["id"]: t for t in buscador.trechos if t["id"] in c.get("gabarito", {}).get("trechos", [])}
        trechos = encontrados + [t for id_, t in ouro.items() if id_ not in ids]
        prompt = tok.apply_chat_template(montar_mensagens(c, trechos), tokenize=False, add_generation_prompt=True)
        p = tok(prompt, add_special_tokens=False).input_ids
        a = tok(alvo_json(c) + tok.eos_token, add_special_tokens=False).input_ids
        dados.append({"input_ids": (p + a)[:MAXLEN], "labels": ([-100] * len(p) + a)[:MAXLEN]})
    del buscador

    def coletor(lote):
        m = max(len(x["input_ids"]) for x in lote)
        pad = tok.pad_token_id
        return {"input_ids": torch.tensor([x["input_ids"] + [pad] * (m - len(x["input_ids"])) for x in lote]),
                "attention_mask": torch.tensor([[1] * len(x["input_ids"]) + [0] * (m - len(x["input_ids"])) for x in lote]),
                "labels": torch.tensor([x["labels"] + [-100] * (m - len(x["labels"])) for x in lote])}

    cuda = torch.cuda.is_available()
    bf16 = cuda and torch.cuda.is_bf16_supported()
    dtype = torch.bfloat16 if bf16 else torch.float16 if cuda else torch.float32
    modelo = AutoModelForCausalLM.from_pretrained(LLM_ID, torch_dtype=dtype)
    modelo = get_peft_model(modelo, LoraConfig(r=16, lora_alpha=32, lora_dropout=0.05, task_type="CAUSAL_LM",
                                               target_modules=["q_proj", "k_proj", "v_proj", "o_proj"]))
    modelo.print_trainable_parameters()
    args = TrainingArguments(output_dir=str(RAIZ / "modelos" / "_tmp"), per_device_train_batch_size=1,
                             gradient_accumulation_steps=8, num_train_epochs=epocas, learning_rate=taxa_aprendizado,
                             logging_steps=5, save_strategy="no", report_to="none",
                             bf16=bf16, fp16=cuda and not bf16, remove_unused_columns=False)
    Trainer(model=modelo, args=args, train_dataset=dados, data_collator=coletor).train()
    destino = caminho_saida or (RAIZ / "modelos" / "lora_alertavida_retreinado")
    Path(destino).mkdir(parents=True, exist_ok=True)
    modelo.save_pretrained(str(destino))
    print("Adaptador salvo em", destino)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dados", default=str(RAIZ / "avaliacao" / "casos_treino.jsonl"))
    parser.add_argument("--saida", default=str(RAIZ / "modelos" / "lora_alertavida_retreinado"),
                        help="diretório do adaptador novo; por padrão não sobrescreve o modelo padrão")
    parser.add_argument("--epocas", type=float, default=3)
    parser.add_argument("--lr", type=float, default=2e-4)
    args = parser.parse_args()
    main(args.dados, args.saida, args.epocas, args.lr)
