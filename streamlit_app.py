import streamlit as st
import pandas as pd
import numpy as np
import openai
import math
import os
from io import BytesIO




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

# --- BLOCO 1 ---
st.markdown("""
<style>
#MainMenu {visibility: hidden;}
header {visibility: hidden;}
footer {visibility: hidden;}

/* Remove "Manage app" */
.stAppDeployButton {display: none !important;}
button[title="Manage app"] {display: none !important;}
</style>
""", unsafe_allow_html=True)

# --- BLOCO 2 ---
st.markdown("""
<style>
/* Caixa de aviso (alert) nas cores Publix */
div[data-testid="stAlert"] {
    background-color: #FFC728 !important;  /* amarelo Publix */
    border-left: 6px solid #E0A600 !important;
    border-radius: 8px !important;
}

/* Força texto preto dentro do alerta */
div[data-testid="stAlert"] * {
    color: #000000 !important;    /* texto preto */
}
</style>
""", unsafe_allow_html=True)


# --- BLOCO 3 (o CSS que estava solto) ---
st.markdown("""
<style>
/* Remove barra inferior "Manage app" extra */
.stAppDeployButton {display: none !important;}
button[title="Manage app"] {display: none !important;}

/* Remove barra preta no canto inferior */
[data-testid="stStatusWidget"] {display: none !important;}

/* Scroll box */
.scroll-box {
    max-height: 450px;
    overflow-y: auto;
    padding-right: 10px;
    border: 1px solid #333;
    border-radius: 8px;
    padding: 10px;
}

/* Oculta botão flutuante */
button[aria-label="Manage app"],
button[title="Manage app"],
div[data-testid="manage-app-button"],
div[data-testid="ManageAppButton"] {
    display: none !important;
}

/* Esconde container fixo */
div[style*="position: fixed"][style*="bottom"][style*="right"] {
    display: none !important;
}
</style>
""", unsafe_allow_html=True)


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
    {"id": "3.1.1", "texto": "Os arranjos de colaboração e coordenação institucional existentes na organização são aderentes ao mandato institucional?", "dimensao": "Monitoramento e Avaliação"},
    {"id": "3.1.2", "texto": "Os arranjos existentes são aderentes aos processos de formulação, implementação, monitoramento e avaliação de políticas e programas?", "dimensao": "Monitoramento e Avaliação"},
    {"id": "3.2.1", "texto": "A organização participa da formulação de políticas públicas integradas à sua área de atuação?", "dimensao": "Monitoramento e Avaliação"},
    {"id": "3.2.2", "texto": "Os arranjos de colaboração e coordenação existentes fortalecem a atuação da organização na formulação de políticas públicas integradas à sua área de atuação?", "dimensao": "Monitoramento e Avaliação"},
    {"id": "3.3.1", "texto": "Os arranjos de colaboração e coordenação existentes fortalecem a atuação da organização na formulação de políticas públicas integradas com outros atores relevantes da área de atuação?", "dimensao": "Monitoramento e Avaliação"},
    {"id": "3.3.2", "texto": "Os representantes da organização envolvidos nos arranjos institucionais de colaboração e coordenação dispõem de capacidade decisória e autonomia para negociação junto aos demais envolvidos?", "dimensao": "Monitoramento e Avaliação"},
    {"id": "3.4.1", "texto": "As estruturas e os mecanismos de governança favorecem a participação da organização nos processos de formulação dos programas, considerando o mandato institucional?", "dimensao": "Monitoramento e Avaliação"},
    {"id": "3.4.2", "texto": " Existem estruturas permanentes ou fóruns ad hoc para a gestão das políticas e programas, considerando a participação de todo o conjunto de atores envolvidos nessa gestão?", "dimensao": "Monitoramento e Avaliação"},
    {"id": "3.5.1", "texto": "A organização aplica mecanismos de coordenação política e participação social por meio de instâncias como conselhos, conferências, comissões, etc, com participação de representantes daquela, da sociedade civil e beneficiários?", "dimensao": "Monitoramento e Avaliação"},
    {"id": "3.5.2", "texto": " Existem estruturas permanentes ou fóruns ad hoc para a gestão das políticas e programas, considerando a participação de todo o conjunto de atores envolvidos nessas instâncias de coordenação política e participação social?", "dimensao": "Monitoramento e Avaliação"},
    {"id": "3.6.1", "texto": "Os acordos formalizados por meio de cooperação técnica, parcerias, convênios, contratos, termos de ajustamento e instrumentos congêneres contém regras para propriedade, posse compartilhada e uso público de informações, bases de dados, sistemas de informação e tecnologias", "dimensao": "Monitoramento e Avaliação"},
    {"id": "3.6.2", "texto": "A organização dispõe de recursos humanos, financeiros, administrativos e tecnológicos para participar das instâncias e mecanismos de governança?", "dimensao": "Monitoramento e Avaliação"},
    {"id": "3.6.3", "texto": "Existem ações para fortalecer a capacidade de coordenadores e articuladores de políticas e programas, visando melhorar a sua atuação nas instâncias de governança?", "dimensao": "Monitoramento e Avaliação"},
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

