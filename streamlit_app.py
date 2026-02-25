import streamlit as st
import pandas as pd
import math
import openai
import streamlit.components.v1 as components
import os
import uuid
from datetime import datetime
from pathlib import Path


# -------------------
# CONFIG GERAIS
# -------------------
st.set_page_config(page_title="Observatório de Governança para Resultados: IA", layout="centered")

st.markdown(
    """
<style>
[data-testid="stSidebar"] { display: none !important; }

.block-container {
    padding-top: 1.5rem !important;
    max-width: 1200px !important;
}

div[data-testid="stSlider"] { margin-bottom: 0.7rem !important; }

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

div[data-testid="stAlert"] {
    background-color: #FFC728 !important;
    border-left: 6px solid #E0A600 !important;
    border-radius: 8px !important;
}
div[data-testid="stAlert"] * { color: #000000 !important; }

h2 { margin-top: 1.2rem !important; margin-bottom: 0.4rem !important; }
h3 { margin-top: 0.6rem !important; margin-bottom: 0.3rem !important; }

.result-card {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-left: 5px solid #FFC728;
    border-radius: 10px;
    padding: 12px 14px;
    margin-bottom: 10px;
}
.result-card-title {
    font-weight: 700;
    margin-bottom: 4px;
}
.result-card-sub {
    color: #444;
    font-size: 0.93rem;
}

.action-box {
    background: #fff8e1;
    border: 1px solid #f3d36c;
    border-radius: 12px;
    padding: 12px 14px;
    margin: 8px 0 14px 0;
}

/* ---------- PRINT / PDF ---------- */
@media print {
    body {
        -webkit-print-color-adjust: exact !important;
        print-color-adjust: exact !important;
        background: #fff !important;
    }

    [data-testid="stChatInput"],
    .no-print,
    iframe,
    button,
    [role="button"],
    [data-testid="stForm"],
    [data-testid="stSlider"] {
        display: none !important;
    }

    .block-container {
        max-width: 100% !important;
        padding: 0.5rem 1rem !important;
    }

    h1, h2, h3 {
        page-break-after: avoid;
    }

    .result-card {
        break-inside: avoid;
        page-break-inside: avoid;
    }

    hr {
        border: none;
        border-top: 1px solid #ddd !important;
    }
}
</style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    """
<h1 style='margin-bottom: -10px;'>Observatório de Governança para Resultados: Inteligência Artificial</h1>

<p style='font-size: 1.05rem; line-height: 1.55;'>
A <strong>Inteligência Artificial do Observatório da Governança para Resultados</strong> é uma camada criada para transformar dados em uma perspectiva de fortalecimento das instituições. Ela interpreta suas respostas, compara com a base nacional do Observatório e identifica padrões, fragilidades e oportunidades de evolução, de maneira objetiva, estratégica e personalizada para o seu órgão.
</p>

<p style='font-size: 1.05rem; line-height: 1.55;'>
Combinando análise de dados, linguagem natural e a experiência do Instituto Publix em gestão para resultados, o Radar oferece uma visão integrada e acionável sobre a maturidade institucional. É um instrumento de navegação: aponta onde você está, ilumina caminhos possíveis e orienta decisões que fortalecem capacidades.
</p>

<p style='font-size: 1.05rem; line-height: 1.55; font-weight: 600;'>
Observatório de Governança para Resultados — inteligência para evoluir capacidades na geração de resultados sustentáveis.
</p>
""",
    unsafe_allow_html=True,
)


# -------------------
# API KEY
# -------------------
openai_api_key = os.getenv("OPENAI_API_KEY")

if not openai_api_key:
    st.error(
        "OPENAI_API_KEY não encontrada. Configure a variável de ambiente OPENAI_API_KEY."
    )
    st.stop()

openai.api_key = openai_api_key


# -------------------
# QUESTÕES
# -------------------
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

    # Demais dimensões permanecem na base original (se quiser reaproveitar depois)
    {"id": "2.1.1", "texto": "A estrutura organizacional está formalizada?", "dimensao": "Alinhamento da Estrutura implementadora"},
    {"id": "3.1.1", "texto": "Os arranjos de colaboração e coordenação institucional existentes na organização são aderentes ao mandato institucional?", "dimensao": "Monitoramento e Avaliação"},
]

# Mantém apenas Agenda Estratégica
QUESTOES = [q for q in QUESTOES if q["dimensao"] == "Agenda Estratégica"]


observatorio_means = {
    "Agenda Estratégica": 1.92,
}

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
    "ministerio publico": 1.57,
    "ministério público": 1.57,
}

BASE_MEDIA_POR_ESFERA = {
    "federal": 1.76,
    "estadual": 1.41,
    "municipal": 1.35,
    "privado": 1.81,
    "organismo internacional": 1.93,
}


# -------------------
# TÍTULOS E SUBTÍTULOS
# -------------------
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
                f"- {dim}: {media_orgao:.2f} "
                f"(média da base: {media_base:.2f}; situação: {situacao}, diferença: {diff:+.2f})"
            )
        else:
            linhas.append(f"- {dim}: {media_orgao:.2f} (sem comparativo na base)")

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


# -------------------
# PERSISTÊNCIA INTERNA (CSV NO SERVIDOR)
# -------------------
ARQUIVO_BASE_RESPONDENTES = Path("observatorio_respostas.csv")


def montar_registro_para_salvar(respondente: dict, respostas: dict, medias_dim: dict):
    media_geral = round(sum(respostas.values()) / len(respostas), 2) if respostas else None
    nivel = classificar_nivel(media_geral) if media_geral is not None else None

    registro = {
        "id_resposta": str(uuid.uuid4()),
        "data_hora": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "versao_instrumento": "agenda_estrategica_v1",
        "modulo": "Agenda Estratégica",

        "nome_respondente": respondente.get("nome_respondente", ""),
        "email_respondente": respondente.get("email_respondente", ""),
        "instituicao": respondente.get("instituicao", ""),
        "poder": respondente.get("poder", ""),
        "esfera": respondente.get("esfera", ""),
        "estado_uf": respondente.get("estado_uf", ""),
        "area_unidade": respondente.get("area_unidade", ""),
        "cargo_funcao": respondente.get("cargo_funcao", ""),
        "consentimento_lgpd": respondente.get("consentimento_lgpd", False),

        "score_geral": media_geral,
        "nivel_maturidade": nivel,
    }

    for dim, valor in medias_dim.items():
        col = f"score_dim_{dim.lower().replace(' ', '_').replace('ã', 'a').replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ó','o').replace('ú','u').replace('ç', 'c')}"
        registro[col] = round(float(valor), 2)

    for qid, nota in respostas.items():
        registro[f"q_{qid.replace('.', '_')}"] = nota

    return registro


def salvar_registro_csv(registro: dict):
    """
    Salva internamente no servidor. Não expõe exportação ao cliente.
    """
    df_novo = pd.DataFrame([registro])

    if ARQUIVO_BASE_RESPONDENTES.exists():
        try:
            df_existente = pd.read_csv(ARQUIVO_BASE_RESPONDENTES)
            cols = list(dict.fromkeys(list(df_existente.columns) + list(df_novo.columns)))
            df_existente = df_existente.reindex(columns=cols)
            df_novo = df_novo.reindex(columns=cols)
            df_final = pd.concat([df_existente, df_novo], ignore_index=True)
        except Exception:
            df_final = df_novo
    else:
        df_final = df_novo

    df_final.to_csv(ARQUIVO_BASE_RESPONDENTES, index=False, encoding="utf-8-sig")


# -------------------
# STATE
# -------------------
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


# -------------------
# ETAPA 1 — DIAGNÓSTICO
# -------------------
st.subheader("1. Preencha o diagnóstico da sua organização")
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

    st.success("Diagnóstico gerado! Agora preencha os dados do respondente para salvar e liberar o resultado completo.")

    st.write("### Resumo do diagnóstico (por dimensão)")
    for dim, media in medias_dim.items():
        base = observatorio_means.get(dim)
        if base is not None:
            diff = round(media - base, 2)
            st.markdown(
                f"""
                <div class="result-card">
                    <div class="result-card-title">{dim}</div>
                    <div class="result-card-sub">
                        Sua média: <strong>{media:.2f}</strong> | Base: <strong>{base:.2f}</strong> | Diferença: <strong>{diff:+.2f}</strong>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )


# -------------------
# ETAPA 2 — IDENTIFICAÇÃO DO RESPONDENTE (PÓS-DIAGNÓSTICO)
# -------------------
if st.session_state.diagnostico_gerado:
    st.markdown("---")
    st.subheader("2. Identificação do respondente e autorização")

    with st.form("form_respondente_pos_diag"):
        c1, c2 = st.columns(2)

        with c1:
            nome_respondente = st.text_input("Nome do respondente")
            email_respondente = st.text_input("E-mail")
            instituicao_pos = st.text_input("Instituição")
            poder_pos = st.selectbox(
                "Poder",
                ["", "Executivo", "Legislativo", "Judiciário", "Ministério Público", "Empresa pública", "Privado", "Organismo internacional", "Outro"],
                key="poder_pos",
            )

        with c2:
            area_unidade = st.text_input("Área / Unidade")
            cargo_funcao = st.text_input("Cargo / Função")
            esfera_pos = st.selectbox(
                "Esfera",
                ["", "Federal", "Estadual", "Municipal", "Privado", "Não se aplica"],
                key="esfera_pos",
            )
            estado_pos = st.selectbox(
                "Estado (UF)",
                ["", "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA",
                 "MG", "MS", "MT", "PA", "PB", "PE", "PI", "PR", "RJ", "RN",
                 "RO", "RR", "RS", "SC", "SE", "SP", "TO"],
                key="estado_pos",
            )

        st.markdown("### Autorização de uso das informações")
        consentimento_lgpd = st.checkbox(
            "Autorizo o uso das informações inseridas neste diagnóstico para fins de análise, consolidação estatística e aperfeiçoamento do Observatório de Governança para Resultados.",
            value=False,
            key="consent_pos",
        )

        st.markdown(
            "<small><em>O sigilo das informações individuais institucionais será preservado, e quaisquer divulgações ocorrerão apenas de forma consolidada e anonimizada.</em></small>",
            unsafe_allow_html=True
        )

        salvar_identificacao = st.form_submit_button("Salvar identificação e liberar resultado final", use_container_width=True)

        if salvar_identificacao:
            if not nome_respondente.strip():
                st.error("Preencha o nome do respondente.")
            elif not email_respondente.strip():
                st.error("Preencha o e-mail do respondente.")
            elif not instituicao_pos.strip():
                st.error("Preencha a instituição.")
            elif not consentimento_lgpd:
                st.error("É necessário autorizar o uso das informações para salvar o diagnóstico.")
            else:
                respondente = {
                    "nome_respondente": nome_respondente.strip(),
                    "email_respondente": email_respondente.strip(),
                    "instituicao": instituicao_pos.strip(),
                    "poder": poder_pos,
                    "esfera": esfera_pos,
                    "estado_uf": estado_pos,
                    "area_unidade": area_unidade.strip(),
                    "cargo_funcao": cargo_funcao.strip(),
                    "consentimento_lgpd": consentimento_lgpd,
                }

                respostas = st.session_state.diagnostico_respostas or {}
                medias_dim = st.session_state.medias_dimensao or {}

                registro = montar_registro_para_salvar(respondente, respostas, medias_dim)
                salvar_registro_csv(registro)  # <-- SALVAMENTO INTERNO

                perfil_txt = montar_perfil_texto(
                    instituicao_pos, poder_pos, esfera_pos, estado_pos, respostas, medias_dim
                )

                st.session_state.diagnostico_perfil_texto = perfil_txt
                st.session_state.respondente_salvo = True
                st.session_state.registro_salvo = registro

                st.success("Dados salvos com sucesso! Resultado, chat e PDF liberados.")


