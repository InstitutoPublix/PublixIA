import streamlit as st
import pandas as pd
from openai import OpenAI
import openai
import os


# -------------------
# API KEY
# -------------------

if "OPENAI_API_KEY" in st.secrets:
    openai.api_key = st.secrets["OPENAI_API_KEY"]
else:
    st.error("A API Key não foi encontrada em st.secrets. Configure OPENAI_API_KEY antes de usar o chat.")

# -------------------
# CONFIGURAÇÕES GERAIS
# -------------------

st.set_page_config(page_title="Diagnóstico de Maturidade + IA", layout="wide")

st.title("Observatório de Maturidade + Assistente de IA")
st.write(
    "Responda ao diagnóstico, compare sua organização com a base do Observatório "
    "e converse com uma IA sobre como evoluir a maturidade do seu órgão público."
)




# -------------------
# CARREGAR DADOS DO OBSERVATÓRIO
# -------------------
@st.cache_data
def load_observatory_stats(path: str = "observatorio_resumo.csv"):
    """
    Esperado: um CSV com colunas, por exemplo:
    - dimension: nome da dimensão (Governança, Pessoas, Processos, etc.)
    - mean_score: média da base
    - p25, p50, p75 (opcional, se você tiver)
    """
    try:
        df = pd.read_csv(path)
        return df
    except Exception as e:
        st.sidebar.warning(f"Não foi possível carregar o observatório: {e}")
        return None

observatorio_df = load_observatory_stats()

# Transformar em dict para acesso rápido {dimensão: média}
observatorio_means = {}
if observatorio_df is not None and "dimension" in observatorio_df.columns and "mean_score" in observatorio_df.columns:
    observatorio_means = (
        observatorio_df
        .set_index("dimension")["mean_score"]
        .to_dict()
    )

# -------------------
# DEFINIR QUESTÕES DO DIAGNÓSTICO (EXEMPLO)
# -------------------
# Aqui você depois substitui pelo seu conjunto completo de ~70 questões.
QUESTOES = [
    {"id": "Q1", "texto": "O órgão possui instâncias formais de governança (comitês, conselhos, etc.)?", "dimensao": "Governança"},
    {"id": "Q2", "texto": "Os processos-chave estão mapeados e documentados?", "dimensao": "Processos"},
    {"id": "Q3", "texto": "Há uso sistemático de dados para apoiar decisões gerenciais?", "dimensao": "Dados"},
    {"id": "Q4", "texto": "Existem ações estruturadas de capacitação para o uso de tecnologias digitais?", "dimensao": "Pessoas"},
    {"id": "Q5", "texto": "Os sistemas de informação são integrados e conversam entre si?", "dimensao": "Tecnologia"},
]

VALORES_ESCALA = {
    0: "0 - Inexistente",
    1: "1 - Muito incipiente",
    2: "2 - Parcialmente estruturado",
    3: "3 - Bem estruturado"
}


# -------------------
# FUNÇÕES AUXILIARES
# -------------------

def calcular_medias_por_dimensao(respostas_dict):
    """
    respostas_dict: {id_questao: nota}
    Usa QUESTOES para somar por dimensão e tira média.
    Retorna um dict: {dimensao: média}
    """
    df = pd.DataFrame(QUESTOES)
    df["nota"] = df["id"].map(respostas_dict)
    medias = (
        df.groupby("dimensao")["nota"]
        .mean()
        .round(2)
        .to_dict()
    )
    return medias


def montar_perfil_texto(nome_orgao, respostas_dict, medias_dimensao, observatorio_means):
    """
    Gera um texto estruturado sobre o órgão, para ser passado como contexto para a IA.
    """
    linhas = []
    linhas.append(f"Organização avaliada: {nome_orgao or 'Não informado'}")
    linhas.append("")
    linhas.append("Resumo das notas por dimensão (escala 0 a 3):")
    
    for dim, media_orgao in medias_dimensao.items():
        media_base = observatorio_means.get(dim)
        if media_base is not None:
            diff = round(media_orgao - media_base, 2)
            situacao = (
                "acima da média da base" if diff > 0.1 else
                "abaixo da média da base" if diff < -0.1 else
                "próximo da média da base"
            )
            linhas.append(
                f"- {dim}: {media_orgao} (média da base: {media_base:.2f}; situação: {situacao}, diferença: {diff:+.2f})"
            )
        else:
            linhas.append(f"- {dim}: {media_orgao} (sem comparativo na base)")
    
    linhas.append("")
    linhas.append("Notas detalhadas por questão:")
    for q in QUESTOES:
        nota = respostas_dict.get(q["id"])
        linhas.append(f"- {q['id']} | {q['dimensao']} | '{q['texto']}' -> nota {nota}")
    
    return "\n".join(linhas)


