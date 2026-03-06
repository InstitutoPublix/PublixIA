import streamlit as st
import io
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
import pandas as pd
import math
import openai
import streamlit.components.v1 as components
import os
import uuid
import html
import base64
from datetime import datetime
from pathlib import Path
import smtplib
import ssl
from email.message import EmailMessage
import gspread
from gspread.exceptions import SpreadsheetNotFound, WorksheetNotFound
from google.oauth2.service_account import Credentials

# -------------------
# CONFIG GERAIS
# -------------------
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

SHEET_NAME = "Observatório - Respostas"
WORKSHEET_NAME = "respostas"

st.set_page_config(
    page_title="Observatório da maturidade em governança para resultados: Faça seu diagnóstico inicial, com suporte de um copiloto de IA",
    layout="centered"
)

LOGO_PATH = Path("publix_logo.png")


# -------------------
# UTILITÁRIOS DE CONFIG
# -------------------
def get_config_value(key: str):
    value = os.getenv(key)
    if value in (None, ""):
        try:
            value = st.secrets.get(key)
        except Exception:
            value = None
    if isinstance(value, str):
        value = value.strip().strip('"').strip("'")
    return value


def formatar_resumo_email(registro: dict, medias_dim: dict) -> str:
    contato_msg = "Sim" if bool(registro.get("deseja_contato_diagnostico_completo", False)) else "Não"

    linhas = []
    linhas.append("Olá,")
    linhas.append("")
    linhas.append("Segue o resumo do seu diagnóstico prévio no Observatório da maturidade em governança para resultados.")
    linhas.append("")
    linhas.append("IDENTIFICAÇÃO")
    linhas.append(f"- Instituição: {registro.get('instituicao', '')}")
    linhas.append(f"- Poder: {registro.get('poder', '')}")
    linhas.append(f"- Esfera: {registro.get('esfera', '')}")
    linhas.append(f"- Estado (UF): {registro.get('estado_uf', '')}")
    linhas.append("")
    linhas.append("RESPONDENTE")
    linhas.append(f"- Nome: {registro.get('nome_respondente', '')}")
    linhas.append(f"- E-mail: {registro.get('email_respondente', '')}")
    linhas.append(f"- Área / Unidade: {registro.get('area_unidade', '')}")
    linhas.append(f"- Cargo / Função: {registro.get('cargo_funcao', '')}")
    linhas.append(f"- Deseja contato para diagnóstico completo: {contato_msg}")
    linhas.append("")
    linhas.append("RESULTADO GERAL")
    linhas.append(f"- Score geral: {registro.get('score_geral', '')}")
    linhas.append(f"- Nível de maturidade: {registro.get('nivel_maturidade', '')}")
    linhas.append(f"- ID do diagnóstico: {registro.get('id_resposta', '')}")
    linhas.append("")

    if medias_dim:
        linhas.append("ANÁLISE POR DIMENSÃO")
        for dim, media in medias_dim.items():
            base = observatorio_means.get(dim)
            if base is None:
                continue
            diff = round(media - base, 2)
            if media < 1.5:
                mensagem = "Prioridade alta: estruturar fundamentos da agenda estratégica (objetivos, metas, cenários e planos de ação)."
            elif media < 2.0:
                mensagem = "Prioridade média: fortalecer consistência, alinhamento e institucionalização das práticas estratégicas."
            else:
                mensagem = "Bom nível relativo: foco em consolidar, padronizar e ampliar a disseminação interna das práticas estratégicas."

            linhas.append(f"- {dim}:")
            linhas.append(f"  • Média da organização: {media:.2f}")
            linhas.append(f"  • Média da base: {base:.2f}")
            linhas.append(f"  • Diferença: {diff:+.2f}")
            linhas.append(f"  • Leitura rápida: {mensagem}")
            linhas.append("")

    linhas.append("Este é um diagnóstico prévio. Caso tenha assinalado interesse, nossa equipe poderá entrar em contato para um diagnóstico completo.")
    linhas.append("")
    linhas.append("Instituto Publix")

    return "\n".join(linhas)


