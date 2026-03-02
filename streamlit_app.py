import streamlit as st
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
    page_title="Observatório de Governança para Resultados: IA",
    layout="centered"
)

LOGO_PATH = Path("publix_logo.png")


# -------------------
# UTILITÁRIOS DE CONFIG
# -------------------
def get_config_value(key: str):
    """
    Lê primeiro do ambiente (Render) e, se não existir, tenta st.secrets (Streamlit).
    Também limpa aspas acidentais nas pontas.
    """
    value = os.getenv(key)

    if value in (None, ""):
        try:
            value = st.secrets.get(key)
        except Exception:
            value = None

    if isinstance(value, str):
        value = value.strip().strip('"').strip("'")

    return value


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
            "GCP_TYPE",
            "GCP_PROJECT_ID",
            "GCP_PRIVATE_KEY_ID",
            "GCP_PRIVATE_KEY",
            "GCP_CLIENT_EMAIL",
            "GCP_CLIENT_ID",
            "GCP_AUTH_URI",
            "GCP_TOKEN_URI",
            "GCP_AUTH_PROVIDER_X509_CERT_URL",
            "GCP_CLIENT_X509_CERT_URL",
            "GCP_UNIVERSE_DOMAIN",
        ]

        faltando = [k for k in required_keys if not get_config_value(k)]
        if faltando:
            raise Exception(
                f"Secrets inválidos: faltam as chaves {', '.join(faltando)} no ambiente."
            )

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

        creds = Credentials.from_service_account_info(
            service_account_info,
            scopes=SCOPES
        )

        client = gspread.authorize(creds)

        try:
            planilha = client.open(SHEET_NAME)
        except SpreadsheetNotFound:
            raise Exception(
                f"Planilha não encontrada ou sem permissão: '{SHEET_NAME}'. "
                f"Compartilhe a planilha com o e-mail da service account ({service_account_info['client_email']})."
            )

        try:
            aba = planilha.worksheet(WORKSHEET_NAME)
        except WorksheetNotFound:
            raise Exception(
                f"A aba '{WORKSHEET_NAME}' não existe dentro da planilha '{SHEET_NAME}'."
            )

        return aba

    except Exception as e:
        raise Exception(f"Erro na conexão com Google Sheets: {e}")


def garantir_cabecalho(aba, registro: dict):
    try:
        primeira_linha = aba.row_values(1)
        cabecalho_esperado = list(registro.keys())

        # Se a planilha está vazia, insere cabeçalho
        if not primeira_linha:
            aba.insert_row(cabecalho_esperado, 1, value_input_option="USER_ENTERED")
            return

        # Se a primeira linha já é um registro (e não cabeçalho), insere o cabeçalho acima
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

