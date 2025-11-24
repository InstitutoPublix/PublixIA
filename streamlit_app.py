import streamlit as st
import pandas as pd
import numpy as np
import openai
import math
import os



# -------------------
# CONFIGURAÇÕES GERAIS
# -------------------

st.set_page_config(page_title="Diagnóstico de Maturidade + IA", layout="wide")

# CSS geral de UX (sem sidebar, dark clean)
st.markdown(
    """
<style>
/* Remove completamente a barra lateral */
[data-testid="stSidebar"] {
    display: none !important;
}

/* Ajuste de largura do conteúdo principal */
.block-container {
    padding-top: 1.5rem !important;
    max-width: 1200px !important;
}

/* Pequeno espaçamento entre sliders */
div[data-testid="stSlider"] {
    margin-bottom: 0.7rem !important;
}
</style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    """
<h1 style='margin-bottom: -10px;'>Radar Publix</h1>

<p style='font-size: 1.05rem; line-height: 1.55;'>
O <strong>Radar Publix</strong> é a camada inteligente do Observatório de Maturidade, criada para transformar dados em clareza.
Ele interpreta suas respostas, compara com a base nacional do Observatório e identifica padrões, fragilidades e oportunidades de evolução, de maneira objetiva, estratégica e personalizada para o seu órgão.
</p>

<p style='font-size: 1.05rem; line-height: 1.55;'>
Combinando análise de dados, linguagem natural e a experiência da Publix em gestão pública,
o Radar oferece uma visão integrada e acionável sobre a maturidade institucional.
É um instrumento de navegação: aponta onde você está, ilumina caminhos possíveis e orienta decisões que fortalecem capacidades.
</p>

<p style='font-size: 1.05rem; line-height: 1.55; font-weight: 600;'>
Radar Publix — inteligência para evoluir capacidades.
</p>
""",
    unsafe_allow_html=True,
)


# -------------------
# API KEY
# -------------------

if "OPENAI_API_KEY" in st.secrets:
    openai.api_key = st.secrets["OPENAI_API_KEY"]
else:
    st.error("A API Key não foi encontrada em st.secrets. Configure OPENAI_API_KEY antes de usar o chat.")

# -------------------
# CSS extra (scroll-box se quiser usar)
# -------------------

st.markdown(
    """
<style>
/* Oculta menu hambúrguer, share, settings, star */
#MainMenu {visibility: hidden;}
header {visibility: hidden;}
footer {visibility: hidden;}

/* Remove a barra inferior "Manage app" (Streamlit Cloud) */
.stAppDeployButton {display: none !important;}
button[title="Manage app"] {display: none !important;}

/* Remove barra preta de controle do app no canto inferior direito */
[data-testid="stStatusWidget"] {display: none !important;}

.scroll-box {
    max-height: 450px;
    overflow-y: auto;
    padding-right: 10px;
    border: 1px solid #333;
    border-radius: 8px;
    padding: 10px;
}
/* Oculta botão flutuante "Manage app" do Streamlit Cloud */

/* Tenta pelos atributos mais comuns */
button[aria-label="Manage app"],
button[title="Manage app"],
div[data-testid="manage-app-button"],
div[data-testid="ManageAppButton"] {
    display: none !important;
}

/* Plano B: esconde qualquer container fixo no canto inferior direito
   usado pelo Streamlit pra esse botão */
div[style*="position: fixed"][style*="bottom: 0px"][style*="right: 0px"],
div[style*="position: fixed"][style*="bottom: 16px"][style*="right: 16px"] {
    display: none !important;
}
</style>
""",
    unsafe_allow_html=True,
)

# -------------------
# CARREGAR DADOS DO OBSERVATÓRIO
# -------------------

@st.cache_data
def load_observatory_stats(path_csv: str = "observatorio_resumo.csv"):
    """
    Esperado: um CSV com colunas:
    - dimension: nome da dimensão
    - mean_score: média da base
    """
    try:
        if os.path.exists(path_csv):
            df = pd.read_csv(path_csv)
            return df

        st.warning("Arquivo observatorio_resumo.csv não encontrado.")
        return None

    except Exception as e:
        st.warning(f"Erro ao carregar observatório: {e}")
        return None


observatorio_df = load_observatory_stats()

# Transformar em dict {dimensão_normalizada: média}
observatorio_means = {}
if (
    observatorio_df is not None
    and "dimension" in observatorio_df.columns
    and "mean_score" in observatorio_df.columns
):
    tmp = observatorio_df.copy()
    tmp["dim_key"] = tmp["dimension"].astype(str).str.strip().str.rstrip(",")
    observatorio_means = tmp.set_index("dim_key")["mean_score"].to_dict()


# -------------------
# QUESTÕES DO DIAGNÓSTICO
# -------------------

QUESTOES = [
    {"id": "1.1.1", "texto": "Identificam-se as forças e fraquezas, assim como as oportunidad...xternos da organização para formulação/revisão das estratégias.", "dimensao": "Agenda Estratégica"},
    {"id": "1.1.2", "texto": "Existe elaboração de cenários, ambientes futuros, considerando perspectivas políticas, econômicas, sociais, tecnológicas e demográficas?", "dimensao": "Agenda Estratégica"},
    {"id": "1.1.3", "texto": " Realiza-se a gestão de stakeholders (partes interessadas) que atuam na formulação/revisão das estratégias da organização?", "dimensao": "Agenda Estratégica"},
    {"id": "1.1.4", "texto": "Existem analises que buscam compreender o universo de políticas públicas que influenciam diretamente a atuação da organização?", "dimensao": "Agenda Estratégica"},
    {"id": "1.2.1", "texto": " A organização possui uma definição clara do seu mandato institucional que leve em conta os seus objetivos legais, institucionais e o mandato social?", "dimensao": "Agenda Estratégica"},
    {"id": "1.2.2", "texto": "O mandato institucional da organização é periodicamente revisado?", "dimensao": "Agenda Estratégica"},
    {"id": "1.2.3", "texto": "Há alinhamento entre o mandato institucional da organização e seu sistema de planejamento?", "dimensao": "Agenda Estratégica"},
    {"id": "1.3.1", "texto": "A organização possui visão institucional definida (documentos, website, documentos estratégicos, etc), sustentada em formulações que espelhem a situação desejada no futuro?", "dimensao": "Agenda Estratégica"},
    {"id": "1.3.2", "texto": "A visão institucional é amplamente divulgada para os públicos interno e externo?", "dimensao": "Agenda Estratégica"},
    {"id": "1.3.3", "texto": "A visão institucional está consolidada nos colaboradores da organização?", "dimensao": "Agenda Estratégica"},
    {"id": "1.4.1", "texto": " A organização possui objetivos estratégicos, declarando seus resultados esperados para o futuro?", "dimensao": "Agenda Estratégica"},
    {"id": "1.4.2", "texto": " Os objetivos estratégicos consideram o mandato institucional que norteia a atuação da organização; desafios e oportunidades provenientes das contexxternos e incumprimento legais?", "dimensao": "Agenda Estratégica"},
    {"id": "1.4.3", "texto": "Os objetivos estratégicos são amplamente divulgados para os públicos interno e externo?", "dimensao": "Agenda Estratégica"},
    {"id": "1.4.4", "texto": "Há envolvimento dos colaboradores na definição dos objetivos?", "dimensao": "Agenda Estratégica"},
    {"id": "1.4.5", "texto": "A definição dos objetivos estratégicos considera os riscos estratégicos futuros passíveis de ocorrer?", "dimensao": "Agenda Estratégica"},
    {"id": "1.5.1", "texto": "A organização dispõe de metas quantificadas, mensuráveis e alcançáveis para cada objetivo?", "dimensao": "Agenda Estratégica"},
    {"id": "1.5.2", "texto": "As metas são revisadas e ajustadas periodicamente?", "dimensao": "Agenda Estratégica"},
    {"id": "1.5.3", "texto": "As metas contemplam os resultados intermediários e finais da intervenção da organização?", "dimensao": "Agenda Estratégica"},
    {"id": "1.5.4", "texto": "As metas são definidas em horizontes temporais compatíveis com o tempo necessário para a produção dos resultados intermediários e finais?", "dimensao": "Agenda Estratégica"},
    {"id": "1.6.1", "texto": " Existem estratégias definindo como a organização realizará seus objetivos estratégicos em horizontes temporais de curto, médio e longo prazo?", "dimensao": "Agenda Estratégica"},
    {"id": "1.6.2", "texto": " As estratégias consideram as capacidades dos colaboradores, a estrutura da organização e características dos sistemas de planejamento, orçamento, recursos humanos, logística, tecnologia da informação e comunicação, gestão de conhecimento, sistemas de monitoramento e avaliação e outras dimensões associadas às capacidades organizacionais?", "dimensao": "Agenda Estratégica"},
    {"id": "1.6.3", "texto": "Os planos de ação articulam os objetivos estratégicos, metas, indicadores e instrumentos de acompanhamento de resultados?", "dimensao": "Agenda Estratégica"},
    {"id": "1.6.4", "texto": "Há mecanismos de alinhamento entre as estratégias institucionais e os planos dos órgãos colegiados efetores das políticas públicas?", "dimensao": "Agenda Estratégica"},
    {"id": "1.7.1", "texto": "Os planos da organização são aderentes ao plano de governo, planos de desenvolvimento nacionais, regionais, municipais e de outros atores?", "dimensao": "Agenda Estratégica"},
    {"id": "1.7.2", "texto": " A organização participa da elaboração da agenda de desenvolvimento econômico, social, ambiental, político e outros relevantes para o seu campo de atuação, a partir das reflexões promovidas no seu próprio ambiente interno?", "dimensao": "Agenda Estratégica"},
    {"id": "1.7.3", "texto": "As políticas, programas e ações para o desenvolvimento econômico, social, ambiental e político consideram os planos da organização?", "dimensao": "Agenda Estratégica"},
    {"id": "2.1.1", "texto": "A estrutura organizacional está formalizada?", "dimensao": "Alinhamento da Estrutura implementadora"},
    {"id": "2.1.2", "texto": "A estrutura organizacional foi elaborada considerando o atingimento dos objetivos institucionais?", "dimensao": "Alinhamento da Estrutura implementadora"},
    {"id": "2.1.3", "texto": "A estrutura organizacional (arranjo organizacional, rede etc.) foi elaborada considerando-se a natureza das políticas e programas de desenvolvimento nos quais a organização atua?", "dimensao": "Alinhamento da Estrutura implementadora"},
    {"id": "2.2.1", "texto": " Os fluxos de trabalho, atividades, competências e responsabilidades estão formalizados?", "dimensao": "Alinhamento da Estrutura implementadora"},
    {"id": "2.2.2", "texto": "Os fluxos de trabalho, atividades, competências e responsabilidades são derivados do planejamento institucional da organização?", "dimensao": "Alinhamento da Estrutura implementadora"},
    {"id": "2.2.3", "texto": " Há alinhamento entre as atividades, competências e responsabilidades dos colaboradores e as atribuições das unidades às quais estão vinculados, nos diferentes níveis da organização?", "dimensao": "Alinhamento da Estrutura implementadora"},
    {"id": "2.3.1", "texto": "As definições de atribuições contemplem claramente devolutivas, mecanismos de articulação institucional e conflitos gerados pelas áreas de interface com os demais órgãos, entidades e organismos autônomos?", "dimensao": "Alinhamento da Estrutura implementadora"},
    {"id": "2.3.2", "texto": "A organização produz planos, organogramas, regimentos e manual de atribuições, visando explicitar melhor a forma como se articulam os diferentes níveis internos?", "dimensao": "Alinhamento da Estrutura implementadora"},
    {"id": "2.3.3", "texto": " A organização trabalha com processos e procedimentos operacionais padronizados e bem difundidos, prevendo que os atores envolvidos disponham de poder de decisão para atividade de rotina, reconheçam a forma de exercer da forma mais adequada, racional e eficiente os meios disponíveis para alcançar os resultados esperados?", "dimensao": "Alinhamento da Estrutura implementadora"},
    {"id": "2.4.1", "texto": "A lógica de ocupação de cargos comissionados e funções gratificadas considera as competências técnicas e gerenciais necessárias para o posto de trabalho?", "dimensao": "Alinhamento da Estrutura implementadora"},
    {"id": "2.4.2", "texto": "O número de cargos comissionados ou funções gratificadas está dimensionado adequadamente?", "dimensao": "Alinhamento da Estrutura implementadora"},
    {"id": "2.4.3", "texto": "São estabelecidas metas e resultados pactuados com os ocupantes dos cargos comissionados ou funções gratificadas?", "dimensao": "Alinhamento da Estrutura implementadora"},
    {"id": "2.5.1", "texto": "As competências e responsabilidades dos governantes, gestores, eleitos, nomeados e envolvidos nos processos de escolha e execução das agendas de políticas públicas estão explicitadas?", "dimensao": "Alinhamento da Estrutura implementadora"},
    {"id": "2.5.2", "texto": "As competências e responsabilidades dos governantes, gestores e eleitos são aderentes aos objetivos e características das políticas públicas?", "dimensao": "Alinhamento da Estrutura implementadora"},
    {"id": "2.5.3", "texto": "As competências e responsabilidades dos executores e burocratas estão explicitadas?", "dimensao": "Alinhamento da Estrutura implementadora"},
    {"id": "2.5.4", "texto": "As competências e responsabilidades dos executores e burocratas levam em consideração eventual assimetria de informação entre aqueles que formulam as políticas e os que implementam?", "dimensao": "Alinhamento da Estrutura implementadora"},
    {"id": "2.6.1", "texto": "A realização dos processos e atividades dos órgãos dentro da organização é formalizada em documentos institucionais?", "dimensao": "Alinhamento da Estrutura implementadora"},
    {"id": "2.6.2", "texto": "A divisão de tarefas entre os órgãos menores encarregados das atividades operacionaliza-se em função dos objetivos da organização?", "dimensao": "Alinhamento da Estrutura implementadora"},
    {"id": "2.6.3", "texto": "A organização dispõe de estrutura formal definida pela dire...cimento de recursos humanos e apostilando quais os desdobramentos decorrentes da situação de falta?", "dimensao": "Alinhamento da Estrutura implementadora"},
    {"id": "3.1.1", "texto": "Os arranjos de colaboração e coordenação institucional existentes na organização são aderentes ao mandato institucional?", "dimensao": "Monitoramento e Avaliação,"},
    {"id": "3.1.2", "texto": "Os arranjos existentes são aderentes aos processos de formulação, implementação, monitoramento e avaliação de políticas e programas?", "dimensao": "Monitoramento e Avaliação,"},
    {"id": "3.2.1", "texto": "A organização participa da formulação de políticas públicas integradas à sua área de atuação?", "dimensao": "Monitoramento e Avaliação,"},
    {"id": "3.2.2", "texto": "Os arranjos de colaboração e coordenação existentes fortalecem a atuação da organização na formulação de políticas públicas integradas à sua área de atuação?", "dimensao": "Monitoramento e Avaliação,"},
    {"id": "3.3.1", "texto": "Os arranjos de colaboração e coordenação existentes fortalecem a atuação da organização na formulação de políticas públicas integradas com outros atores relevantes da área de atuação?", "dimensao": "Monitoramento e Avaliação,"},
    {"id": "3.3.2", "texto": "Os representantes da organização envolvidos nos arranjos institucionais de colaboração e coordenação dispõem de capacidade decisória e autonomia para negociação junto aos demais envolvidos?", "dimensao": "Monitoramento e Avaliação,"},
    {"id": "3.4.1", "texto": "As estruturas e os mecanismos de governança favorecem a participação da organização nos processos de formulação dos programas, considerando o mandato institucional?", "dimensao": "Monitoramento e Avaliação,"},
    {"id": "3.4.2", "texto": " Existem estruturas permanentes ou fóruns ad hoc para a gestão das políticas e programas, considerando a participação de todo o conjunto de atores envolvidos nessa gestão?", "dimensao": "Monitoramento e Avaliação,"},
    {"id": "3.5.1", "texto": "A organização aplica mecanismos de coordenação política e participação social por meio de instâncias como conselhos, conferências, comissões, etc, com participação de representantes daquela, da sociedade civil e beneficiários?", "dimensao": "Monitoramento e Avaliação,"},
    {"id": "3.5.2", "texto": " Existem estruturas permanentes ou fóruns ad hoc para a gestão das políticas e programas, considerando a participação de todo o conjunto de atores envolvidos nessas instâncias de coordenação política e participação social?", "dimensao": "Monitoramento e Avaliação,"},
    {"id": "3.6.1", "texto": "Os acordos formalizados por meio de cooperação técnica, parcerias, convênios, contratos, termos de ajustamento e instrumentos congêneres contém regras para propriedade, posse compartilhada e uso público de informações, bases de dados, sistemas de informação e tecnologias", "dimensao": "Monitoramento e Avaliação,"},
    {"id": "3.6.2", "texto": "A organização dispõe de recursos humanos, financeiros, administrativos e tecnológicos para participar das instâncias e mecanismos de governança?", "dimensao": "Monitoramento e Avaliação,"},
    {"id": "3.6.3", "texto": "Existem ações para fortalecer a capacidade de coordenadores e articuladores de políticas e programas, visando melhorar a sua atuação nas instâncias de governança?", "dimensao": "Monitoramento e Avaliação,"},
    {"id": "3.7.1", "texto": "A organização realiza avaliações para analisar o desempenho das políticas e programas nos quais atua?", "dimensao": "Monitoramento e Avaliação,"},
    {"id": "3.7.2", "texto": "As avaliações seguem procedimentos de institucionalização, incluindo processos para composição de equipes (área responsável, avaliadores, beneficiários diretos, etc.), acesso a dados, partilha de informações, recuperação de base documental e de dados, etc.?", "dimensao": "Monitoramento e Avaliação,"},
    {"id": "3.7.3", "texto": "A organização dispõe de instrumentos para elaborar propostas e executar ajustes nas políticas e programas com base nas avaliações realizadas?", "dimensao": "Monitoramento e Avaliação,"},
    {"id": "3.7.4", "texto": "A organização promove ações de capacitação específica visando fortalecer a capacidade de lidar com resultados advindos das avaliações e aprimorar o arcabouço legal e institucional que orienta a formulação, implementação, monitoramento e avaliação das políticas e programas?", "dimensao": "Monitoramento e Avaliação,"},
    {"id": "3.8.1", "texto": "A organização utiliza avaliações para fortalecer a capacidade de coordenação política e articulações para a governança das políticas e programas?", "dimensao": "Monitoramento e Avaliação,"},
    {"id": "3.8.2", "texto": "A organização utiliza avaliações para fortalecer arranjos colaborativos, assegurar o aprofundamento da coordenação política e fortalecer mecanismos de colaboração em rede?", "dimensao": "Monitoramento e Avaliação,"},
    {"id": "3.8.3", "texto": "A organização utiliza os resultados das avaliações no processo de alinhamento dos objetivos e metas das políticas e programas aos desafios de desenvolvimento econômico, social e ambiental?", "dimensao": "Monitoramento e Avaliação,"},
    {"id": "3.8.4", "texto": "A organização utiliza os resultados das avaliações para auxiliar no processo de coordenação e articulação com órgãos de controle externo?", "dimensao": "Monitoramento e Avaliação,"},
]

VALORES_ESCALA = {
    0: "0 - Inexistente",
    1: "1 - Muito incipiente",
    2: "2 - Parcialmente estruturado",
    3: "3 - Bem estruturado",
}

# -------------------
# FUNÇÕES AUXILIARES
# -------------------

def calcular_medias_por_dimensao(respostas_dict):
    """
    respostas_dict: {id_questao: nota}
    Usa QUESTOES para somar por dimensão e tirar a média.
    Retorna um dict: {dimensao_normalizada: média}
    """
    df = pd.DataFrame(QUESTOES)
    df["dim_key"] = df["dimensao"].astype(str).str.strip().str.rstrip(",")
    df["nota"] = df["id"].map(respostas_dict)
    medias = df.groupby("dim_key")["nota"].mean().round(2).to_dict()
    return medias


def montar_perfil_texto(instituicao, poder, esfera, estado,
                        respostas_dict, medias_dimensao, observatorio_means):
    """
    Gera um texto estruturado sobre o órgão, para ser passado como contexto para a IA.
    """
    linhas = []
    linhas.append(f"Instituição avaliada: {instituicao or 'Não informada'}")
    linhas.append(f"Poder: {poder or 'Não informado'}")
    linhas.append(f"Esfera: {esfera or 'Não informada'}")
    linhas.append(f"Estado: {estado or 'Não informado'}")
    linhas.append("")
    linhas.append("Resumo das notas por dimensão (escala 0 a 3):")
    # (deixa o restante da função exatamente como já está)


    for dim, media_orgao in medias_dimensao.items():
        media_base = observatorio_means.get(dim)
        if media_base is not None:
            diff = round(media_orgao - media_base, 2)
            situacao = (
                "acima da média da base"
                if diff > 0.1
                else "abaixo da média da base"
                if diff < -0.1
                else "próximo da média da base"
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


def chamar_ia(perfil_texto, user_message, chat_history):
    system_prompt = """
Você é um assistente de IA especializado em gestão pública e maturidade institucional.
Sua função é analisar o diagnóstico de um órgão público e sugerir caminhos práticos
para evoluir a maturidade nas diferentes dimensões (governança, processos, pessoas,
dados, tecnologia, etc.).

Regras:
- Use sempre as informações do diagnóstico e da comparação com a base fornecida.
- Comece resumindo brevemente os principais pontos fortes e fracos.
- Ajude o usuário a priorizar: indique por onde começar e o que é mais crítico.
- Traga sugestões realistas para o contexto de órgãos públicos brasileiros
  (considerando restrições de tempo, orçamento, burocracia).
- Evite jargão excessivo; explique em linguagem clara.
"""
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "system", "content": "A seguir está o diagnóstico estruturado da organização:"},
        {"role": "system", "content": perfil_texto},
    ]
    messages.extend(chat_history)
    messages.append({"role": "user", "content": user_message})

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
# STATE INICIAL
# -------------------

if "diagnostico_respostas" not in st.session_state:
    st.session_state.diagnostico_respostas = None

if "diagnostico_perfil_texto" not in st.session_state:
    st.session_state.diagnostico_perfil_texto = None

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# dicionário central de respostas (id -> nota)
if "respostas_dict" not in st.session_state:
    st.session_state.respostas_dict = {q["id"]: 1 for q in QUESTOES}

# estado da página do questionário
if "pagina_quest" not in st.session_state:
    st.session_state.pagina_quest = 1

# -------------------
# LAYOUT PRINCIPAL
# -------------------

col_form, col_chat = st.columns([2, 3])

# -------- COLUNA ESQUERDA: FORMULÁRIO --------
with col_form:
    st.subheader("1. Preencha o diagnóstico da sua organização")

    instituicao = st.text_input("Instituição", "")
    poder = st.text_input("Poder (ex.: Executivo, Judiciário, Legislativo)", "")
    esfera = st.text_input("Esfera (ex.: Federal, Estadual, Municipal)", "")
    estado = st.text_input("Estado (UF)", "")


    QUESTOES_POR_PAG = 10
    total_paginas = math.ceil(len(QUESTOES) / QUESTOES_POR_PAG)

    pagina = st.session_state.pagina_quest
    inicio = (pagina - 1) * QUESTOES_POR_PAG
    fim = min(inicio + QUESTOES_POR_PAG, len(QUESTOES))

    st.write(
        f"Responda cada afirmação numa escala de 0 a 3 (bloco {pagina} de {total_paginas}):"
    )

    # mostra apenas o bloco atual de questões
    for q in QUESTOES[inicio:fim]:
        atual = st.session_state.respostas_dict.get(q["id"], 1)
        novo_valor = st.slider(
            label=f"{q['id']} — {q['texto']}",
            min_value=0,
            max_value=3,
            value=atual,
            step=1,
            help="0 = Inexistente | 3 = Bem estruturado",
            key=f"slider_{q['id']}",
        )
        st.session_state.respostas_dict[q["id"]] = novo_valor

    # navegação entre blocos
    col1, col2, col3 = st.columns([1, 1, 2])

    def ir_anterior():
        if st.session_state.pagina_quest > 1:
            st.session_state.pagina_quest -= 1

    def ir_proximo():
        if st.session_state.pagina_quest < total_paginas:
            st.session_state.pagina_quest += 1

    with col1:
        st.button(
            "Anterior",
            key="btn_anterior",
            disabled=(pagina == 1),
            on_click=ir_anterior,
        )

    with col2:
        st.button(
            "Próximo",
            key="btn_proximo",
            disabled=(pagina == total_paginas),
            on_click=ir_proximo,
        )

    with col3:
        gerar = st.button("Gerar diagnóstico", key="btn_gerar", use_container_width=True)

    if gerar:
        respostas = st.session_state.respostas_dict.copy()

        st.session_state.diagnostico_respostas = respostas
        medias_dim = calcular_medias_por_dimensao(respostas)

        perfil_txt = montar_perfil_texto(
            instituicao,
            poder,
            esfera,
            estado,
            respostas,
            medias_dim,
            observatorio_means,
        )

        st.session_state.diagnostico_perfil_texto = perfil_txt

        st.success(
            "Diagnóstico gerado! Agora você pode ir para o chat com a IA na coluna ao lado."
        )

        st.write("### Resumo do diagnóstico (por dimensão)")
        for dim, media in medias_dim.items():
            base = observatorio_means.get(dim)
            if base is not None:
                st.write(f"- **{dim}**: {media} (base: {base:.2f})")
            else:
                st.write(f"- **{dim}**: {media}")

        # DEBUG opcional para você conferir nota por questão
        df_debug = pd.DataFrame(QUESTOES)
        df_debug["nota"] = df_debug["id"].map(respostas)
        with st.expander("Ver respostas detalhadas (debug)"):
            st.dataframe(df_debug[["id", "dimensao", "nota"]])

        with st.expander("Ver diagnóstico completo (texto que vai para a IA)"):
            st.text(st.session_state.diagnostico_perfil_texto)

# -------- COLUNA DIREITA: CHAT --------
with col_chat:
    st.subheader("2. Converse com a IA sobre o seu diagnóstico")

    if st.session_state.diagnostico_perfil_texto is None:
        st.info("Preencha o diagnóstico na coluna ao lado para habilitar o chat.")
    elif "OPENAI_API_KEY" not in st.secrets:
        st.warning("API Key não encontrada nos secrets do Streamlit.")
    else:
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        prompt = st.chat_input(
            "Faça uma pergunta para a IA sobre o diagnóstico da sua organização..."
        )
        if prompt:
            st.session_state.chat_history.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                with st.spinner("Gerando resposta da IA..."):
                    resposta = chamar_ia(
                        st.session_state.diagnostico_perfil_texto,
                        prompt,
                        st.session_state.chat_history,
                    )
                    st.markdown(resposta)

            st.session_state.chat_history.append(
                {"role": "assistant", "content": resposta}
            )
st.markdown(
    """
<hr style="margin-top: 3rem; margin-bottom: 0.5rem;">

<div style="font-size: 0.85rem; color: #777777; text-align: right;">
    Desenvolvido pelo <span style="font-weight: 600; color: #FFC728;">
    Instituto Publix
    </span>
</div>
""",
    unsafe_allow_html=True,
)