def gerar_pdf_relatorio(registro: dict, medias_dim: dict) -> bytes:
    """Gera o PDF do relatório fiel ao layout da tela, sem ID do diagnóstico."""
    from reportlab.graphics.shapes import Drawing, Rect
    from reportlab.graphics import renderPDF

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18*mm,
        leftMargin=18*mm,
        topMargin=16*mm,
        bottomMargin=16*mm,
    )

    PAGE_W = A4[0] - 36*mm  # largura útil

    amarelo      = colors.HexColor("#FFC728")
    amarelo_grad = colors.HexColor("#FFB300")
    cinza_claro  = colors.HexColor("#f8f8f8")
    cinza_borda  = colors.HexColor("#e0e0e0")
    cinza_texto  = colors.HexColor("#444444")
    cinza_muted  = colors.HexColor("#666666")
    preto        = colors.HexColor("#111111")

    def s(name, **kw):
        base = ParagraphStyle(name, fontName="Helvetica", fontSize=9,
                              textColor=cinza_texto, leading=13)
        for k, v in kw.items():
            setattr(base, k, v)
        return base

    st_titulo    = s("titulo",   fontName="Helvetica-Bold", fontSize=13, textColor=preto, leading=17, spaceAfter=2)
    st_sub       = s("sub",      fontSize=8,  textColor=colors.HexColor("#555555"), leading=12, spaceAfter=2)
    st_secao     = s("secao",    fontName="Helvetica-Bold", fontSize=10, textColor=preto, spaceBefore=8, spaceAfter=5)
    st_label     = s("label",    fontSize=7.5, textColor=colors.HexColor("#888888"), leading=11)
    st_valor     = s("valor",    fontName="Helvetica-Bold", fontSize=9, textColor=preto, leading=13)
    st_normal    = s("normal",   fontSize=8.5, textColor=cinza_texto, leading=13)
    st_muted     = s("muted",    fontSize=8,   textColor=cinza_muted,  leading=12)
    st_rodape    = s("rodape",   fontSize=7.5, textColor=colors.HexColor("#aaaaaa"), alignment=TA_RIGHT)
    st_badge_on  = s("badge_on", fontName="Helvetica-Bold", fontSize=7.5,
                     textColor=preto, backColor=colors.HexColor("#fff3c4"),
                     borderColor=amarelo, borderWidth=0.5, borderPadding=3)
    st_badge_off = s("badge_off", fontSize=7.5, textColor=colors.HexColor("#888888"),
                     backColor=colors.white, borderColor=cinza_borda,
                     borderWidth=0.5, borderPadding=3)

    story = []

    # ── Faixa amarela topo ──────────────────────────────────────────────
    story.append(Table([[""]], colWidths=[PAGE_W], rowHeights=[4],
        style=TableStyle([("BACKGROUND",(0,0),(-1,-1), amarelo),
                          ("LINEABOVE",(0,0),(-1,-1),0,colors.white)])))
    story.append(Spacer(1, 5*mm))

    # ── Cabeçalho: título + logo ────────────────────────────────────────
    # Logo — tenta carregar do arquivo
    logo_b64 = file_to_base64(LOGO_PATH)
    if logo_b64:
        from reportlab.platypus import Image as RLImage
        logo_data = base64.b64decode(logo_b64)
        logo_buf = io.BytesIO(logo_data)
        logo_img = RLImage(logo_buf, width=28*mm, height=18*mm, kind="proportional")
        header_data = [[
            [Paragraph("Relatório de Diagnóstico — Agenda Estratégica", st_titulo),
             Paragraph("Observatório de Governança para Resultados: Inteligência Artificial", st_sub),
             Paragraph(f"Emitido em: {registro.get('data_hora','')}", st_sub)],
            logo_img
        ]]
        t_header = Table(header_data, colWidths=[PAGE_W - 32*mm, 32*mm])
        t_header.setStyle(TableStyle([
            ("VALIGN",(0,0),(-1,-1),"TOP"),
            ("ALIGN",(1,0),(1,0),"RIGHT"),
            ("LEFTPADDING",(0,0),(-1,-1),0),
            ("RIGHTPADDING",(0,0),(-1,-1),0),
            ("TOPPADDING",(0,0),(-1,-1),0),
            ("BOTTOMPADDING",(0,0),(-1,-1),0),
        ]))
    else:
        t_header = Table([[
            [Paragraph("Relatório de Diagnóstico — Agenda Estratégica", st_titulo),
             Paragraph("Observatório de Governança para Resultados", st_sub),
             Paragraph(f"Emitido em: {registro.get('data_hora','')}", st_sub)]
        ]], colWidths=[PAGE_W])

    story.append(t_header)
    story.append(Spacer(1, 3*mm))
    story.append(HRFlowable(width="100%", thickness=1, color=cinza_borda, spaceAfter=5))

    # ── Identificação institucional ─────────────────────────────────────
    story.append(Paragraph("Identificação institucional", st_secao))

    half = PAGE_W / 2 - 1*mm
    def kpi_cell(label, valor):
        return [Paragraph(label, st_label), Paragraph(str(valor), st_valor)]

    t_inst = Table([
        [kpi_cell("Instituição", registro.get("instituicao","")),
         kpi_cell("Classificação", f"{registro.get('poder','')} | {registro.get('esfera','')} | {registro.get('estado_uf','')}")],
        [kpi_cell("Respondente", registro.get("nome_respondente","")),
         kpi_cell("Cargo / contato", f"{registro.get('cargo_funcao','')} | {registro.get('email_respondente','')}")],
    ], colWidths=[half, half])
    t_inst.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1), cinza_claro),
        ("BOX",(0,0),(-1,-1), 0.5, cinza_borda),
        ("INNERGRID",(0,0),(-1,-1), 0.5, cinza_borda),
        ("LINEBEFORE",(0,0),(0,-1), 3, amarelo),
        ("LINEBEFORE",(1,0),(1,-1), 3, amarelo),
        ("TOPPADDING",(0,0),(-1,-1), 6),
        ("BOTTOMPADDING",(0,0),(-1,-1), 6),
        ("LEFTPADDING",(0,0),(-1,-1), 8),
        ("RIGHTPADDING",(0,0),(-1,-1), 6),
        ("VALIGN",(0,0),(-1,-1),"TOP"),
    ]))
    story.append(t_inst)
    story.append(Spacer(1, 5*mm))

    # ── Resultado geral (sem ID) ────────────────────────────────────────
    story.append(Paragraph("Resultado geral", st_secao))
    score_raw = float(registro.get("score_geral", 0) or 0)
    nivel_txt = str(registro.get("nivel_maturidade",""))

    t_res = Table([
        [kpi_cell("Score geral", f"{score_raw:.2f} / 3,00"),
         kpi_cell("Nível de maturidade", nivel_txt)],
    ], colWidths=[half, half])
    t_res.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1), cinza_claro),
        ("BOX",(0,0),(-1,-1), 0.5, cinza_borda),
        ("INNERGRID",(0,0),(-1,-1), 0.5, cinza_borda),
        ("LINEBEFORE",(0,0),(0,-1), 3, amarelo),
        ("LINEBEFORE",(1,0),(1,-1), 3, amarelo),
        ("TOPPADDING",(0,0),(-1,-1), 6),
        ("BOTTOMPADDING",(0,0),(-1,-1), 6),
        ("LEFTPADDING",(0,0),(-1,-1), 8),
        ("RIGHTPADDING",(0,0),(-1,-1), 6),
        ("VALIGN",(0,0),(-1,-1),"TOP"),
    ]))
    story.append(t_res)
    story.append(Spacer(1, 5*mm))

    # ── Visual executivo — barra de maturidade + badges ─────────────────
    story.append(Paragraph("Visual executivo", st_secao))

    score_pct = max(0.0, min(score_raw / 3.0, 1.0))
    BAR_W = PAGE_W - 20*mm   # largura da barra dentro do card
    BAR_H = 8                 # altura em pts

    if score_raw < 1.0:   active = 0
    elif score_raw < 2.0: active = 1
    elif score_raw < 2.6: active = 2
    else:                  active = 3
    levels = ["Incipiente", "Em estruturação", "Parcialmente estruturado", "Bem estruturado"]

    # desenha barra usando Drawing
    bar_drawing = Drawing(BAR_W, BAR_H + 2)
    bar_drawing.add(Rect(0, 1, BAR_W, BAR_H,
                         fillColor=colors.HexColor("#f1f1f1"), strokeColor=None))
    bar_drawing.add(Rect(0, 1, BAR_W * score_pct, BAR_H,
                         fillColor=amarelo, strokeColor=None))

    badges = []
    for i, lbl in enumerate(levels):
        st_b = st_badge_on if i == active else st_badge_off
        badges.append(Paragraph(lbl, st_b))

    visual_content = [
        [Paragraph("<b>Indicador visual de maturidade</b>", st_normal)],
        [Paragraph(f"Score geral: <b>{score_raw:.2f}</b> / 3,0", st_normal)],
        [bar_drawing],
        [Paragraph("Escala de 0 a 3", st_muted)],
        [Table([badges], colWidths=[PAGE_W/4 - 6*mm]*4,
               style=TableStyle([("ALIGN",(0,0),(-1,-1),"CENTER"),
                                 ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
                                 ("LEFTPADDING",(0,0),(-1,-1),2),
                                 ("RIGHTPADDING",(0,0),(-1,-1),2)]))],
    ]
    t_visual = Table(visual_content, colWidths=[PAGE_W - 16*mm])
    t_visual.setStyle(TableStyle([
        ("BOX",(0,0),(-1,-1), 0.5, cinza_borda),
        ("BACKGROUND",(0,0),(-1,-1), cinza_claro),
        ("TOPPADDING",(0,0),(-1,-1), 5),
        ("BOTTOMPADDING",(0,0),(-1,-1), 4),
        ("LEFTPADDING",(0,0),(-1,-1), 8),
        ("RIGHTPADDING",(0,0),(-1,-1), 8),
    ]))
    story.append(t_visual)
    story.append(Spacer(1, 5*mm))

    # ── Análise por dimensão ────────────────────────────────────────────
    if medias_dim:
        story.append(Paragraph("Análise por dimensão", st_secao))
        for dim, media in medias_dim.items():
            base = 1.92
            diff = round(media - base, 2)
            sinal = "+" if diff >= 0 else ""

            org_pct  = max(0.0, min(media / 3.0, 1.0))
            base_pct = max(0.0, min(base  / 3.0, 1.0))

            if media < 1.5:
                prioridade  = "Prioridade alta"
                recomendacao = "Estruturar fundamentos da agenda estratégica (cenários, objetivos, metas e planos de ação)."
            elif media < 2.0:
                prioridade  = "Prioridade média"
                recomendacao = "Fortalecer consistência e institucionalização das práticas estratégicas."
            else:
                prioridade  = "Prioridade de consolidação"
                recomendacao = "Padronizar e ampliar a disseminação interna das práticas já existentes."

            DIM_W = PAGE_W - 20*mm

            org_bar = Drawing(DIM_W, BAR_H + 2)
            org_bar.add(Rect(0,1, DIM_W, BAR_H, fillColor=colors.HexColor("#f1f1f1"), strokeColor=None))
            org_bar.add(Rect(0,1, DIM_W*org_pct, BAR_H, fillColor=amarelo, strokeColor=None))

            base_bar = Drawing(DIM_W, BAR_H + 2)
            base_bar.add(Rect(0,1, DIM_W, BAR_H, fillColor=colors.HexColor("#f1f1f1"), strokeColor=None))
            base_bar.add(Rect(0,1, DIM_W*base_pct, BAR_H, fillColor=colors.HexColor("#cfcfcf"), strokeColor=None))

            dim_rows = [
                [Paragraph(f"<b>{dim}</b>", st_normal)],
                [Paragraph(
                    f"Média da organização: <b>{media:.2f}</b> &nbsp;|&nbsp; "
                    f"Base: <b>{base:.2f}</b> &nbsp;|&nbsp; "
                    f"Diferença: <b>{sinal}{diff:.2f}</b>",
                    st_normal)],
                [Paragraph("<b>Organização</b>", st_muted)],
                [org_bar],
                [Paragraph("<b>Base nacional</b>", st_muted)],
                [base_bar],
                [Paragraph(f"<b>{prioridade}:</b> {recomendacao}", st_muted)],
            ]
            t_dim = Table(dim_rows, colWidths=[DIM_W])
            t_dim.setStyle(TableStyle([
                ("BOX",(0,0),(-1,-1), 0.5, cinza_borda),
                ("BACKGROUND",(0,0),(-1,-1), cinza_claro),
                ("LINEBEFORE",(0,0),(0,-1), 3, amarelo),
                ("TOPPADDING",(0,0),(-1,-1), 5),
                ("BOTTOMPADDING",(0,0),(-1,-1), 4),
                ("LEFTPADDING",(0,0),(-1,-1), 8),
                ("RIGHTPADDING",(0,0),(-1,-1), 8),
            ]))
            story.append(t_dim)
            story.append(Spacer(1, 4*mm))

    # ── Rodapé ──────────────────────────────────────────────────────────
    story.append(Spacer(1, 6*mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=cinza_borda, spaceAfter=3))
    story.append(Paragraph("Desenvolvido pelo Instituto Publix — institutopublix.com.br", st_rodape))

    doc.build(story)
    return buffer.getvalue()