st.markdown(
    """
<style>
[data-testid="stSidebar"] { display: none !important; }

.block-container {
    padding-top: 1.2rem !important;
    max-width: 1200px !important;
}

#MainMenu {visibility: hidden;}
header {visibility: hidden;}
footer {visibility: hidden;}

.stAppDeployButton {display: none !important;}
button[title="Manage app"] {display: none !important;}
[data-testid="stStatusWidget"] {display: none !important;}
button[aria-label="Manage app"],
div[data-testid="manage-app-button"],
div[data-testid="ManageAppButton"] {
    display: none !important;
}

div[data-testid="stSlider"] {
    margin-bottom: 0.7rem !important;
}

h1, h2, h3 {
    color: #111;
}

div[data-testid="stAlert"] {
    background-color: #FFF3C4 !important;
    border-left: 6px solid #FFC728 !important;
    border-radius: 8px !important;
}
div[data-testid="stAlert"] * { color: #000 !important; }

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
.result-card-title {
    font-weight: 700;
    margin-bottom: 3px;
}
.result-card-sub {
    color: #444;
    font-size: 0.94rem;
}

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

.report-header-left {
    flex: 1;
    min-width: 0;
}

.report-logo {
    flex: 0 0 auto;
    display: flex;
    align-items: center;
    justify-content: flex-end;
}

.report-logo img {
    max-height: 42px;
    width: auto;
    object-fit: contain;
}

.report-title {
    font-size: 1.25rem;
    font-weight: 800;
    margin-bottom: 2px;
}

.report-subtitle {
    color: #555;
    font-size: 0.92rem;
    margin-bottom: 10px;
}

.publix-band {
    height: 8px;
    background: linear-gradient(90deg, #FFC728 0%, #FFB300 100%);
    border-radius: 999px;
    margin-bottom: 12px;
}

.kpi-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
    margin: 10px 0 14px 0;
}

.kpi-card {
    background: #fff;
    border: 1px solid #e8e8e8;
    border-left: 5px solid #FFC728;
    border-radius: 10px;
    padding: 10px 12px;
}

.kpi-card .label {
    font-size: 0.82rem;
    color: #666;
    margin-bottom: 2px;
}

.kpi-card .value {
    font-weight: 800;
    font-size: 1.02rem;
    color: #111;
    word-break: break-word;
}

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

.dim-card strong {
    display: block;
    margin-bottom: 4px;
}

.muted {
    color: #666;
    font-size: 0.9rem;
}

.visual-block {
    border: 1px solid #e9e9e9;
    border-radius: 10px;
    padding: 12px;
    margin-bottom: 10px;
    background: #fff;
    break-inside: avoid;
    page-break-inside: avoid;
}

.visual-title {
    font-weight: 800;
    margin-bottom: 8px;
}

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

.bar-legend {
    font-size: 0.84rem;
    color: #666;
}

.compare-row {
    margin-top: 8px;
}

.compare-label {
    font-size: 0.84rem;
    font-weight: 700;
    margin-bottom: 2px;
}

.compare-track {
    width: 100%;
    height: 10px;
    background: #f1f1f1;
    border-radius: 999px;
    overflow: hidden;
}

.compare-fill-org {
    height: 100%;
    background: #FFC728;
    border-radius: 999px;
}

.compare-fill-base {
    height: 100%;
    background: #cfcfcf;
    border-radius: 999px;
}

.level-badges {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
    margin-top: 8px;
}

.level-badge {
    font-size: 0.78rem;
    padding: 4px 8px;
    border-radius: 999px;
    border: 1px solid #ddd;
    background: #fafafa;
    color: #555;
}

.level-badge.active {
    background: #fff3c4;
    border-color: #FFC728;
    color: #111;
    font-weight: 700;
}

.no-print { display: block; }
.print-only { display: none; }

@media print {
    @page {
        size: A4;
        margin: 12mm;
    }

    html, body {
        background: #fff !important;
    }

    body {
        -webkit-print-color-adjust: exact !important;
        print-color-adjust: exact !important;
    }

    .print-only {
        display: block !important;
    }

    .block-container {
        max-width: 100% !important;
        padding: 0 !important;
    }

    h1 { font-size: 18pt !important; margin-bottom: 6px !important; }
    h2 { font-size: 14pt !important; margin: 10px 0 6px 0 !important; }
    h3 { font-size: 12pt !important; margin: 8px 0 4px 0 !important; }

    p, li, div, span {
        font-size: 10.5pt !important;
        line-height: 1.35 !important;
    }

    .report-wrap,
    .result-card,
    .kpi-card,
    .dim-card,
    .visual-block {
        break-inside: avoid !important;
        page-break-inside: avoid !important;
    }

    hr {
        border: none !important;
        border-top: 1px solid #dcdcdc !important;
        margin: 8px 0 !important;
    }
}
</style>
""",
    unsafe_allow_html=True,
)

st.markdown('<div class="no-print">', unsafe_allow_html=True)
st.markdown(
    """
<h1 style='margin-bottom: -8px;'>Observatório de Governança para Resultados: Inteligência Artificial</h1>

<p style='font-size: 1.03rem; line-height: 1.52;'>
A <strong>Inteligência Artificial do Observatório da Governança para Resultados</strong> é uma camada criada para transformar dados em uma perspectiva de fortalecimento das instituições.
Ela interpreta suas respostas, compara com a base nacional do Observatório e identifica padrões, fragilidades e oportunidades de evolução, de maneira objetiva, estratégica e personalizada para o seu órgão.
</p>

<p style='font-size: 1.03rem; line-height: 1.52;'>
Combinando análise de dados, linguagem natural e a experiência do Instituto Publix em gestão para resultados, o Radar oferece uma visão integrada e acionável sobre a maturidade institucional.
É um instrumento de navegação: aponta onde você está, ilumina caminhos possíveis e orienta decisões que fortalecem capacidades.
</p>

<p style='font-size: 1.03rem; line-height: 1.52; font-weight: 600;'>
Observatório de Governança para Resultados — inteligência para evoluir capacidades na geração de resultados sustentáveis.
</p>
""",
    unsafe_allow_html=True,
)
st.markdown('</div>', unsafe_allow_html=True)