OBSERVATORIO_MEANS = {
    "Agenda Estratégica": 1.92,
    "Estrutura da Implementação": 1.53,
    "Monitoramento e Avaliação": 1.47,
}


BASE_SINTETICA = """
Base nacional do Observatório de Maturidade – resumo sintético

1. Perfil da base
- 259 respondentes, provenientes de 153 organizações.
- Esferas: 54,8% Federal; 31,6% Estadual; 8,1% Municipal; restante entre privado, 3º setor e organismos internacionais.
- Poderes: Executivo (144), Legislativo (36), Judiciário (29), Empresas Públicas (24), Privado (11).
- Escolaridade predominante: Especialização (123), Graduação (66), Pós-graduação (36), MBA (26).

2. Maturidade geral
- Média nacional de maturidade: 1,64 (escala 0 a 3).
- Cerca de 22,45% dos órgãos estão no nível 3.
- Interpretação macro: a administração pública brasileira está, em geral, entre níveis iniciais e intermediários de maturidade.

3. Médias por dimensão
- Agenda Estratégica: 1,92
- Estrutura da Implementação: 1,53
- Monitoramento e Avaliação: 1,47
Leitura: a Estratégia é relativamente mais consolidada; a Implementação é mediana; Monitoramento e Avaliação aparece como o maior gargalo estrutural do país.

4. Médias por esfera
- Organismos Internacionais: 1,93
- Privado: 1,81
- Federal: 1,76
- Estadual: 1,41
- Municipal: 1,35
Leitura: organizações federais e privadas são significativamente mais maduras que estaduais e municipais.

5. Médias por poder
- Organismos Internacionais: 1,93
- Empresas Públicas: 1,87
- Privado: 1,82
- Legislativo: 1,73
- Executivo: 1,57
Insight crítico: o Executivo é o mais frequente na amostra, mas apresenta a menor maturidade média entre os poderes.

6. Padrão nacional por dimensão
- Estratégia tende a ser o ponto mais forte dos órgãos públicos.
- Implementação expõe fragilidades em competências, processos e arranjos institucionais.
- Monitoramento e Avaliação costuma ser o principal ponto crítico e a dimensão menos institucionalizada.

Use sempre essa lógica ao comparar o diagnóstico do órgão do usuário com a base nacional.
"""


# Médias da base por Poder (retiradas do BI)
BASE_MEDIA_POR_PODER = {
    "organismo internacional": 1.93,
    "empresa pública": 1.87,
    "privado": 1.82,
    "legislativo": 1.73,
    "executivo": 1.57,
    "confederação": 1.57,
}

# Médias da base por Esfera (retiradas do BI)
BASE_MEDIA_POR_ESFERA = {
    "federal": 1.76,
    "estadual": 1.41,
    "municipal": 1.35,
    "privado": 1.81,
    "organismo internacional": 1.93,
    # se quiser, pode adicionar "3º setor" depois que tiver o valor certinho
}

def _normalizar_label(texto: str) -> str | None:
    if not texto:
        return None
    t = texto.strip().lower()

    # mapeia algumas variações comuns
    substituicoes = {
        "poder executivo": "executivo",
        "poder legislativo": "legislativo",
        "poder judiciário": "judiciário",
        "judiciario": "judiciário",
        "judiciário": "judiciário",
        "org. internacional": "organismo internacional",
        "organismo int.": "organismo internacional",
    }
    t = substituicoes.get(t, t)
    return t