def enviar_resumo_por_email(destinatario: str, registro: dict, medias_dim: dict):
    smtp_host = get_config_value("SMTP_HOST")
    smtp_port = get_config_value("SMTP_PORT")
    smtp_user = get_config_value("SMTP_USER")
    smtp_password = get_config_value("SMTP_PASSWORD")
    smtp_from_email = get_config_value("SMTP_FROM_EMAIL") or smtp_user
    smtp_from_name = get_config_value("SMTP_FROM_NAME") or "Instituto Publix"

    faltando = []
    if not smtp_host: faltando.append("SMTP_HOST")
    if not smtp_port: faltando.append("SMTP_PORT")
    if not smtp_user: faltando.append("SMTP_USER")
    if not smtp_password: faltando.append("SMTP_PASSWORD")
    if not smtp_from_email: faltando.append("SMTP_FROM_EMAIL")
    if faltando:
        raise Exception(f"Configuração de e-mail incompleta. Faltam: {', '.join(faltando)}.")

    nome = registro.get("nome_respondente", "")

    # Corpo institucional do e-mail
    corpo_html = f"""
<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; color: #333;">
  <div style="background: linear-gradient(90deg, #FFC728, #FFB300); height: 6px; border-radius: 3px;"></div>
  <div style="padding: 28px 32px;">
    <p style="font-size: 15px; font-weight: bold; margin-bottom: 12px;">Olá, {nome}!</p>
    <p style="font-size: 14px; line-height: 1.7; margin: 0 0 12px 0;">
      Agradecemos o seu interesse em participar do <strong>Observatório da Maturidade em Governança
      para Resultados</strong> do Instituto Publix.
    </p>
    <p style="font-size: 14px; line-height: 1.7; margin: 0 0 12px 0;">
      Em anexo, você encontrará o relatório inicial referente ao diagnóstico realizado.
    </p>
    <p style="font-size: 14px; line-height: 1.7; margin: 0 0 12px 0;">
      Para a realização do diagnóstico completo e aprofundado, nossa equipe entrará em contato
      em breve para apresentar as possibilidades e os próximos passos.
    </p>
    <p style="font-size: 14px; line-height: 1.7; margin: 0 0 24px 0;">
      Em caso de dúvidas, permanecemos à disposição pelo e-mail
      <a href="mailto:contato@institutopublix.com.br" style="color: #FFC728; text-decoration: none;">
        contato@institutopublix.com.br
      </a>.
    </p>
    <p style="font-size: 14px; line-height: 1.7; margin: 0;">
      Atenciosamente,<br>
      <strong>Instituto Publix</strong>
    </p>
  </div>
  <div style="background: #f8f8f8; padding: 12px 32px; font-size: 11px; color: #999; text-align: right; border-top: 1px solid #eee;">
    Instituto Publix — institutopublix.com.br
  </div>
</div>
"""

    corpo_texto = f"""Olá, {nome}!

Agradecemos o seu interesse em participar do Observatório da Maturidade em Governança para Resultados do Instituto Publix.

Em anexo, você encontrará o relatório inicial referente ao diagnóstico realizado.

Para a realização do diagnóstico completo e aprofundado, nossa equipe entrará em contato em breve para apresentar as possibilidades e os próximos passos.

Em caso de dúvidas, permanecemos à disposição pelo e-mail contato@institutopublix.com.br.

Atenciosamente,
Instituto Publix
"""

    # Gera PDF
    pdf_bytes = gerar_pdf_relatorio(registro, medias_dim)

    # Monta e-mail com anexo
    msg = MIMEMultipart("mixed")
    msg["Subject"] = "Seu relatório de diagnóstico — Observatório de Governança para Resultados"
    msg["From"] = f"{smtp_from_name} <{smtp_from_email}>"
    msg["To"] = destinatario

    alternativa = MIMEMultipart("alternative")
    alternativa.attach(MIMEText(corpo_texto, "plain", "utf-8"))
    alternativa.attach(MIMEText(corpo_html, "html", "utf-8"))
    msg.attach(alternativa)

    # Anexa PDF
    part_pdf = MIMEBase("application", "pdf")
    part_pdf.set_payload(pdf_bytes)
    encoders.encode_base64(part_pdf)
    part_pdf.add_header("Content-Disposition", "attachment",
                        filename="Relatorio_Diagnostico_Publix.pdf")
    msg.attach(part_pdf)

    port = int(str(smtp_port).strip())
    context = ssl.create_default_context()

    if port == 465:
        with smtplib.SMTP_SSL(smtp_host, port, context=context, timeout=30) as server:
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
    else:
        with smtplib.SMTP(smtp_host, port, timeout=30) as server:
            server.ehlo()
            server.starttls(context=context)
            server.ehlo()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)


def file_to_base64(path: Path):
    if not path.exists():
        return None
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except Exception:
        return None


# -------------------
# GOOGLE SHEETS
# -------------------
@st.cache_resource
def conectar_google_sheets():
    try:
        required_keys = [
            "GCP_TYPE", "GCP_PROJECT_ID", "GCP_PRIVATE_KEY_ID", "GCP_PRIVATE_KEY",
            "GCP_CLIENT_EMAIL", "GCP_CLIENT_ID", "GCP_AUTH_URI", "GCP_TOKEN_URI",
            "GCP_AUTH_PROVIDER_X509_CERT_URL", "GCP_CLIENT_X509_CERT_URL", "GCP_UNIVERSE_DOMAIN",
        ]
        faltando = [k for k in required_keys if not get_config_value(k)]
        if faltando:
            raise Exception(f"Secrets inválidos: faltam as chaves {', '.join(faltando)}.")

        service_account_info = {
            "type": get_config_value("GCP_TYPE"),
            "project_id": get_config_value("GCP_PROJECT_ID"),
            "private_key_id": get_config_value("GCP_PRIVATE_KEY_ID"),
            "private_key": get_config_value("GCP_PRIVATE_KEY"),
            "client_email": get_config_value("GCP_CLIENT_EMAIL"),
            "client_id": get_config_value("GCP_CLIENT_ID"),
            "auth_uri": get_config_value("GCP_AUTH_URI"),
            "token_uri": get_config_value("GCP_TOKEN_URI"),
            "auth_provider_x509_cert_url": get_config_value("GCP_AUTH_PROVIDER_X509_CERT_URL"),
            "client_x509_cert_url": get_config_value("GCP_CLIENT_X509_CERT_URL"),
            "universe_domain": get_config_value("GCP_UNIVERSE_DOMAIN"),
        }

        # Corrige private key salva com \n literal
        if isinstance(service_account_info["private_key"], str):
            service_account_info["private_key"] = service_account_info["private_key"].replace("\\n", "\n")

        creds = Credentials.from_service_account_info(service_account_info, scopes=SCOPES)
        client = gspread.authorize(creds)

        try:
            planilha = client.open(SHEET_NAME)
        except SpreadsheetNotFound:
            raise Exception(
                f"Planilha não encontrada ou sem permissão: '{SHEET_NAME}'. "
                f"Compartilhe com: {service_account_info['client_email']}"
            )

        try:
            aba = planilha.worksheet(WORKSHEET_NAME)
        except WorksheetNotFound:
            raise Exception(f"A aba '{WORKSHEET_NAME}' não existe dentro da planilha '{SHEET_NAME}'.")

        return aba
    except Exception as e:
        raise Exception(f"Erro na conexão com Google Sheets: {e}")


def garantir_cabecalho(aba, registro: dict):
    try:
        primeira_linha = aba.row_values(1)
        cabecalho_esperado = list(registro.keys())
        if not primeira_linha:
            aba.insert_row(cabecalho_esperado, 1, value_input_option="USER_ENTERED")
            return
        if primeira_linha != cabecalho_esperado:
            aba.insert_row(cabecalho_esperado, 1, value_input_option="USER_ENTERED")
    except Exception as e:
        raise Exception(f"Erro ao garantir cabeçalho da planilha: {e}")


def salvar_registro_google_sheets(registro: dict):
    try:
        aba = conectar_google_sheets()
        garantir_cabecalho(aba, registro)
        aba.append_row(list(registro.values()), value_input_option="USER_ENTERED")
    except Exception as e:
        raise Exception(f"Erro ao salvar registro no Google Sheets: {e}")