def chamar_ia(client, perfil_texto, user_message, chat_history):
    """
    client: OpenAI()
    perfil_texto: texto com o diagnóstico e comparação
    user_message: mensagem atual do usuário no chat
    chat_history: lista de dicts [{'role': 'user'/'assistant', 'content': '...'}, ...]
    """
    system_prompt = """
Você é um assistente de IA especializado em gestão pública e maturidade institucional.
Sua função é analisar o diagnóstico de um órgão público e sugerir caminhos práticos
para evoluir a maturidade nas diferentes dimensões (governança, processos, pessoas,
dados, tecnologia, etc.).

Regras:
- Use SEMPRE as informações do diagnóstico e da comparação com a base fornecida.
- Comece resumindo brevemente os principais pontos fortes e fracos.
- Ajude o usuário a priorizar: indique por onde começar e o que é mais crítico.
- Traga sugestões realistas para o contexto de órgãos públicos brasileiros
  (considerando restrições de tempo, orçamento, burocracia).
- Evite jargão excessivo; explique os conceitos em linguagem clara.
- Não prometa nada impossível (por ex.: "resolver todos os problemas rapidamente").
- Se o usuário perguntar algo fora do escopo, responda brevemente e puxe de volta
  para o tema de maturidade institucional e melhoria do órgão.
"""
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "system", "content": "A seguir está o diagnóstico estruturado da organização:"},
        {"role": "system", "content": perfil_texto},
    ]
    messages.extend(chat_history)
    messages.append({"role": "user", "content": user_message})

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=messages,
        temperature=0.3,
    )

    return response.choices[0].message.content


# -------------------
# STATE INICIAL
# -------------------
if "diagnostico_respostas" not in st.session_state:
    st.session_state.diagnostico_respostas = None

if "diagnostico_perfil_texto" not in st.session_state:
    st.session_state.diagnostico_perfil_texto = None

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []


# -------------------
# LAYOUT PRINCIPAL
# -------------------

col_form, col_chat = st.columns([2, 3])

# -------- COLUNA ESQUERDA: FORMULÁRIO --------
with col_form:
    st.subheader("1. Preencha o diagnóstico da sua organização")

    nome_orgao = st.text_input("Nome do órgão/organização (opcional)", "")

    with st.form("form_diagnostico"):
        st.write("Responda cada afirmação numa escala de 0 a 3:")
        respostas = {}

        for q in QUESTOES:
            respostas[q["id"]] = st.slider(
                q["texto"],
                min_value=0,
                max_value=3,
                value=1,
                step=1,
                help="0 = Inexistente | 3 = Bem estruturado"
            )

        submitted = st.form_submit_button("Gerar diagnóstico")

    if submitted:
        st.session_state.diagnostico_respostas = respostas
        medias_dim = calcular_medias_por_dimensao(respostas)
        perfil_txt = montar_perfil_texto(nome_orgao, respostas, medias_dim, observatorio_means)
        st.session_state.diagnostico_perfil_texto = perfil_txt

        st.success("Diagnóstico gerado! Agora você pode ir para o chat com a IA na coluna ao lado.")

        st.write("### Resumo do diagnóstico (por dimensão)")
        for dim, media in medias_dim.items():
            base = observatorio_means.get(dim)
            if base is not None:
                st.write(f"- **{dim}**: {media} (base: {base:.2f})")
            else:
                st.write(f"- **{dim}**: {media}")

        with st.expander("Ver diagnóstico completo (texto que vai para a IA)"):
            st.text(st.session_state.diagnostico_perfil_texto)

# -------- COLUNA DIREITA: CHAT --------
with col_chat:
    st.subheader("2. Converse com a IA sobre o seu diagnóstico")

    if st.session_state.diagnostico_perfil_texto is None:
        st.info("Preencha o diagnóstico na coluna ao lado para habilitar o chat.")
    elif not client:
        st.warning("Informe sua OpenAI API Key na barra lateral para ativar o chat.")
    else:
        # Mostrar histórico
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        prompt = st.chat_input("Faça uma pergunta para a IA sobre o diagnóstico da sua organização...")
        if prompt:
            # Adiciona mensagem do usuário
            st.session_state.chat_history.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            # Chama IA
            with st.chat_message("assistant"):
                with st.spinner("Gerando resposta da IA..."):
                    resposta = chamar_ia(
                        client,
                        st.session_state.diagnostico_perfil_texto,
                        prompt,
                        st.session_state.chat_history
                    )
                    st.markdown(resposta)

            # Salva resposta no histórico
            st.session_state.chat_history.append({"role": "assistant", "content": resposta})
