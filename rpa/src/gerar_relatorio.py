from pathlib import Path
import json

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle


BASE_DIR = Path(__file__).resolve().parents[1]
RESULTADO = BASE_DIR / "output" / "alertas_priorizados.json"
SAIDA = BASE_DIR / "docs" / "Relatorio_Tecnico_RPA.pdf"


def gerar() -> Path:
    if not RESULTADO.exists():
        raise FileNotFoundError("Execute o RPA antes de gerar o relatório.")
    dados = json.loads(RESULTADO.read_text(encoding="utf-8"))

    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    documento = SimpleDocTemplate(
        str(SAIDA),
        pagesize=A4,
        rightMargin=1.8 * cm,
        leftMargin=1.8 * cm,
        topMargin=1.8 * cm,
        bottomMargin=1.8 * cm,
        title="Relatório Técnico RPA - AlertaVida",
    )
    estilos = getSampleStyleSheet()
    estilos.add(ParagraphStyle(
        name="TituloCentral",
        parent=estilos["Title"],
        alignment=TA_CENTER,
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#8B1538"),
    ))

    conteudo = [
        Paragraph("AlertaVida", estilos["TituloCentral"]),
        Paragraph("Relatório Técnico — Automação RPA", estilos["TituloCentral"]),
        Spacer(1, 0.7 * cm),
        Paragraph("<b>Objetivo</b>", estilos["Heading2"]),
        Paragraph(
            "Automatizar a triagem operacional dos alertas produzidos pelo AlertaVida, "
            "validando registros, removendo duplicidades e classificando prioridades "
            "para apoiar a revisão humana.",
            estilos["BodyText"],
        ),
        Spacer(1, 0.3 * cm),
        Paragraph("<b>Fontes de entrada</b>", estilos["Heading2"]),
        Paragraph(
            "API pública do MVP pela rota <i>/api/alertas</i> ou arquivo CSV de demonstração.",
            estilos["BodyText"],
        ),
        Paragraph("<b>Regras de negócio</b>", estilos["Heading2"]),
        Paragraph(
            "ALTA: status PENDENTE e confiança maior ou igual a 85%. "
            "Média: PENDENTE ou CONFIRMADO e confiança maior ou igual a 70%. "
            "Baixa: demais combinações.",
            estilos["BodyText"],
        ),
        Paragraph("<b>Segurança e LGPD</b>", estilos["Heading2"]),
        Paragraph(
            "A demonstração usa identificadores simulados. O componente não coleta CPF, telefone, "
            "endereço pessoal ou dados médicos e não realiza acionamento de serviços de emergência.",
            estilos["BodyText"],
        ),
        Spacer(1, 0.4 * cm),
    ]

    linhas = [
        ["Indicador", "Resultado"],
        ["Identificador da execução", str(dados.get("execution_id", ""))],
        ["Registros de entrada", str(dados.get("total_entrada", 0))],
        ["Registros processados", str(dados.get("total_processados", 0))],
        ["Registros inválidos", str(dados.get("invalidos", 0))],
        ["Registros duplicados", str(dados.get("duplicados", 0))],
        ["Prioridade alta", str(dados.get("prioridades", {}).get("ALTA", 0))],
        ["Prioridade média", str(dados.get("prioridades", {}).get("MEDIA", 0))],
        ["Prioridade baixa", str(dados.get("prioridades", {}).get("BAIXA", 0))],
        ["Gerado em", str(dados.get("gerado_em", ""))],
    ]
    tabela = Table(linhas, colWidths=[6 * cm, 8.5 * cm])
    tabela.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#8B1538")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#F7F7F7")),
    ]))
    conteudo.append(tabela)

    conteudo.extend([
        Spacer(1, 0.5 * cm),
        Paragraph("<b>Exceções tratadas</b>", estilos["Heading2"]),
        Paragraph(
            "Arquivo ausente, API indisponível após novas tentativas, resposta inválida, "
            "campos obrigatórios vazios, status desconhecido, confiança fora do intervalo "
            "0–1 e eventos duplicados.",
            estilos["BodyText"],
        ),
        Paragraph("<b>Auditoria e integrações</b>", estilos["Heading2"]),
        Paragraph(
            "A execução gera JSON e CSV por substituição atômica e registra eventos em "
            "<i>rpa/logs/processamento.jsonl</i>. O backend disponibiliza o resultado em "
            "<i>GET /api/rpa/ultima-execucao</i>; a decisão final permanece sob validação humana.",
            estilos["BodyText"],
        ),
    ])
    documento.build(conteudo)
    return SAIDA


if __name__ == "__main__":
    print(gerar())