# -------------------
# RESUMO EXECUTIVO (MELHOR PARA PDF)
# -------------------
if st.session_state.respondente_salvo and st.session_state.registro_salvo:
    r = st.session_state.registro_salvo

    st.markdown("---")
    st.subheader("Resumo executivo do diagnóstico")

    st.markdown(
        f"""
        <div class="result-card">
            <div class="result-card-title">Instituição</div>
            <div class="result-card-sub">{r.get('instituicao','')} | {r.get('poder','')} | {r.get('esfera','')} | {r.get('estado_uf','')}</div>
        </div>
        <div class="result-card">
            <div class="result-card-title">Respondente</div>
            <div class="result-card-sub">{r.get('nome_respondente','')} ({r.get('cargo_funcao','')}) — {r.get('email_respondente','')}</div>
        </div>
        <div class="result-card">
            <div class="result-card-title">Resultado geral</div>
            <div class="result-card-sub">Score geral: <strong>{r.get('score_geral','')}</strong> | Nível: <strong>{r.get('nivel_maturidade','')}</strong> | ID do diagnóstico: <strong>{r.get('id_resposta','')}</strong></div>
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
                <div class="result-card-title">{dim} — interpretação rápida</div>
                <div class="result-card-sub">
                    Média: <strong>{media:.2f}</strong> | Base: <strong>{base:.2f}</strong> | Diferença: <strong>{diff:+.2f}</strong><br>
                    {mensagem}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        """
        <div class="action-box">
            <strong>Próximos passos:</strong> você pode conversar com a IA sobre o diagnóstico e gerar um PDF usando o botão no canto inferior direito.
        </div>
        """,
        unsafe_allow_html=True,
    )


# -------------------
# ETAPA 3 — CHAT COM IA
# -------------------
st.markdown("---")
st.subheader("3. Converse com a IA sobre o seu diagnóstico")

if not st.session_state.respondente_salvo or st.session_state.diagnostico_perfil_texto is None:
    st.info("Gere o diagnóstico e salve a identificação do respondente para habilitar o chat.")
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


# -------------------
# BOTÃO FLUTUANTE DE PDF (CLIENTE VÊ)
# -------------------
if st.session_state.respondente_salvo:
    components.html(
        """
        <script>
        function printPage() {
            try {
                if (window.parent && window.parent !== window) {
                    window.parent.print();
                } else if (window.top) {
                    window.top.print();
                } else {
                    window.print();
                }
            } catch (e) {
                window.print();
            }
        }
        </script>

        <div class="no-print" style="position: fixed; bottom: 20px; right: 20px; z-index: 9999;">
            <button
                onclick="printPage()"
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


# -------------------
# RODAPÉ
# -------------------
st.markdown(
    """
<hr style="margin-top: 3rem; margin-bottom: 0.5rem;">
<div style="font-size: 0.85rem; color: #777777; text-align: right;">
    Desenvolvido pelo <span style="font-weight: 600; color: #FFC728;">Instituto Publix</span>
</div>
""",
    unsafe_allow_html=True,
)