# Mapeia o nome usado no questionário para o nome da base do Observatório
DIM_ALIAS = {
    "Alinhamento da Estrutura implementadora": "Estrutura da Implementação",
}

# -------------------
# FUNÇÕES AUXILIARES
# -------------------

def limpar_texto_pdf(texto: str) -> str:
    """
    FPDF só aceita latin-1. Aqui trocamos alguns caracteres problemáticos
    e garantimos que o texto seja convertido sem quebrar.
    """
    if texto is None:
        return ""

    texto = (
        str(texto)
        .replace("–", "-")
        .replace("—", "-")
        .replace("“", '"')
        .replace("”", '"')
        .replace("’", "'")
    )

    # força para latin-1, substituindo o que não existir
    return texto.encode("latin-1", "replace").decode("latin-1")



def calcular_medias_por_dimensao(respostas_dict):
    """
    respostas_dict: {id_questao: nota}
    Usa QUESTOES para somar por dimensão e tirar a média.
    Retorna um dict: {dimensao_normalizada: média}
    """
    df = pd.DataFrame(QUESTOES)

    # Normaliza o nome da dimensão e aplica o alias para casar com a base
    df["dim_key"] = (
        df["dimensao"]
        .astype(str)
        .str.strip()
        .str.rstrip(",")
        .replace(DIM_ALIAS)  # <- aqui fazemos "Alinhamento..." -> "Estrutura da Implementação"
    )

    df["nota"] = df["id"].map(respostas_dict)
    medias = df.groupby("dim_key")["nota"].mean().round(2).to_dict()
    return medias


def montar_perfil_texto(instituicao, poder, esfera, estado,
                        respostas_dict, medias_dimensao, observatorio_means):
    """
    Gera um texto estruturado sobre o órgão, para ser passado como contexto para a IA.
    Agora inclui comparações com a base por Poder e por Esfera.
    """
    linhas = []

    # --- Identificação básica ---
    linhas.append(f"Instituição avaliada: {instituicao or 'Não informada'}")
    linhas.append(f"Poder: {poder or 'Não informado'}")
    linhas.append(f"Esfera: {esfera or 'Não informada'}")
    linhas.append(f"Estado: {estado or 'Não informado'}")
    linhas.append("")

    # --- Comparação por Poder / Esfera com a base do Observatório ---
    poder_norm = _normalizar_label(poder)
    esfera_norm = _normalizar_label(esfera)

    media_poder_base = BASE_MEDIA_POR_PODER.get(poder_norm) if poder_norm else None
    media_esfera_base = BASE_MEDIA_POR_ESFERA.get(esfera_norm) if esfera_norm else None

    if media_poder_base is not None:
        linhas.append(
            f"No Observatório de Maturidade, a média geral de maturidade para o "
            f"poder '{poder}' é {media_poder_base:.2f}."
        )
    if media_esfera_base is not None:
        linhas.append(
            f"Na esfera '{esfera}', a média geral de maturidade observada na base "
            f"é {media_esfera_base:.2f}."
        )
    if media_poder_base is not None or media_esfera_base is not None:
        linhas.append("")

    # --- Resumo por dimensão (comparando com a base) ---
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
        linhas.append(f"- {q['id']} | {q['dimensao']} | '{q['texto']}' -> nota {nota}")

    return "\n".join(linhas)


def chamar_ia(perfil_texto, user_message, chat_history):
    system_prompt = """
Você é o Radar Publix, assistente de IA especializado em gestão pública e maturidade institucional.
Sua função é analisar o diagnóstico de um órgão público e compará-lo com a base nacional do Observatório,
indicando pontos fortes, fragilidades e caminhos práticos de evolução.

Regras:
- Use SEMPRE os dados do diagnóstico do órgão e da base nacional fornecida.
- Compare de forma explícita: diga quando o órgão está acima, abaixo ou próximo da média da base.
- Considere, sempre que possível, o Poder, a Esfera e o Estado informados.
- Ajude o usuário a priorizar: indique o que é mais crítico atacar primeiro.
- Traga sugestões realistas para órgãos públicos brasileiros (restrições de tempo, orçamento, burocracia).
- Evite jargão excessivo; use linguagem clara e orientada à ação.
"""

    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "system",
            "content": "A seguir estão os principais achados da base nacional do Observatório de Maturidade:"
        },
        {"role": "system", "content": BASE_SINTETICA},
        {
            "role": "system",
            "content": "A seguir está o diagnóstico estruturado da organização do usuário:"
        },
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