# -------------------
# CSS
# -------------------
st.markdown(
    """
<style>
[data-testid="stSidebar"] { display: none !important; }
.block-container { padding-top: 1.2rem !important; max-width: 1200px !important; }
#MainMenu {visibility: hidden;}
header {visibility: hidden;}
footer {visibility: hidden;}
.stAppDeployButton {display: none !important;}
button[title="Manage app"] {display: none !important;}
[data-testid="stStatusWidget"] {display: none !important;}
button[aria-label="Manage app"],
div[data-testid="manage-app-button"],
div[data-testid="ManageAppButton"] { display: none !important; }
div[data-testid="stSlider"] { margin-bottom: 0.7rem !important; }
h1, h2, h3 { color: #111; }
div[data-testid="stAlert"] {
    background-color: #FFF3C4 !important;
    border-left: 6px solid #FFC728 !important;
    border-radius: 8px !important;
}
div[data-testid="stAlert"] * { color: #000 !important; }

/* ---- preview de score (antes do e-mail) ---- */
.preview-banner {
    background: linear-gradient(135deg, #fffbea 0%, #fff8d6 100%);
    border: 2px solid #FFC728;
    border-radius: 14px;
    padding: 20px 24px;
    margin: 16px 0;
    text-align: center;
}
.preview-score {
    font-size: 2.8rem;
    font-weight: 900;
    color: #111;
    line-height: 1.1;
}
.preview-nivel {
    font-size: 1.1rem;
    color: #555;
    margin-top: 4px;
    margin-bottom: 12px;
}
.preview-dim-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 7px 0;
    border-bottom: 1px solid #f0e8c8;
}
.preview-dim-row:last-child { border-bottom: none; }
.preview-dim-name { font-weight: 600; font-size: 0.97rem; }
.preview-dim-value { font-size: 0.97rem; color: #444; }

/* ---- blur / lock overlay ---- */
.locked-section {
    filter: blur(4px);
    pointer-events: none;
    user-select: none;
    opacity: 0.55;
}
.unlock-cta {
    background: #fff;
    border: 2px solid #FFC728;
    border-radius: 14px;
    padding: 20px 24px;
    margin: 20px 0;
    text-align: center;
    box-shadow: 0 4px 18px rgba(255,199,40,0.15);
}
.unlock-cta-title {
    font-size: 1.18rem;
    font-weight: 800;
    margin-bottom: 6px;
}
.unlock-cta-sub {
    color: #555;
    font-size: 0.97rem;
    margin-bottom: 0;
}

/* ---- email match indicator ---- */
.email-match-ok {
    color: #1a7a3c;
    font-weight: 700;
    font-size: 0.92rem;
    margin-top: -8px;
    margin-bottom: 8px;
}
.email-match-err {
    color: #c0392b;
    font-weight: 700;
    font-size: 0.92rem;
    margin-top: -8px;
    margin-bottom: 8px;
}

.form-card {
    border: 1px solid #dddddd;
    border-radius: 10px;
    padding: 14px;
    background: #f8f8f8;
    margin-bottom: 14px;
}
.action-box {
    background: #fff8e1;
    border: 1px solid #f3d36c;
    border-radius: 10px;
    padding: 10px 12px;
    margin: 8px 0 12px 0;
}
.result-card {
    background: #fff;
    border: 1px solid #e6e6e6;
    border-left: 5px solid #FFC728;
    border-radius: 10px;
    padding: 10px 12px;
    margin-bottom: 8px;
}
.result-card-title { font-weight: 700; margin-bottom: 3px; }
.result-card-sub { color: #444; font-size: 0.94rem; }
.report-wrap {
    background: #ffffff;
    border: 1px solid #e8e8e8;
    border-radius: 14px;
    padding: 18px;
    margin: 12px 0 16px 0;
}
.report-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 16px;
    margin-bottom: 10px;
}
.report-header-left { flex: 1; min-width: 0; }
.report-logo { flex: 0 0 auto; display: flex; align-items: center; justify-content: flex-end; }
.report-logo img { max-height: 42px; width: auto; object-fit: contain; }
.report-title { font-size: 1.25rem; font-weight: 800; margin-bottom: 2px; }
.report-subtitle { color: #555; font-size: 0.92rem; margin-bottom: 10px; }
.publix-band {
    height: 8px;
    background: linear-gradient(90deg, #FFC728 0%, #FFB300 100%);
    border-radius: 999px;
    margin-bottom: 12px;
}
.kpi-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin: 10px 0 14px 0; }
.kpi-card {
    background: #fff;
    border: 1px solid #e8e8e8;
    border-left: 5px solid #FFC728;
    border-radius: 10px;
    padding: 10px 12px;
}
.kpi-card .label { font-size: 0.82rem; color: #666; margin-bottom: 2px; }
.kpi-card .value { font-weight: 800; font-size: 1.02rem; color: #111; word-break: break-word; }
.section-print-title {
    font-weight: 800;
    font-size: 1rem;
    margin: 12px 0 8px 0;
    padding-bottom: 4px;
    border-bottom: 1px solid #ececec;
}
.dim-card {
    border: 1px solid #e9e9e9;
    border-radius: 10px;
    padding: 10px 12px;
    margin-bottom: 8px;
    background: #fff;
    break-inside: avoid;
    page-break-inside: avoid;
}
.dim-card strong { display: block; margin-bottom: 4px; }
.muted { color: #666; font-size: 0.9rem; }
.visual-block {
    border: 1px solid #e9e9e9;
    border-radius: 10px;
    padding: 12px;
    margin-bottom: 10px;
    background: #fff;
    break-inside: avoid;
    page-break-inside: avoid;
}
.visual-title { font-weight: 800; margin-bottom: 8px; }
.bar-track {
    width: 100%;
    height: 12px;
    background: #f1f1f1;
    border-radius: 999px;
    overflow: hidden;
    margin: 6px 0 4px 0;
}
.bar-fill {
    height: 100%;
    background: linear-gradient(90deg, #FFC728 0%, #FFB300 100%);
    border-radius: 999px;
}
.bar-legend { font-size: 0.84rem; color: #666; }
.compare-row { margin-top: 8px; }
.compare-label { font-size: 0.84rem; font-weight: 700; margin-bottom: 2px; }
.compare-track { width: 100%; height: 10px; background: #f1f1f1; border-radius: 999px; overflow: hidden; }
.compare-fill-org { height: 100%; background: #FFC728; border-radius: 999px; }
.compare-fill-base { height: 100%; background: #cfcfcf; border-radius: 999px; }
.level-badges { display: flex; gap: 6px; flex-wrap: wrap; margin-top: 8px; }
.level-badge {
    font-size: 0.78rem;
    padding: 4px 8px;
    border-radius: 999px;
    border: 1px solid #ddd;
    background: #fafafa;
    color: #555;
}
.level-badge.active { background: #fff3c4; border-color: #FFC728; color: #111; font-weight: 700; }
.no-print { display: block; }
.print-only { display: none; }

@media print {
    @page { size: A4; margin: 12mm; }
    html, body { background: #fff !important; }
    body { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }
    .print-only { display: block !important; }
    .block-container { max-width: 100% !important; padding: 0 !important; }
    h1 { font-size: 18pt !important; margin-bottom: 6px !important; }
    h2 { font-size: 14pt !important; margin: 10px 0 6px 0 !important; }
    h3 { font-size: 12pt !important; margin: 8px 0 4px 0 !important; }
    p, li, div, span { font-size: 10.5pt !important; line-height: 1.35 !important; }
    .report-wrap, .result-card, .kpi-card, .dim-card, .visual-block {
        break-inside: avoid !important;
        page-break-inside: avoid !important;
    }
    hr { border: none !important; border-top: 1px solid #dcdcdc !important; margin: 8px 0 !important; }
}
</style>
""",
    unsafe_allow_html=True,
)

# -------------------
# CABEÇALHO
# -------------------
st.markdown('<div class="no-print">', unsafe_allow_html=True)
st.markdown(
    """
<h1 style='margin-bottom: 4px;'>Observatório da maturidade em governança para resultados</h1>
<p style='font-size: 1.08rem; line-height: 1.4; margin-top: 0; margin-bottom: 16px; color: #444; font-weight: 600;'>
Faça seu diagnóstico inicial, com suporte de um copiloto de IA
</p>
<p style='font-size: 1.03rem; line-height: 1.52;'>
A <strong>Inteligência Artificial do Observatório da Governança para Resultados</strong> é uma camada criada para transformar dados em uma perspectiva de fortalecimento das instituições.
Ela interpreta suas respostas, compara com a base nacional do Observatório e identifica padrões, fragilidades e oportunidades de evolução, de maneira objetiva, estratégica e personalizada para o seu órgão.
</p>
<p style='font-size: 1.03rem; line-height: 1.52;'>
Combinando análise de dados, linguagem natural e a experiência do Instituto Publix em gestão para resultados, a IA oferece uma visão integrada e acionável sobre a maturidade institucional.
É um instrumento de navegação: aponta onde você está, ilumina caminhos possíveis e orienta decisões que fortalecem capacidades.
</p>
<p style='font-size: 1.03rem; line-height: 1.52; font-weight: 600;'>
Apresentamos abaixo um diagnóstico preliminar para experimentação da Plataforma.
O instrumento tem como finalidade proporcionar uma avaliação inicial. Caso haja interesse em realizar o diagnóstico completo, solicitamos o preenchimento das informações complementares ao final do formulário, com a devida indicação de interesse para contato.
</p>
<p style='font-size: 1.03rem; line-height: 1.52; font-weight: 600;'>
Observatório de Governança para Resultados: inteligência para evoluir capacidades na geração de resultados sustentáveis.
</p>
""",
    unsafe_allow_html=True,
)
st.markdown('</div>', unsafe_allow_html=True)

# -------------------
# OPENAI
# -------------------
openai_api_key = get_config_value("OPENAI_API_KEY")
if not openai_api_key:
    st.error("OPENAI_API_KEY não encontrada. Configure em Secrets do Streamlit ou na variável de ambiente.")
    st.stop()

openai.api_key = openai_api_key