openai_api_key = get_config_value("OPENAI_API_KEY")
if not openai_api_key:
    st.error("OPENAI_API_KEY não encontrada. Configure em Secrets do Streamlit ou na variável de ambiente.")
    st.stop()

openai.api_key = openai_api_key

QUESTOES = [
    {"id": "1.1.1", "texto": "Identificam-se as forças e fraquezas, assim como as oportunidades e ameaças dos contextos internos e externos da organização para formulação/revisão das estratégias.", "dimensao": "Agenda Estratégica"},
    {"id": "1.1.2", "texto": "Existe elaboração de cenários, ambientes futuros, considerando perspectivas políticas, econômicas, sociais, tecnológicas e demográficas?", "dimensao": "Agenda Estratégica"},
    {"id": "1.1.3", "texto": "Realiza-se a gestão de stakeholders (partes interessadas) que atuam na formulação/revisão das estratégias da organização?", "dimensao": "Agenda Estratégica"},
    {"id": "1.1.4", "texto": "Existem análises que buscam compreender o universo de políticas públicas que influenciam diretamente a atuação da organização?", "dimensao": "Agenda Estratégica"},
    {"id": "1.2.1", "texto": "A organização possui uma definição clara do seu mandato institucional que leve em conta os seus objetivos legais, institucionais e o mandato social?", "dimensao": "Agenda Estratégica"},
    {"id": "1.2.2", "texto": "O mandato institucional da organização é periodicamente revisado?", "dimensao": "Agenda Estratégica"},
    {"id": "1.2.3", "texto": "Há alinhamento entre o mandato institucional da organização e seu sistema de planejamento?", "dimensao": "Agenda Estratégica"},
    {"id": "1.3.1", "texto": "A organização possui visão institucional definida (documentos, website, documentos estratégicos etc.), sustentada em formulações que espelhem a situação desejada no futuro?", "dimensao": "Agenda Estratégica"},
    {"id": "1.3.2", "texto": "A visão institucional é amplamente divulgada para os públicos interno e externo?", "dimensao": "Agenda Estratégica"},
    {"id": "1.3.3", "texto": "A visão institucional está consolidada nos colaboradores da organização?", "dimensao": "Agenda Estratégica"},
    {"id": "1.4.1", "texto": "A organização possui objetivos estratégicos, declarando seus resultados esperados para o futuro?", "dimensao": "Agenda Estratégica"},
    {"id": "1.4.2", "texto": "Os objetivos estratégicos consideram o mandato institucional, desafios e oportunidades dos contextos externos e internos, bem como requisitos legais?", "dimensao": "Agenda Estratégica"},
    {"id": "1.4.3", "texto": "Os objetivos estratégicos são amplamente divulgados para os públicos interno e externo?", "dimensao": "Agenda Estratégica"},
    {"id": "1.4.4", "texto": "Há envolvimento dos colaboradores na definição dos objetivos?", "dimensao": "Agenda Estratégica"},
    {"id": "1.4.5", "texto": "A definição dos objetivos estratégicos considera os riscos estratégicos futuros passíveis de ocorrer?", "dimensao": "Agenda Estratégica"},
    {"id": "1.5.1", "texto": "A organização dispõe de metas quantificadas, mensuráveis e alcançáveis para cada objetivo?", "dimensao": "Agenda Estratégica"},
    {"id": "1.5.2", "texto": "As metas são revisadas e ajustadas periodicamente?", "dimensao": "Agenda Estratégica"},
    {"id": "1.5.3", "texto": "As metas contemplam os resultados intermediários e finais da intervenção da organização?", "dimensao": "Agenda Estratégica"},
    {"id": "1.5.4", "texto": "As metas são definidas em horizontes temporais compatíveis com o tempo necessário para a produção dos resultados intermediários e finais?", "dimensao": "Agenda Estratégica"},
    {"id": "1.6.1", "texto": "Existem estratégias definindo como a organização realizará seus objetivos estratégicos em horizontes temporais de curto, médio e longo prazo?", "dimensao": "Agenda Estratégica"},
    {"id": "1.6.2", "texto": "As estratégias consideram as capacidades dos colaboradores, a estrutura da organização e características dos sistemas de planejamento, orçamento, recursos humanos, logística, tecnologia da informação e comunicação, gestão do conhecimento, monitoramento e avaliação?", "dimensao": "Agenda Estratégica"},
    {"id": "1.6.3", "texto": "Os planos de ação articulam objetivos estratégicos, metas, indicadores e instrumentos de acompanhamento de resultados?", "dimensao": "Agenda Estratégica"},
    {"id": "1.6.4", "texto": "Há mecanismos de alinhamento entre as estratégias institucionais e os planos dos órgãos colegiados efetores das políticas públicas?", "dimensao": "Agenda Estratégica"},
    {"id": "1.7.1", "texto": "Os planos da organização são aderentes ao plano de governo e a planos de desenvolvimento nacionais, regionais, municipais e de outros atores?", "dimensao": "Agenda Estratégica"},
    {"id": "1.7.2", "texto": "A organização participa da elaboração da agenda de desenvolvimento econômico, social, ambiental, político e outros temas relevantes para seu campo de atuação?", "dimensao": "Agenda Estratégica"},
    {"id": "1.7.3", "texto": "As políticas, programas e ações para o desenvolvimento econômico, social, ambiental e político consideram os planos da organização?", "dimensao": "Agenda Estratégica"},
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
        "empresa publica": "empresa pública",
        "org. internacional": "organismo internacional",
        "organismo int.": "organismo internacional",
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
        linhas.append(
            f"No Observatório de Maturidade, a média geral de maturidade para o poder '{poder}' é {media_poder_base:.2f}."
        )
    if media_esfera_base is not None:
        linhas.append(
            f"Na esfera '{esfera}', a média geral de maturidade observada na base é {media_esfera_base:.2f}."
        )
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

            linhas.append(
                f"- {dim}: {media_orgao:.2f} (média da base: {media_base:.2f}; situação: {situacao}, diferença: {diff:+.2f})"
            )

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
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.3,
        )
        return response.choices[0].message["content"]
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