def criar_pdf_diagnostico(texto: str, instituicao: str | None = None) -> BytesIO:
    """
    Gera um PDF simples com o texto do diagnóstico e retorna um buffer em memória.
    """
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_title("Diagnóstico de Maturidade")
    pdf.set_author("Radar Publix")

    # Título
    pdf.set_font("Helvetica", "B", 16)
    titulo = "Diagnóstico de Maturidade"
    if instituicao:
        titulo += f" - {instituicao}"
    pdf.multi_cell(0, 10, titulo)
    pdf.ln(8)

    # Corpo do texto
    pdf.set_font("Helvetica", "", 11)
    for linha in texto.split("\n"):
        if linha.strip() == "":
            pdf.ln(4)  # linha em branco = espaçamento
        else:
            pdf.multi_cell(0, 7, linha)

    # Gera bytes em memória
    pdf_bytes = pdf.output(dest="S").encode("latin-1")
    return BytesIO(pdf_bytes)



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

            # Botão para imprimir / salvar o diagnóstico em PDF (via navegador)
            st.markdown(
                """
                <div style="text-align: right; margin-top: 1rem;">
                    <button
                        onclick="window.print()"
                        style="
                            background-color: #FFC728;
                            border: none;
                            padding: 0.6rem 1.2rem;
                            border-radius: 999px;
                            font-weight: 600;
                            cursor: pointer;
                            font-size: 0.95rem;
                        "
                    >
                        Imprimir / salvar diagnóstico em PDF
                    </button>
                </div>
                """,
                unsafe_allow_html=True,
            )


    



        # DEBUG opcional para você conferir nota por questão
        df_debug = pd.DataFrame(QUESTOES)
        df_debug["nota"] = df_debug["id"].map(respostas)
        with st.expander("Ver respostas detalhadas (debug)"):
            st.dataframe(df_debug[["id", "dimensao", "nota"]])

        with st.expander("Ver diagnóstico completo (texto que vai para a IA)"):
            st.text(st.session_state.diagnostico_perfil_texto)

    # Botão para baixar o diagnóstico em PDF (se já houver diagnóstico gerado)
    if st.session_state.diagnostico_perfil_texto:
        pdf_buffer = criar_pdf_diagnostico(
            st.session_state.diagnostico_perfil_texto,
            instituicao=instituicao,
        )

        st.download_button(
            label="📄 Baixar diagnóstico em PDF",
            data=pdf_buffer,
            file_name="diagnostico_maturidade.pdf",
            mime="application/pdf",
            use_container_width=True,
        )


# -------- COLUNA DIREITA: CHAT --------
with col_chat:
    st.subheader("2. Converse com a IA sobre o seu diagnóstico")

    if st.session_state.diagnostico_perfil_texto is None:
        st.info("Preencha o diagnóstico na coluna ao lado para habilitar o chat.")
    elif "OPENAI_API_KEY" not in st.secrets:
        st.warning("API Key não encontrada nos secrets do Streamlit.")
    else:
        # Mostra o histórico
        for msg in st.session_state.chat_history:
            if msg["role"] == "user":
                with st.chat_message("user"):
                    st.markdown(msg["content"])
            elif msg["role"] == "assistant":
                with st.chat_message("assistant"):
                    st.markdown(msg["content"])

        # Caixa de entrada do chat
        prompt = st.chat_input(
            "Faça uma pergunta para a IA sobre o diagnóstico da sua organização..."
        )

        if prompt:
            # Adiciona mensagem do usuário ao histórico
            user_msg = {"role": "user", "content": prompt}
            st.session_state.chat_history.append(user_msg)

            # Mostra imediatamente a mensagem do usuário
            with st.chat_message("user"):
                st.markdown(prompt)

            # Gera resposta da IA
            with st.chat_message("assistant"):
                with st.spinner("Gerando resposta da IA..."):
                    resposta = chamar_ia(
                        st.session_state.diagnostico_perfil_texto,
                        prompt,
                        st.session_state.chat_history,
                    )
                    st.markdown(resposta)

            # Salva resposta no histórico
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