# -------------------
# QUESTÕES
# -------------------
QUESTOES = [
    {"id": "1.1.1", "texto": "Identificam-se as forças e fraquezas, assim como as oportunidades e ameaças da organização (análise SWOT) como forma de compreender os ambientes internos e externos da organização para formulação/revisão das estratégias.", "dimensao": "Agenda Estratégica"},
    {"id": "1.1.2", "texto": "Existe elaboração de cenários, ambientes futuros, dos quais situações hipotéticas podem emergir e implicar em redirecionamentos estratégicos.", "dimensao": "Agenda Estratégica"},
    {"id": "1.1.3", "texto": "Realiza-se a gestão de stakeholders (partes interessadas), que compreende um conjunto de atividades que busca identificar, qualificar, avaliar e melhorar o relacionamento com as diversas partes interessadas, inclusive informações periódicas sobre a opinião e satisfação dos usuários referentes aos serviços oferecidos pela organização.", "dimensao": "Agenda Estratégica"},
    {"id": "1.1.4", "texto": "Existem analises que buscam compreender o universo de política pública na qual a organização opera, seus princípios, diretrizes, orientações, resultados e disposições programáticas (em planos setoriais, governamentais, plurianuais etc.).", "dimensao": "Agenda Estratégica"},
    {"id": "1.2.1", "texto": "A organização possui uma definição clara do seu propósito, informando sua razão de ser, seus produtos e os impactos visados aos seus beneficiários.", "dimensao": "Agenda Estratégica"},
    {"id": "1.2.2", "texto": "A agenda estratégica estabelece uma visão de longo prazo a partir da construção de um ideal transformador do contexto no qual está inserida.", "dimensao": "Agenda Estratégica"},
    {"id": "1.2.3", "texto": "Existe uma declaração de valores que serve de referência para a retórica (discursos, apresentações etc.) e as práticas organizacionais.", "dimensao": "Agenda Estratégica"},
    {"id": "1.2.4", "texto": "O propósito da organização é amplamente difundido internamente. Realizam-se campanhas de sensibilização (palestras, workshops etc.) para orientar e motivar os servidores quanto aos propósitos da organização.", "dimensao": "Agenda Estratégica"},
    {"id": "1.2.5", "texto": "O propósito da organização é sistematicamente divulgado à sociedade. A organização executa estratégias de comunicação às demais partes interessadas (cidadãos, governo, organizações parceiras etc.).", "dimensao": "Agenda Estratégica"},
    {"id": "1.3.1", "texto": "A programação estratégica (o conjunto de objetivos ou projetos, programas etc.) está alinhada com a visão, representando seu desdobramento.", "dimensao": "Agenda Estratégica"},
    {"id": "1.3.2", "texto": "A estratégia da organização está explicitada (preferencialmente por meio de um mapa estratégico, roadmap ou outra forma gráfica), expondo as relações de causa e efeito entre seus elementos.", "dimensao": "Agenda Estratégica"},
    {"id": "1.3.3", "texto": "Há um conjunto minimamente significativo de indicadores e metas de eficiência (relação entre os produtos/serviços gerados com os insumos empregados), eficácia (quantidade e qualidade de produtos/serviços entregues ao usuário) e efetividade (impactos gerados pelos produtos/serviços, processos ou projetos) que buscam mensurar os elementos programáticos da estratégia (objetivos, projetos etc.).", "dimensao": "Agenda Estratégica"},
    {"id": "1.3.4", "texto": "Há um razoável grau de realismo e desafio das metas, tendo em conta a escala dos problemas e demandas das partes interessadas e a disponibilidade de recursos (materiais, humanos, financeiros etc.)", "dimensao": "Agenda Estratégica"},
    {"id": "1.4.1", "texto": "Há um conjunto minimamente significativo de iniciativas estratégicas definidas para proporcionar o alcance das metas fixadas.", "dimensao": "Agenda Estratégica"},
    {"id": "1.4.2", "texto": "As iniciativas estratégicas são detalhadas em ações com prazos, responsáveis e marcos críticos.", "dimensao": "Agenda Estratégica"},
    {"id": "1.4.3", "texto": "Há um razoável equilíbrio nos níveis de detalhamento das iniciativas em termos de abrangência (cobrindo todas as metas). ", "dimensao": "Agenda Estratégica"},
    {"id": "1.4.4", "texto": "Há um razoável equilíbrio nos níveis de detalhamento das iniciativas em termos de profundidade (sem sub ou super-especificação).", "dimensao": "Agenda Estratégica"},
]

observatorio_means = {"Agenda Estratégica": 1.92}

BASE_SINTETICA = """
Base nacional do Observatório de Maturidade – resumo sintético

1. Perfil da base
- 259 respondentes, provenientes de 153 organizações.
- Esferas: 54,8% Federal; 31,6% Estadual; 8,1% Municipal; restante entre privado, 3º setor e organismos internacionais.
- Poderes: Executivo (144), Legislativo (36), Judiciário (29), Empresas Públicas (24), Privado (11).

2. Maturidade geral
- Média nacional de maturidade: 1,64 (escala 0 a 3).

3. Médias por dimensão
- Agenda Estratégica: 1,92
"""

BASE_MEDIA_POR_PODER = {
    "organismo internacional": 1.93,
    "empresa pública": 1.87,
    "privado": 1.82,
    "legislativo": 1.73,
    "executivo": 1.57,
    "judiciário": 1.57,
    "ministerio público": 1.57,
    "ministério público": 1.57,
}

BASE_MEDIA_POR_ESFERA = {
    "federal": 1.76,
    "estadual": 1.41,
    "municipal": 1.35,
    "privado": 1.81,
    "organismo internacional": 1.93,
}

PART_TITLES = {"1": "Agenda Estratégica"}
SECTION_TITLES = {
    "1.1": "Compreensão do Ambiente Institucional",
    "1.2": "Estabelecimento do Propósito",
    "1.3": "Definição de Resultados",
    "1.4": "Definição de Objetivos Estratégicos",
    "1.5": "Definição de Metas",
    "1.6": "Estratégias e Planos de Ação",
    "1.7": "Alinhamento com Agenda de Desenvolvimento",
}


# -------------------
# FUNÇÕES AUXILIARES
# -------------------
def extrair_partes(qid: str):
    partes = str(qid).split(".")
    part = partes[0] if len(partes) >= 1 else None
    sec = ".".join(partes[:2]) if len(partes) >= 2 else None
    return part, sec


def _normalizar_label(texto: str):
    if not texto:
        return None
    t = texto.strip().lower()
    substituicoes = {
        "poder executivo": "executivo",
        "poder legislativo": "legislativo",
        "poder judiciário": "judiciário",
        "judiciario": "judiciário",
        "org. internacional": "organismo internacional",
        "organismo int.": "organismo internacional",
        "organismo internacional e terceiro setor": "organismo internacional",
        "terceiro setor": "privado",
    }
    return substituicoes.get(t, t)


def calcular_medias_por_dimensao(respostas_dict):
    df = pd.DataFrame(QUESTOES)
    df["dim_key"] = df["dimensao"].astype(str).str.strip().str.rstrip(",")
    df["nota"] = df["id"].map(respostas_dict)
    return df.groupby("dim_key")["nota"].mean().round(2).to_dict()


def classificar_nivel(media_geral: float):
    if media_geral < 1.0:
        return "Inexistente / muito incipiente"
    elif media_geral < 2.0:
        return "Em estruturação"
    elif media_geral < 2.6:
        return "Parcialmente estruturado"
    return "Bem estruturado"


def montar_perfil_texto(instituicao, poder, esfera, estado, respostas_dict, medias_dimensao):
    linhas = []
    linhas.append(f"Instituição avaliada: {instituicao or 'Não informada'}")
    linhas.append(f"Poder: {poder or 'Não informado'}")
    linhas.append(f"Esfera: {esfera or 'Não informada'}")
    linhas.append(f"Estado: {estado or 'Não informado'}")
    linhas.append("")

    poder_norm = _normalizar_label(poder)
    esfera_norm = _normalizar_label(esfera)

    media_poder_base = BASE_MEDIA_POR_PODER.get(poder_norm) if poder_norm else None
    media_esfera_base = BASE_MEDIA_POR_ESFERA.get(esfera_norm) if esfera_norm else None

    if media_poder_base is not None:
        linhas.append(f"No Observatório de Maturidade, a média geral de maturidade para o poder '{poder}' é {media_poder_base:.2f}.")
    if media_esfera_base is not None:
        linhas.append(f"Na esfera '{esfera}', a média geral de maturidade observada na base é {media_esfera_base:.2f}.")
    if media_poder_base is not None or media_esfera_base is not None:
        linhas.append("")

    linhas.append("Resumo das notas por dimensão (escala 0 a 3):")
    for dim, media_orgao in medias_dimensao.items():
        media_base = observatorio_means.get(dim)
        if media_base is not None and not pd.isna(media_base):
            diff = round(media_orgao - media_base, 2)
            if diff > 0.1:
                situacao = "acima da média da base"
            elif diff < -0.1:
                situacao = "abaixo da média da base"
            else:
                situacao = "próximo da média da base"
            linhas.append(f"- {dim}: {media_orgao:.2f} (média da base: {media_base:.2f}; situação: {situacao}, diferença: {diff:+.2f})")

    linhas.append("")
    linhas.append("Notas detalhadas por questão:")
    for q in QUESTOES:
        nota = respostas_dict.get(q["id"])
        linhas.append(f"- {q['id']} | {q['texto']} -> nota {nota}")

    return "\n".join(linhas)