if "diagnostico_respostas" not in st.session_state:
    st.session_state.diagnostico_respostas = None
if "diagnostico_perfil_texto" not in st.session_state:
    st.session_state.diagnostico_perfil_texto = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "respostas_dict" not in st.session_state:
    st.session_state.respostas_dict = {q["id"]: 1 for q in QUESTOES}
if "pagina_quest" not in st.session_state:
    st.session_state.pagina_quest = 1
if "medias_dimensao" not in st.session_state:
    st.session_state.medias_dimensao = None
if "diagnostico_gerado" not in st.session_state:
    st.session_state.diagnostico_gerado = False
if "respondente_salvo" not in st.session_state:
    st.session_state.respondente_salvo = False
if "registro_salvo" not in st.session_state:
    st.session_state.registro_salvo = None
if "dados_institucionais" not in st.session_state:
    st.session_state.dados_institucionais = None
if "etapa1_ok" not in st.session_state:
    st.session_state.etapa1_ok = False
if "dados_pessoais" not in st.session_state:
    st.session_state.dados_pessoais = None

st.markdown('<div class="no-print">', unsafe_allow_html=True)
st.subheader("1. Dados institucionais e autorização")

with st.form("form_dados_institucionais", clear_on_submit=False):
    c1, c2 = st.columns(2)

    with c1:
        instituicao = st.text_input("Instituição")
        poder = st.selectbox(
            "A qual poder sua instituição pertence?",
            [
                "",
                "Executivo",
                "Legislativo",
                "Judiciário",
                "Ministério Público",
                "Empresa pública",
                "Privado",
                "Organismo internacional",
                "Outro",
            ],
        )

    with c2:
        esfera = st.selectbox(
            "Esfera",
            ["", "Federal", "Estadual", "Municipal", "Privado", "Não se aplica"],
        )
        estado_uf = st.selectbox(
            "Estado (UF)",
            [
                "",
                "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA",
                "MG", "MS", "MT", "PA", "PB", "PE", "PI", "PR", "RJ", "RN",
                "RO", "RR", "RS", "SC", "SE", "SP", "TO"
            ],
        )

    st.markdown("### Autorização de uso das informações")
    autorizacao_uso = st.checkbox(
        "Autorizo o uso das informações inseridas neste diagnóstico para fins de análise, consolidação estatística e aperfeiçoamento do Observatório de Governança para Resultados.",
        value=False,
    )
    st.markdown(
        "<small><em>O sigilo das informações individuais institucionais será preservado, e quaisquer divulgações ocorrerão apenas de forma consolidada e anonimizada.</em></small>",
        unsafe_allow_html=True
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

st.markdown('<div class="no-print">', unsafe_allow_html=True)
st.markdown("---")
st.subheader("2. Agenda Estratégica")

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
        st.session_state.respondente_salvo = False
        st.session_state.diagnostico_perfil_texto = None
        st.session_state.registro_salvo = None
        st.session_state.chat_history = []
        st.session_state.dados_pessoais = None

        st.success("Diagnóstico gerado com sucesso!")

        st.write("### Resumo do diagnóstico (por dimensão)")
        for dim, media in medias_dim.items():
            base = observatorio_means.get(dim)
            if base is not None:
                diff = round(media - base, 2)
                st.markdown(
                    f"""
                    <div class="result-card">
                        <div class="result-card-title">{html.escape(dim)}</div>
                        <div class="result-card-sub">
                            Sua média: <strong>{media:.2f}</strong> | Base: <strong>{base:.2f}</strong> | Diferença: <strong>{diff:+.2f}</strong>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div class="no-print">', unsafe_allow_html=True)
if st.session_state.diagnostico_gerado:
    st.markdown("---")
    st.subheader("3. Liberação da IA especialista")

    st.markdown(
        """
<div class="action-box">
<strong>Para conversar com a IA especialista sobre a sua organização, informe os dados abaixo:</strong>
</div>
""",
        unsafe_allow_html=True,
    )

    with st.form("form_dados_pessoais_pos_diag", clear_on_submit=False):
        c1, c2 = st.columns(2)

        with c1:
            nome_respondente = st.text_input("Nome")
            email_respondente = st.text_input("E-mail")

        with c2:
            area_unidade = st.text_input("Área / Unidade")
            cargo_funcao = st.text_input("Cargo / Função")

        deseja_contato = st.checkbox(
            "Assinale esta opção se deseja que façamos contato para um diagnóstico mais completo.",
            value=False,
        )

        salvar_dados_pessoais = st.form_submit_button("Liberar chat com IA", use_container_width=True)

        if salvar_dados_pessoais:
            if not nome_respondente.strip():
                st.error("Preencha seu nome.")
            elif not email_respondente.strip():
                st.error("Preencha seu e-mail.")
            else:
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

                try:
                    salvar_registro_google_sheets(registro)
                except Exception as e:
                    st.error(str(e))
                    st.info("O diagnóstico foi gerado, mas houve falha no salvamento. Verifique os Secrets, o nome da planilha/aba e a permissão da service account.")
                    st.stop()

                perfil_txt = montar_perfil_texto(
                    dados_inst.get("instituicao"),
                    dados_inst.get("poder"),
                    dados_inst.get("esfera"),
                    dados_inst.get("estado_uf"),
                    respostas,
                    medias_dim,
                )

                st.session_state.diagnostico_perfil_texto = perfil_txt
                st.session_state.respondente_salvo = True
                st.session_state.registro_salvo = registro

                st.success("Perfeito! Chat com IA liberado e dados salvos com sucesso.")
st.markdown('</div>', unsafe_allow_html=True)

if st.session_state.respondente_salvo and st.session_state.registro_salvo:
    st.markdown('<div class="no-print">', unsafe_allow_html=True)

    r = st.session_state.registro_salvo

    st.markdown("---")
    st.subheader("Resumo executivo do diagnóstico")

    contato_msg = "Sim" if bool(r.get("deseja_contato_diagnostico_completo", False)) else "Não"

    st.markdown(
        f"""
        <div class="result-card">
            <div class="result-card-title">Instituição</div>
            <div class="result-card-sub">{html.escape(str(r.get('instituicao','')))} | {html.escape(str(r.get('poder','')))} | {html.escape(str(r.get('esfera','')))} | {html.escape(str(r.get('estado_uf','')))}</div>
        </div>
        <div class="result-card">
            <div class="result-card-title">Respondente</div>
            <div class="result-card-sub">{html.escape(str(r.get('nome_respondente','')))} ({html.escape(str(r.get('cargo_funcao','')))}) — {html.escape(str(r.get('email_respondente','')))}</div>
        </div>
        <div class="result-card">
            <div class="result-card-title">Interesse em contato</div>
            <div class="result-card-sub">Deseja contato para diagnóstico mais completo: <strong>{contato_msg}</strong></div>
        </div>
        <div class="result-card">
            <div class="result-card-title">Resultado geral</div>
            <div class="result-card-sub">Score geral: <strong>{html.escape(str(r.get('score_geral','')))}</strong> | Nível: <strong>{html.escape(str(r.get('nivel_maturidade','')))}</strong> | ID do diagnóstico: <strong>{html.escape(str(r.get('id_resposta','')))}</strong></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    medias_dim = st.session_state.medias_dimensao or {}
    for dim, media in medias_dim.items():
        base = observatorio_means.get(dim, None)
        if base is None:
            continue

        diff = round(media - base, 2)
        if media < 1.5:
            mensagem = "Prioridade alta: estruturar fundamentos da agenda estratégica (objetivos, metas, cenários e planos de ação)."
        elif media < 2.0:
            mensagem = "Prioridade média: fortalecer consistência, alinhamento e institucionalização das práticas estratégicas."
        else:
            mensagem = "Bom nível relativo: foco em consolidar, padronizar e ampliar disseminação interna das práticas estratégicas."

        st.markdown(
            f"""
            <div class="result-card">
                <div class="result-card-title">{html.escape(dim)} — interpretação rápida</div>
                <div class="result-card-sub">
                    Média: <strong>{media:.2f}</strong> | Base: <strong>{base:.2f}</strong> | Diferença: <strong>{diff:+.2f}</strong><br>
                    {html.escape(mensagem)}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown('</div>', unsafe_allow_html=True)

if st.session_state.respondente_salvo and st.session_state.registro_salvo:
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
            f'<div class="compare-row">'
            f'<div class="compare-label">Organização</div>'
            f'<div class="compare-track"><div class="compare-fill-org" style="width:{org_pct:.1f}%;"></div></div>'
            f'</div>'
            f'<div class="compare-row">'
            f'<div class="compare-label">Base nacional</div>'
            f'<div class="compare-track"><div class="compare-fill-base" style="width:{base_pct:.1f}%;"></div></div>'
            f'</div>'
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

st.markdown('<div class="no-print">', unsafe_allow_html=True)
st.markdown("---")
st.subheader("4. Converse com a IA sobre o seu diagnóstico")

if not st.session_state.respondente_salvo or st.session_state.diagnostico_perfil_texto is None:
    st.info("Gere o diagnóstico e preencha os dados de liberação da IA para habilitar o chat.")
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

if st.session_state.respondente_salvo:
    components.html(
        """
        <script>
        function printOnlyReport() {
            try {
                const rootDoc = window.parent && window.parent.document ? window.parent.document : document;
                const report = rootDoc.getElementById("report-print-root");

                if (!report) {
                    alert("Relatório não encontrado para impressão.");
                    return;
                }

                const styles = Array.from(rootDoc.querySelectorAll("style, link[rel='stylesheet']"))
                    .map(el => el.outerHTML)
                    .join("\\n");

                const extraPrintCss = `
                    <style>
                        @page { size: A4; margin: 12mm; }
                        html, body { background: #fff !important; margin: 0; padding: 0; }
                        body {
                            -webkit-print-color-adjust: exact !important;
                            print-color-adjust: exact !important;
                            font-family: sans-serif;
                        }
                        .print-only { display: block !important; }
                        .report-wrap, .kpi-card, .dim-card, .visual-block {
                            break-inside: avoid !important;
                            page-break-inside: avoid !important;
                        }
                    </style>
                `;

                const printWindow = window.open("", "_blank", "width=1024,height=768");
                if (!printWindow) {
                    alert("Não foi possível abrir a janela de impressão. Verifique se o navegador bloqueou pop-up.");
                    return;
                }

                printWindow.document.open();
                printWindow.document.write(`
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <meta charset="UTF-8" />
                        <title>Relatório de Diagnóstico</title>
                        ${styles}
                        ${extraPrintCss}
                    </head>
                    <body>
                        ${report.outerHTML}
                    </body>
                    </html>
                `);
                printWindow.document.close();

                printWindow.onload = function() {
                    printWindow.focus();
                    printWindow.print();
                    printWindow.close();
                };
            } catch (e) {
                console.error(e);
                alert("Erro ao gerar impressão do relatório.");
            }
        }
        </script>

        <div style="position: fixed; bottom: 20px; right: 20px; z-index: 9999;">
            <button
                onclick="printOnlyReport()"
                style="
                    background-color: #FFC728;
                    border: none;
                    padding: 0.8rem 1.6rem;
                    border-radius: 999px;
                    font-weight: 700;
                    cursor: pointer;
                    font-size: 0.95rem;
                    box-shadow: 0 4px 10px rgba(0,0,0,0.18);
                "
            >
                Imprimir / salvar diagnóstico em PDF
            </button>
        </div>
        """,
        height=80,
    )

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