def chamar_ia(perfil_texto, chat_history):
    system_prompt = """
Você é o Radar Publix, assistente de IA especializado em gestão pública e maturidade institucional.
Sua função é analisar o diagnóstico de um órgão e compará-lo com a base nacional do Observatório,
indicando pontos fortes, fragilidades e caminhos práticos de evolução.

Regras:
- Seja objetivo e útil.
- Traga recomendações práticas.
- Use linguagem clara e profissional.
- Quando possível, organize em tópicos curtos.
"""
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "system", "content": "Principais achados da base nacional do Observatório de Maturidade:"},
        {"role": "system", "content": BASE_SINTETICA},
        {"role": "system", "content": "Diagnóstico estruturado da organização do usuário:"},
        {"role": "system", "content": perfil_texto},
    ]
    messages.extend(chat_history)

    try:
        client_oai = openai.OpenAI(api_key=openai_api_key)
        response = client_oai.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.3,
        )
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"Erro ao chamar a API de IA: {e}")
        return "Tive um problema técnico para gerar a resposta agora. Tente novamente em instantes."


def montar_registro_para_salvar(dados_institucionais: dict, dados_pessoais: dict, respostas: dict, medias_dim: dict):
    media_geral = round(sum(respostas.values()) / len(respostas), 2) if respostas else None
    nivel = classificar_nivel(media_geral) if media_geral is not None else None

    registro = {
        "id_resposta": str(uuid.uuid4()),
        "data_hora": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "versao_instrumento": "agenda_estrategica_v1",
        "modulo": "Agenda Estratégica",
        "instituicao": dados_institucionais.get("instituicao", ""),
        "poder": dados_institucionais.get("poder", ""),
        "esfera": dados_institucionais.get("esfera", ""),
        "estado_uf": dados_institucionais.get("estado_uf", ""),
        "consentimento_uso_informacoes": dados_institucionais.get("consentimento_uso_informacoes", False),
        "nome_respondente": dados_pessoais.get("nome_respondente", ""),
        "email_respondente": dados_pessoais.get("email_respondente", ""),
        "area_unidade": dados_pessoais.get("area_unidade", ""),
        "cargo_funcao": dados_pessoais.get("cargo_funcao", ""),
        "deseja_contato_diagnostico_completo": dados_pessoais.get("deseja_contato_diagnostico_completo", False),
        "score_geral": media_geral,
        "nivel_maturidade": nivel,
    }

    for dim, valor in medias_dim.items():
        col = (
            "score_dim_"
            + dim.lower()
            .replace(" ", "_")
            .replace("ã", "a")
            .replace("á", "a")
            .replace("é", "e")
            .replace("í", "i")
            .replace("ó", "o")
            .replace("ú", "u")
            .replace("ç", "c")
        )
        registro[col] = round(float(valor), 2)

    for qid, nota in respostas.items():
        registro[f"q_{qid.replace('.', '_')}"] = nota

    return registro


# -------------------
# SESSION STATE
# -------------------
defaults = {
    "diagnostico_respostas": None,
    "diagnostico_perfil_texto": None,
    "chat_history": [],
    "respostas_dict": {q["id"]: 1 for q in QUESTOES},
    "pagina_quest": 1,
    "medias_dimensao": None,
    "diagnostico_gerado": False,
    "respondente_salvo": False,
    "registro_salvo": None,
    "dados_institucionais": None,
    "etapa1_ok": False,
    "dados_pessoais": None,
    # --- novos estados para verificação de e-mail ---
    "email_verificado": False,
    "email_confirmacao_erro": False,
    "email_erro_msg": None,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# =========================================================
# ETAPA 1 — Dados institucionais
# =========================================================
st.markdown('<div class="no-print">', unsafe_allow_html=True)
st.subheader("Dados institucionais e autorização")

with st.form("form_dados_institucionais", clear_on_submit=False):
    l1, l2 = st.columns(2)
    with l1:
        instituicao = st.text_input("1.1 Instituição", max_chars=120)
    with l2:
        poder = st.selectbox(
            "1.2 A qual poder sua instituição pertence?",
            ["", "Executivo", "Legislativo", "Judiciário", "Ministério Público",
             "Organismo internacional e terceiro setor", "Outro"],
        )

    l3, l4 = st.columns(2)
    with l3:
        esfera = st.selectbox("1.3 Esfera", ["", "Federal", "Estadual", "Municipal", "Terceiro setor"])
    with l4:
        estado_uf = st.selectbox(
            "1.4 Estado (UF)",
            ["", "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA",
             "MG", "MS", "MT", "PA", "PB", "PE", "PI", "PR", "RJ", "RN",
             "RO", "RR", "RS", "SC", "SE", "SP", "TO"],
        )

    st.markdown("### Autorização de uso das informações")
    autorizacao_uso = st.checkbox(
        "Autorizo o uso das informações inseridas neste diagnóstico para fins de análise, consolidação estatística e aperfeiçoamento do Observatório de Governança para Resultados.",
        value=False,
    )
    st.markdown(
        "<small><em>O sigilo das informações individuais institucionais será preservado, e quaisquer divulgações ocorrerão apenas de forma consolidada e anonimizada.</em></small>",
        unsafe_allow_html=True,
    )

    confirmar_etapa1 = st.form_submit_button("Continuar para o diagnóstico", use_container_width=True)

    if confirmar_etapa1:
        if not instituicao.strip():
            st.error("Preencha a instituição.")
        elif not poder.strip():
            st.error("Selecione o poder.")
        elif not esfera.strip():
            st.error("Selecione a esfera.")
        elif not estado_uf.strip():
            st.error("Selecione o Estado (UF).")
        elif not autorizacao_uso:
            st.error("É necessário autorizar o uso das informações para continuar.")
        else:
            st.session_state.dados_institucionais = {
                "instituicao": instituicao.strip(),
                "poder": poder,
                "esfera": esfera,
                "estado_uf": estado_uf,
                "consentimento_uso_informacoes": autorizacao_uso,
            }
            st.session_state.etapa1_ok = True
            st.success("Dados institucionais salvos. Agora preencha a Agenda Estratégica.")
st.markdown('</div>', unsafe_allow_html=True)


# =========================================================
# ETAPA 2 — Questionário
# =========================================================
st.markdown('<div class="no-print">', unsafe_allow_html=True)
st.markdown("---")
st.subheader("Agenda Estratégica")

if not st.session_state.etapa1_ok:
    st.info("Preencha os dados institucionais e a autorização acima para liberar o diagnóstico.")
else:
    st.caption("Responda cada afirmação em uma escala de 0 a 3.")

    QUESTOES_POR_PAG = 10
    total_paginas = math.ceil(len(QUESTOES) / QUESTOES_POR_PAG)
    pagina = st.session_state.pagina_quest
    inicio = (pagina - 1) * QUESTOES_POR_PAG
    fim = min(inicio + QUESTOES_POR_PAG, len(QUESTOES))

    st.write(f"Bloco {pagina} de {total_paginas}")

    part_atual = None
    sec_atual = None

    for q in QUESTOES[inicio:fim]:
        qid = q["id"]
        part, sec = extrair_partes(qid)

        if part != part_atual:
            titulo = PART_TITLES.get(part, "")
            st.markdown("---")
            st.markdown(f"## {part}. {titulo}" if titulo else f"## {part}")
            part_atual = part
            sec_atual = None

        if sec and sec != sec_atual:
            subtitulo = SECTION_TITLES.get(sec, "")
            st.markdown(f"### {sec}. {subtitulo}" if subtitulo else f"### {sec}")
            sec_atual = sec

        atual = st.session_state.respostas_dict.get(qid, 1)
        novo_valor = st.slider(
            label=f"{qid} — {q['texto']}",
            min_value=0,
            max_value=3,
            value=atual,
            step=1,
            help="0 = Inexistente | 1 = Muito incipiente | 2 = Parcialmente estruturado | 3 = Bem estruturado",
            key=f"slider_{qid}",
        )
        st.session_state.respostas_dict[qid] = novo_valor

    col1, col2, col3 = st.columns([1, 1, 2])

    def ir_anterior():
        if st.session_state.pagina_quest > 1:
            st.session_state.pagina_quest -= 1

    def ir_proximo():
        if st.session_state.pagina_quest < total_paginas:
            st.session_state.pagina_quest += 1

    with col1:
        st.button("Anterior", key="btn_anterior", disabled=(pagina == 1), on_click=ir_anterior)
    with col2:
        st.button("Próximo", key="btn_proximo", disabled=(pagina == total_paginas), on_click=ir_proximo)
    with col3:
        ultimo_bloco = (pagina == total_paginas)
        gerar = st.button(
            "Gerar diagnóstico",
            key="btn_gerar",
            use_container_width=True,
            disabled=not ultimo_bloco,
        )
        if not ultimo_bloco:
            st.caption("Finalize todos os blocos para habilitar o diagnóstico.")

    if gerar:
        respostas = st.session_state.respostas_dict.copy()
        st.session_state.diagnostico_respostas = respostas
        medias_dim = calcular_medias_por_dimensao(respostas)
        st.session_state.medias_dimensao = medias_dim
        st.session_state.diagnostico_gerado = True
        # Reseta estados de verificação ao regerar
        st.session_state.email_verificado = False
        st.session_state.respondente_salvo = False
        st.session_state.diagnostico_perfil_texto = None
        st.session_state.registro_salvo = None
        st.session_state.chat_history = []
        st.session_state.dados_pessoais = None

st.markdown('</div>', unsafe_allow_html=True)


# =========================================================
# ETAPA 3 — Preview do score (visível antes do e-mail)
# =========================================================
if st.session_state.diagnostico_gerado:
    respostas_preview = st.session_state.diagnostico_respostas or {}
    medias_preview = st.session_state.medias_dimensao or {}
    score_geral_preview = round(sum(respostas_preview.values()) / len(respostas_preview), 2) if respostas_preview else 0
    nivel_preview = classificar_nivel(score_geral_preview)

    st.markdown("---")
    st.markdown('<div class="no-print">', unsafe_allow_html=True)
    st.subheader("Resultado parcial do diagnóstico")

    # --- Banner com score e resumo por dimensão ---
    dims_html = ""
    for dim, media in medias_preview.items():
        base = observatorio_means.get(dim, None)
        diff_txt = ""
        if base is not None:
            diff = round(media - base, 2)
            sinal = "+" if diff >= 0 else ""
            diff_txt = f"&nbsp;&nbsp;<span style='color:#888;font-size:0.88rem;'>vs. base: {sinal}{diff:.2f}</span>"
        dims_html += f"""
        <div class="preview-dim-row">
            <span class="preview-dim-name">{html.escape(dim)}</span>
            <span class="preview-dim-value"><b>{media:.2f}</b> / 3,00{diff_txt}</span>
        </div>
        """

    st.markdown(
        f"""
        <div class="preview-banner">
            <div class="preview-score">{score_geral_preview:.2f} <span style="font-size:1.2rem;font-weight:400;color:#777;">/ 3,00</span></div>
            <div class="preview-nivel">Nível: <strong>{html.escape(nivel_preview)}</strong></div>
            {dims_html}
        </div>
        """,
        unsafe_allow_html=True,
    )

    # --- CTA para desbloquear IA e relatório completo ---
    if not st.session_state.email_verificado:
        st.markdown(
            """
            <div class="unlock-cta">
                <div class="unlock-cta-title">🔓 Quer o relatório completo e acesso à IA especialista?</div>
                <div class="unlock-cta-sub">Informe seus dados abaixo. O relatório detalhado será enviado para o seu e-mail — por isso pedimos confirmação do endereço.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown('</div>', unsafe_allow_html=True)


# =========================================================
# ETAPA 4 — Formulário de dados pessoais + verificação de e-mail
# =========================================================
st.markdown('<div class="no-print">', unsafe_allow_html=True)

if st.session_state.diagnostico_gerado and not st.session_state.email_verificado:
    st.subheader("Seus dados para receber o relatório")

    with st.form("form_dados_pessoais_pos_diag", clear_on_submit=False):
        c1, c2 = st.columns(2)
        with c1:
            nome_respondente = st.text_input("Nome *")
            email_respondente = st.text_input("E-mail *")
        with c2:
            area_unidade = st.text_input("Área / Unidade")
            cargo_funcao = st.selectbox(
                "Cargo / Função",
                [
                    "",
                    "Analista",
                    "Assessor",
                    "Assistente",
                    "Auditor",
                    "Chefe de Gabinete",
                    "Consultor",
                    "Coordenador",
                    "Diretor",
                    "Especialista",
                    "Gerente",
                    "Gestor",
                    "Ouvidor",
                    "Prefeito / Vice-Prefeito",
                    "Presidente / Vice-Presidente",
                    "Procurador",
                    "Secretário",
                    "Servidor Público",
                    "Subsecretário",
                    "Superintendente",
                    "Técnico",
                    "Vereador / Deputado",
                    "Outro",
                ],
            )

        # Campo de confirmação de e-mail
        email_confirmacao = st.text_input(
            "Confirme seu e-mail *",
            help="Digite o mesmo e-mail acima para confirmarmos o endereço.",
        )

        deseja_contato = st.checkbox(
            "Autorizo o compartilhamento do meu e-mail para receber comunicados, novidades e newsletter do Instituto Publix.",
            value=False,
        )

        salvar_dados_pessoais = st.form_submit_button(
            "Confirmar e-mail e acessar relatório completo + IA",
            use_container_width=True,
        )

        if salvar_dados_pessoais:
            erros = []
            if not nome_respondente.strip():
                erros.append("Preencha seu nome.")
            if not email_respondente.strip():
                erros.append("Preencha seu e-mail.")
            if not email_confirmacao.strip():
                erros.append("Confirme seu e-mail.")
            elif email_respondente.strip().lower() != email_confirmacao.strip().lower():
                erros.append("Os e-mails não coincidem. Verifique e tente novamente.")

            if erros:
                for erro in erros:
                    st.error(erro)
            else:
                # E-mails conferem — salva dados e prossegue
                st.session_state.dados_pessoais = {
                    "nome_respondente": nome_respondente.strip(),
                    "email_respondente": email_respondente.strip(),
                    "area_unidade": area_unidade.strip(),
                    "cargo_funcao": cargo_funcao.strip(),
                    "deseja_contato_diagnostico_completo": deseja_contato,
                }

                dados_inst = st.session_state.dados_institucionais or {}
                respostas = st.session_state.diagnostico_respostas or {}
                medias_dim = st.session_state.medias_dimensao or {}

                registro = montar_registro_para_salvar(
                    dados_institucionais=dados_inst,
                    dados_pessoais=st.session_state.dados_pessoais,
                    respostas=respostas,
                    medias_dim=medias_dim,
                )

                # Salva no Google Sheets
                try:
                    salvar_registro_google_sheets(registro)
                except Exception as e:
                    st.error(str(e))
                    st.info("O diagnóstico foi gerado, mas houve falha no salvamento. Verifique os Secrets, o nome da planilha/aba e a permissão da service account.")
                    st.stop()

                # Envia e-mail com resumo — falha não bloqueia o fluxo
                email_erro_msg = None
                try:
                    enviar_resumo_por_email(
                        destinatario=st.session_state.dados_pessoais["email_respondente"],
                        registro=registro,
                        medias_dim=medias_dim,
                    )
                except Exception as e:
                    email_erro_msg = str(e)

                # Monta perfil para IA
                perfil_txt = montar_perfil_texto(
                    dados_inst.get("instituicao"),
                    dados_inst.get("poder"),
                    dados_inst.get("esfera"),
                    dados_inst.get("estado_uf"),
                    respostas,
                    medias_dim,
                )

                st.session_state.diagnostico_perfil_texto = perfil_txt
                st.session_state.email_verificado = True
                st.session_state.respondente_salvo = True
                st.session_state.registro_salvo = registro
                st.session_state.email_erro_msg = email_erro_msg

                st.rerun()

st.markdown('</div>', unsafe_allow_html=True)


# =========================================================
# ETAPA 5 — Relatório completo (só após e-mail confirmado)
# =========================================================
if st.session_state.respondente_salvo and st.session_state.registro_salvo:
    # Mostra status do e-mail persistido antes do rerun
    if st.session_state.get("email_erro_msg"):
        st.warning(
            f"⚠️ Dados salvos, mas houve falha no envio do e-mail: {st.session_state.email_erro_msg}\n\n"
            "Você ainda pode acessar o relatório e a IA abaixo."
        )
    else:
        email_dest = st.session_state.registro_salvo.get("email_respondente", "")
        st.success(f"✅ Relatório enviado para **{email_dest}**. Verifique sua caixa de entrada!")

    r = st.session_state.registro_salvo
    medias_dim = st.session_state.medias_dimensao or {}

    score_geral_raw = float(r.get("score_geral", 0) or 0)
    score_geral = html.escape(str(r.get("score_geral", "")))
    nivel = html.escape(str(r.get("nivel_maturidade", "")))
    data_relatorio = html.escape(str(r.get("data_hora", "")))
    instituicao_txt = html.escape(str(r.get("instituicao", "")))
    poder_txt = html.escape(str(r.get("poder", "")))
    esfera_txt = html.escape(str(r.get("esfera", "")))
    uf_txt = html.escape(str(r.get("estado_uf", "")))
    respondente_txt = html.escape(str(r.get("nome_respondente", "")))
    cargo_txt = html.escape(str(r.get("cargo_funcao", "")))
    email_txt = html.escape(str(r.get("email_respondente", "")))
    diag_id_txt = html.escape(str(r.get("id_resposta", "")))

    score_pct = max(0, min((score_geral_raw / 3) * 100, 100))

    if score_geral_raw < 1.0:
        active_level = 1
    elif score_geral_raw < 2.0:
        active_level = 2
    elif score_geral_raw < 2.6:
        active_level = 3
    else:
        active_level = 4

    level_badges_html = (
        f'<div class="level-badges">'
        f'<div class="level-badge{" active" if active_level == 1 else ""}">Incipiente</div>'
        f'<div class="level-badge{" active" if active_level == 2 else ""}">Em estruturação</div>'
        f'<div class="level-badge{" active" if active_level == 3 else ""}">Parcialmente estruturado</div>'
        f'<div class="level-badge{" active" if active_level == 4 else ""}">Bem estruturado</div>'
        f'</div>'
    )

    cards_html_list = []
    for dim, media in medias_dim.items():
        base = observatorio_means.get(dim, None)
        if base is None:
            continue
        diff = round(media - base, 2)
        org_pct = max(0, min((media / 3) * 100, 100))
        base_pct = max(0, min((base / 3) * 100, 100))

        if media < 1.5:
            prioridade = "Prioridade alta"
            recomendacao = "Estruturar fundamentos da agenda estratégica (cenários, objetivos, metas e planos de ação)."
        elif media < 2.0:
            prioridade = "Prioridade média"
            recomendacao = "Fortalecer consistência e institucionalização das práticas estratégicas."
        else:
            prioridade = "Prioridade de consolidação"
            recomendacao = "Padronizar e ampliar a disseminação interna das práticas já existentes."

        cards_html_list.append(
            f'<div class="dim-card">'
            f'<strong>{html.escape(dim)}</strong>'
            f'<div><b>Média da organização:</b> {media:.2f} | <b>Base:</b> {base:.2f} | <b>Diferença:</b> {diff:+.2f}</div>'
            f'<div class="compare-row"><div class="compare-label">Organização</div>'
            f'<div class="compare-track"><div class="compare-fill-org" style="width:{org_pct:.1f}%;"></div></div></div>'
            f'<div class="compare-row"><div class="compare-label">Base nacional</div>'
            f'<div class="compare-track"><div class="compare-fill-base" style="width:{base_pct:.1f}%;"></div></div></div>'
            f'<div class="muted" style="margin-top:6px;"><b>{html.escape(prioridade)}:</b> {html.escape(recomendacao)}</div>'
            f'</div>'
        )

    html_dim_cards = "".join(cards_html_list)

    logo_b64 = file_to_base64(LOGO_PATH)
    logo_html = ""
    if logo_b64:
        logo_html = (
            '<div class="report-logo">'
            f'<img src="data:image/png;base64,{logo_b64}" alt="Logo Publix">'
            '</div>'
        )

    visual_score_html = (
        '<div class="visual-block">'
        '<div class="visual-title">Indicador visual de maturidade</div>'
        f'<div><b>Score geral:</b> {score_geral} / 3,0</div>'
        f'<div class="bar-track"><div class="bar-fill" style="width:{score_pct:.1f}%;"></div></div>'
        '<div class="bar-legend">Escala de 0 a 3</div>'
        + level_badges_html +
        '</div>'
    )

    html_relatorio = (
        '<div id="report-print-root" class="print-only">'
        '<div class="report-wrap">'
        '<div class="publix-band"></div>'
        '<div class="report-header">'
        '<div class="report-header-left">'
        '<div class="report-title">Relatório de Diagnóstico — Agenda Estratégica</div>'
        f'<div class="report-subtitle">Observatório de Governança para Resultados: Inteligência Artificial<br>Emitido em: {data_relatorio}</div>'
        '</div>'
        + logo_html +
        '</div>'
        '<div class="section-print-title">Identificação institucional</div>'
        '<div class="kpi-grid">'
        '<div class="kpi-card"><div class="label">Instituição</div><div class="value">' + instituicao_txt + '</div></div>'
        '<div class="kpi-card"><div class="label">Classificação</div><div class="value">' + poder_txt + ' | ' + esfera_txt + ' | ' + uf_txt + '</div></div>'
        '<div class="kpi-card"><div class="label">Respondente</div><div class="value">' + respondente_txt + '</div></div>'
        '<div class="kpi-card"><div class="label">Cargo / contato</div><div class="value">' + cargo_txt + ' | ' + email_txt + '</div></div>'
        '</div>'
        '<div class="section-print-title">Resultado geral</div>'
        '<div class="kpi-grid" style="grid-template-columns: 1fr 1fr 1fr;">'
        '<div class="kpi-card"><div class="label">Score geral</div><div class="value">' + score_geral + '</div></div>'
        '<div class="kpi-card"><div class="label">Nível de maturidade</div><div class="value">' + nivel + '</div></div>'
        '<div class="kpi-card"><div class="label">ID do diagnóstico</div><div class="value">' + diag_id_txt + '</div></div>'
        '</div>'
        '<div class="section-print-title">Visual executivo</div>'
        + visual_score_html +
        '<div class="section-print-title">Análise por dimensão</div>'
        + html_dim_cards +
        '</div>'
        '</div>'
    )

    st.markdown(html_relatorio, unsafe_allow_html=True)


# =========================================================
# ETAPA 6 — Chat com IA (só após e-mail confirmado)
# =========================================================
st.markdown('<div class="no-print">', unsafe_allow_html=True)
st.markdown("---")
st.subheader("Converse com a IA sobre o seu diagnóstico")

if not st.session_state.email_verificado or st.session_state.diagnostico_perfil_texto is None:
    if st.session_state.diagnostico_gerado:
        # Mostra seção "travada" visualmente para incentivar o preenchimento
        st.markdown(
            '<div class="locked-section">',
            unsafe_allow_html=True,
        )
        st.markdown(
            "_Exemplo de análise da IA: 'Sua organização está abaixo da média nacional em Agenda Estratégica. "
            "Os maiores gaps estão em Definição de Metas e Alinhamento com a Agenda de Desenvolvimento...'_"
        )
        st.markdown('</div>', unsafe_allow_html=True)
        st.caption("🔒 Confirme seu e-mail acima para desbloquear a IA especialista.")
else:
    for msg in st.session_state.chat_history:
        if msg["role"] == "user":
            with st.chat_message("user"):
                st.markdown(msg["content"])
        elif msg["role"] == "assistant":
            with st.chat_message("assistant"):
                st.markdown(msg["content"])

    prompt = st.chat_input("Faça uma pergunta para a IA sobre o diagnóstico da sua organização...")

    if prompt:
        user_msg = {"role": "user", "content": prompt}
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.chat_history.append(user_msg)

        with st.chat_message("assistant"):
            with st.spinner("Gerando resposta da IA..."):
                resposta = chamar_ia(
                    st.session_state.diagnostico_perfil_texto,
                    st.session_state.chat_history,
                )
                st.markdown(resposta)

        st.session_state.chat_history.append({"role": "assistant", "content": resposta})

st.markdown('</div>', unsafe_allow_html=True)


# =========================================================
# BOTÃO FLUTUANTE DE IMPRESSÃO (só após e-mail confirmado)
# =========================================================
if st.session_state.respondente_salvo:
    components.html(
        """
        <script>
        function printOnlyReport() {
            try {
                const rootDoc = window.parent && window.parent.document ? window.parent.document : document;
                const report = rootDoc.getElementById("report-print-root");
                if (!report) { alert("Relatório não encontrado para impressão."); return; }

                const styles = Array.from(rootDoc.querySelectorAll("style, link[rel='stylesheet']"))
                    .map(el => el.outerHTML).join("\\n");

                const extraPrintCss = `
                    <style>
                        @page { size: A4; margin: 12mm; }
                        html, body { background: #fff !important; margin: 0; padding: 0; }
                        body { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; font-family: sans-serif; }
                        .print-only { display: block !important; }
                        .report-wrap, .kpi-card, .dim-card, .visual-block { break-inside: avoid !important; page-break-inside: avoid !important; }
                    </style>`;

                const printWindow = window.open("", "_blank", "width=1024,height=768");
                if (!printWindow) { alert("Não foi possível abrir a janela de impressão. Verifique se o navegador bloqueou pop-up."); return; }

                printWindow.document.open();
                printWindow.document.write(`<!DOCTYPE html><html><head><meta charset="UTF-8" /><title>Relatório de Diagnóstico</title>${styles}${extraPrintCss}</head><body>${report.outerHTML}</body></html>`);
                printWindow.document.close();
                printWindow.onload = function() { printWindow.focus(); printWindow.print(); printWindow.close(); };
            } catch (e) { console.error(e); alert("Erro ao gerar impressão do relatório."); }
        }
        </script>
        <div style="position: fixed; bottom: 20px; right: 20px; z-index: 9999;">
            <button onclick="printOnlyReport()" style="background-color:#FFC728;border:none;padding:0.8rem 1.6rem;border-radius:999px;font-weight:700;cursor:pointer;font-size:0.95rem;box-shadow:0 4px 10px rgba(0,0,0,0.18);">
                Imprimir / salvar diagnóstico em PDF
            </button>
        </div>
        """,
        height=80,
    )


# =========================================================
# RODAPÉ
# =========================================================
st.markdown('<div class="no-print">', unsafe_allow_html=True)
st.markdown(
    """
<hr style="margin-top: 3rem; margin-bottom: 0.5rem;">
<div style="font-size: 0.85rem; color: #777777; text-align: right;">
    Desenvolvido pelo <span style="font-weight: 600; color: #FFC728;">Instituto Publix</span>
</div>
""",
    unsafe_allow_html=True,
)
st.markdown('</div>', unsafe_allow_html=True)