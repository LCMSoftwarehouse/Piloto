import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import textwrap
import io
import os
import sqlite3
import base64
from datetime import datetime

from openai import OpenAI
import tempfile

# =========================================================
# CONFIGURAÇÃO OPENAI
# =========================================================
# A API key deve ser configurada como variável de ambiente ou nos secrets do Streamlit
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
if not OPENAI_API_KEY and hasattr(st, 'secrets') and "OPENAI_API_KEY" in st.secrets:
    OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY and OPENAI_API_KEY.strip() else None
OPENAI_ENABLED = client is not None

# =========================================================
# DIRETÓRIO BASE / BANCO / LOGO
# =========================================================
# Usar diretório relativo ao script para funcionar em qualquer ambiente
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# No Streamlit Cloud, usar diretório temporário para dados persistentes
# ATENÇÃO: No Streamlit Cloud, os dados são perdidos quando o app reinicia!
# Para persistência real, use um banco externo (Supabase, PlanetScale, etc.)
if os.environ.get("STREAMLIT_SHARING_MODE") or os.path.exists("/mount/src"):
    # Estamos no Streamlit Cloud
    DATA_DIR = tempfile.gettempdir()
else:
    # Estamos em ambiente local
    DATA_DIR = os.path.join(BASE_DIR, "data")
    os.makedirs(DATA_DIR, exist_ok=True)

LOGO_FILE = "image.png"
LOGO_PATH = os.path.join(BASE_DIR, LOGO_FILE)

DB_PATH = os.path.join(DATA_DIR, "avaliacoes_ade.db")

# =========================================================
# PALETA DE CORES – VERSÃO COMERCIAL
# =========================================================
COLOR2_BG_APP = "#ebf7f8"   # Fundo da aplicação (não está sendo muito usado)
COLOR3_BG_INPUT = "#d0e0eb" # Fundo das caixas de digitação
COLOR4_SUBTITLE = "#88abc2" # Subtítulos
COLOR5_TITLE = "#49708a"    # Títulos
COLOR_TEXT = "#333333"

PRIMARY_BLUE = COLOR5_TITLE
DARK_GRAY = COLOR_TEXT
LIGHT_GRAY = COLOR3_BG_INPUT
BORDER_GRAY = "#cbd5e1"

# Botões – azul CLARO e fonte branca
BUTTON_BLUE = "#3b82f6"
BUTTON_BLUE_HOVER = "#2563eb"

# =========================================================
# ANOS ESCOLARES
# =========================================================
ANOS_ESCOLARES = [
    "",
    "Educação Infantil - 4 anos",
    "Educação Infantil - 5 anos",
    "1º ano EF",
    "2º ano EF",
    "3º ano EF",
    "4º ano EF",
    "5º ano EF",
    "6º ano EF",
    "7º ano EF",
    "8º ano EF",
    "9º ano EF",
    "1º ano EM",
    "2º ano EM",
    "3º ano EM",
]


def ano_tem_boletim(ano_escolar: str) -> bool:
    """A partir do 2º ano EF consideramos boletim escolar/relatório de desempenho."""
    if not ano_escolar:
        return False
    if "2º ano EF" in ano_escolar:
        return True
    palavras_chave = [
        "3º ano EF", "4º ano EF", "5º ano EF", "6º ano EF", "7º ano EF",
        "8º ano EF", "9º ano EF", "1º ano EM", "2º ano EM", "3º ano EM"
    ]
    return any(p in ano_escolar for p in palavras_chave)


# =========================================================
# DISCIPLINAS OBRIGATÓRIAS (BOLETIM) – VISÃO SIMPLIFICADA
# =========================================================
def get_disciplinas_boletim_mec(ano_escolar: str):
    """
    Retorna lista base de disciplinas para o boletim por etapa.
    Essa lista é simplificada e pode ser ajustada conforme a matriz da escola.
    """
    if any(x in ano_escolar for x in ["2º ano EF", "3º ano EF", "4º ano EF", "5º ano EF"]):
        # Anos iniciais EF
        return [
            "Língua Portuguesa",
            "Matemática",
            "Ciências",
            "História",
            "Geografia",
            "Arte",
            "Educação Física",
            "Inglês",
        ]
    if any(x in ano_escolar for x in ["6º ano EF", "7º ano EF", "8º ano EF", "9º ano EF"]):
        # Anos finais EF
        return [
            "Língua Portuguesa",
            "Matemática",
            "Ciências",
            "História",
            "Geografia",
            "Arte",
            "Educação Física",
            "Inglês",
        ]
    if "ano EM" in ano_escolar:
        # Ensino Médio (organização simplificada)
        return [
            "Língua Portuguesa / Literatura",
            "Matemática",
            "Inglês",
            "História",
            "Geografia",
            "Física",
            "Química",
            "Biologia",
            "Arte",
            "Educação Física",
            "Projeto de Vida",
        ]
    # fallback
    return [
        "Língua Portuguesa",
        "Matemática",
        "Ciências",
        "História",
        "Geografia",
        "Arte",
        "Educação Física",
    ]


# =========================================================
# INSTRUMENTOS POR ANO (BNCC – VISÃO SINTÉTICA POR ETAPA)
# =========================================================
def instrumento_ei():
    return {
        "CE1": {
            "nome": "Eu, o outro e o nós",
            "itens": [
                ("CE1_1", "Interage com colegas e adultos em diferentes situações do cotidiano escolar."),
                ("CE1_2", "Demonstra atitudes de cuidado consigo, com o outro e com o ambiente."),
                ("CE1_3", "Respeita combinados construídos coletivamente na turma."),
            ],
        },
        "CE2": {
            "nome": "Corpo, gestos e movimentos",
            "itens": [
                ("CE2_1", "Explora movimentos do corpo em brincadeiras e jogos."),
                ("CE2_2", "Coordena gestos em atividades de desenho, pintura e manipulação de objetos."),
                ("CE2_3", "Participa de atividades que envolvem equilíbrio, força e deslocamento."),
            ],
        },
        "CE3": {
            "nome": "Traços, sons, cores e formas",
            "itens": [
                ("CE3_1", "Utiliza diferentes materiais para desenhar, pintar e modelar."),
                ("CE3_2", "Explora sons, ritmos e músicas em atividades propostas."),
                ("CE3_3", "Expressa ideias e sentimentos em produções visuais ou sonoras."),
            ],
        },
        "CE4": {
            "nome": "Escuta, fala, pensamento e imaginação",
            "itens": [
                ("CE4_1", "Escuta histórias, relatos e orientações, demonstrando atenção."),
                ("CE4_2", "Expressa-se oralmente para relatar fatos, sentimentos e necessidades."),
                ("CE4_3", "Participa de conversas, fazendo perguntas e comentários pertinentes."),
            ],
        },
        "CE5": {
            "nome": "Espaços, tempos, quantidades, relações e transformações",
            "itens": [
                ("CE5_1", "Observa e compara tamanhos, formas e quantidades em situações do cotidiano."),
                ("CE5_2", "Reconhece rotinas e sequências de acontecimentos na escola."),
                ("CE5_3", "Participa de situações de contagem, organização de objetos e resolução de pequenos problemas."),
            ],
        },
    }


def instrumento_1_ano_ef():
    return {
        "LP": {
            "nome": "Língua Portuguesa – Alfabetização inicial",
            "itens": [
                ("LP1_1", "Reconhece letras do alfabeto em diferentes contextos."),
                ("LP1_2", "Identifica seu nome e o de colegas em materiais impressos."),
                ("LP1_3", "Demonstra interesse por ouvir e comentar histórias, parlendas e cantigas."),
                ("LP1_4", "Começa a relacionar sons da fala com letras e sílabas."),
            ],
        },
        "MAT": {
            "nome": "Matemática – Números e operações",
            "itens": [
                ("MAT1_1", "Conta objetos em situações do cotidiano."),
                ("MAT1_2", "Compara quantidades (mais, menos, igual)."),
                ("MAT1_3", "Reconhece números em diferentes contextos (sala, materiais, jogos)."),
            ],
        },
        "CIE": {
            "nome": "Ciências da Natureza – Mundo físico e seres vivos",
            "itens": [
                ("CIE1_1", "Observa características de plantas, animais e ambiente ao redor."),
                ("CIE1_2", "Participa de conversas sobre cuidados com o corpo e higiene."),
            ],
        },
        "HGE": {
            "nome": "História e Geografia – Vivências e espaços de convivência",
            "itens": [
                ("HGE1_1", "Reconhece a escola como espaço coletivo de convivência."),
                ("HGE1_2", "Relata aspectos de sua rotina e de sua família."),
            ],
        },
        "SOC": {
            "nome": "Socioemocional – Convivência e autorregulação",
            "itens": [
                ("SOC1_1", "Demonstra cooperação em atividades em grupo."),
                ("SOC1_2", "Lida com frustrações e espera a sua vez com apoio do adulto."),
            ],
        },
    }


def instrumento_2a5_ef():
    return {
        "LP": {
            "nome": "Língua Portuguesa – Leitura e escrita",
            "itens": [
                ("LP2_1", "Lê textos curtos, identificando informações principais."),
                ("LP2_2", "Escreve pequenos textos com coerência, ainda que com ajustes ortográficos."),
                ("LP2_3", "Revisa a própria escrita com apoio do professor."),
            ],
        },
        "MAT": {
            "nome": "Matemática – Números, operações e resolução de problemas",
            "itens": [
                ("MAT2_1", "Resolve situações-problema envolvendo adição e subtração."),
                ("MAT2_2", "Utiliza estratégias para calcular e conferir resultados."),
                ("MAT2_3", "Reconhece e utiliza noções de multiplicação e divisão em contextos cotidianos."),
            ],
        },
        "CIE": {
            "nome": "Ciências – Ambiente, corpo humano e tecnologia",
            "itens": [
                ("CIE2_1", "Reconhece relações entre hábitos de vida e saúde."),
                ("CIE2_2", "Participa de atividades de investigação e experimentação."),
            ],
        },
        "HGE": {
            "nome": "História e Geografia – Tempo, espaço e sociedade",
            "itens": [
                ("HGE2_1", "Localiza-se em mapas simples e representações de espaço."),
                ("HGE2_2", "Reconhece mudanças e permanências em fatos do cotidiano e de sua comunidade."),
            ],
        },
        "SOC": {
            "nome": "Socioemocional – Projeto de vida e convivência",
            "itens": [
                ("SOC2_1", "Respeita opiniões diferentes e dialoga em situações de conflito."),
                ("SOC2_2", "Organiza materiais e tarefas, com crescente autonomia."),
            ],
        },
    }


def instrumento_6a9_ef():
    return {
        "LP": {
            "nome": "Língua Portuguesa – Compreensão e produção de textos",
            "itens": [
                ("LP3_1", "Lê textos de diferentes gêneros, identificando ideias principais e inferências."),
                ("LP3_2", "Produz textos adequados ao gênero solicitado, revisando com autonomia crescente."),
            ],
        },
        "MAT": {
            "nome": "Matemática – Números, álgebra e geometria",
            "itens": [
                ("MAT3_1", "Resolve problemas envolvendo operações com números naturais e racionais."),
                ("MAT3_2", "Utiliza representações variadas (tabelas, gráficos, expressões) para resolver problemas."),
            ],
        },
        "CIE": {
            "nome": "Ciências – Vida, terra e universo",
            "itens": [
                ("CIE3_1", "Analisa fenômenos naturais com base em conceitos científicos trabalhados em sala."),
                ("CIE3_2", "Participa de atividades experimentais, registrando observações e conclusões."),
            ],
        },
        "HGE": {
            "nome": "História e Geografia – Sociedade, cultura e território",
            "itens": [
                ("HGE3_1", "Relaciona fatos históricos e geográficos a contextos atuais."),
                ("HGE3_2", "Analisa diferentes fontes de informação (textos, mapas, imagens, gráficos)."),
            ],
        },
        "SOC": {
            "nome": "Socioemocional – Autonomia, responsabilidade e convivência",
            "itens": [
                ("SOC3_1", "Assume responsabilidades em projetos e trabalhos em grupo."),
                ("SOC3_2", "Lida com pressões acadêmicas e sociais com busca de apoio adequado."),
            ],
        },
    }


def instrumento_em():
    return {
        "LCH": {
            "nome": "Linguagens e Ciências Humanas",
            "itens": [
                ("LCH1_1", "Analisa criticamente textos e discursos de diferentes mídias."),
                ("LCH1_2", "Participa de debates, posicionando-se de forma fundamentada e respeitosa."),
            ],
        },
        "CNM": {
            "nome": "Ciências da Natureza e Matemática",
            "itens": [
                ("CNM1_1", "Aplica conceitos científicos e matemáticos na resolução de problemas do cotidiano."),
                ("CNM1_2", "Interpreta dados, tabelas e gráficos em diferentes contextos."),
            ],
        },
        "PV": {
            "nome": "Projeto de Vida",
            "itens": [
                ("PV1_1", "Define metas acadêmicas e profissionais de curto e médio prazo."),
                ("PV1_2", "Toma decisões considerando suas potencialidades e interesses."),
            ],
        },
        "SOC": {
            "nome": "Socioemocional – Autonomia e participação social",
            "itens": [
                ("SOC4_1", "Participa de ações coletivas na escola ou comunidade."),
                ("SOC4_2", "Administra o tempo de estudo e outras responsabilidades com autonomia crescente."),
            ],
        },
    }


def get_instrumento_para_ano(ano_escolar: str):
    if "Educação Infantil" in ano_escolar:
        return instrumento_ei()
    if "1º ano EF" in ano_escolar:
        return instrumento_1_ano_ef()
    if any(x in ano_escolar for x in ["2º ano EF", "3º ano EF", "4º ano EF", "5º ano EF"]):
        return instrumento_2a5_ef()
    if any(x in ano_escolar for x in ["6º ano EF", "7º ano EF", "8º ano EF", "9º ano EF"]):
        return instrumento_6a9_ef()
    if "ano EM" in ano_escolar:
        return instrumento_em()
    return instrumento_2a5_ef()


# =========================================================
# CONFIG STREAMLIT
# =========================================================
st.set_page_config(
    page_title="Plataforma ADE – Avaliação e Desenvolvimento Educacional",
    layout="wide"
)

# =========================================================
# CSS – TEMA COMERCIAL
# =========================================================
st.markdown(
    f"""
    <style>
    :root, html, body {{
        color-scheme: light only !important;
    }}

    html, body, .main, .stApp,
    [data-testid="stAppViewContainer"],
    [data-testid="stHeader"],
    [data-testid="stToolbar"],
    [data-testid="stDecoration"],
    [data-testid="stStatusWidget"],
    .block-container {{
        background-color: #FFFFFF !important;
        color: {DARK_GRAY} !important;
    }}

    [data-testid="stSidebar"],
    [data-testid="stSidebarContent"],
    section[data-testid="stSidebar"] > div {{
        background-color: #FFFFFF !important;
    }}

    p, span, label, div, li, td, th,
    .stMarkdown, .stText,
    [data-testid="stMarkdownContainer"],
    [data-testid="stMarkdownContainer"] p,
    [data-testid="stMarkdownContainer"] span {{
        color: {DARK_GRAY} !important;
    }}

    h1, [data-testid="stMarkdownContainer"] h1 {{
        color: {PRIMARY_BLUE} !important;
        font-weight: 700 !important;
    }}

    h2, h3,
    [data-testid="stMarkdownContainer"] h2,
    [data-testid="stMarkdownContainer"] h3 {{
        color: {DARK_GRAY} !important;
    }}

    .ade-title {{
        color: {PRIMARY_BLUE} !important;
        font-weight: 700;
        font-size: 30px;
    }}
    .ade-subtitle {{
        color: #555555 !important;
        font-size: 14px;
    }}

    /* Inputs texto */
    input, textarea,
    .stTextInput input,
    .stTextArea textarea,
    [data-testid="stTextInput"] input,
    [data-testid="stTextArea"] textarea,
    [data-baseweb="input"] input,
    [data-baseweb="textarea"] textarea {{
        background-color: {LIGHT_GRAY} !important;
        color: {DARK_GRAY} !important;
        border: 1px solid {BORDER_GRAY} !important;
        border-radius: 8px !important;
        -webkit-text-fill-color: {DARK_GRAY} !important;
        padding: 8px 10px !important;
    }}
    input:focus, textarea:focus,
    .stTextInput input:focus,
    .stTextArea textarea:focus {{
        border-color: {PRIMARY_BLUE} !important;
        outline: none !important;
        box-shadow: 0 0 0 2px rgba(18,55,91,0.15) !important;
    }}
    input::placeholder, textarea::placeholder {{
        color: #AAAAAA !important;
        -webkit-text-fill-color: #AAAAAA !important;
    }}

    [data-baseweb="input"],
    [data-baseweb="textarea"],
    [data-baseweb="base-input"] {{
        background-color: {LIGHT_GRAY} !important;
        border-radius: 8px !important;
    }}

    /* Select */
    [data-baseweb="select"] > div {{
        background-color: {LIGHT_GRAY} !important;
        border: 1px solid {BORDER_GRAY} !important;
        border-radius: 8px !important;
        min-height: 38px !important;
    }}
    [data-baseweb="select"] > div:hover {{
        border-color: #B0B0B0 !important;
    }}
    [data-baseweb="select"] > div:focus-within {{
        border-color: {PRIMARY_BLUE} !important;
        box-shadow: 0 0 0 2px rgba(18,55,91,0.15) !important;
    }}
    [data-baseweb="select"] input {{
        opacity: 0 !important;
        width: 0 !important;
        height: 0 !important;
        padding: 0 !important;
        margin: 0 !important;
        border: none !important;
        position: absolute !important;
        pointer-events: none !important;
    }}
    [data-baseweb="select"] [data-baseweb="input"] {{
        border: none !important;
        background: transparent !important;
    }}
    [data-baseweb="select"] span,
    [data-baseweb="select"] div {{
        color: {DARK_GRAY} !important;
        -webkit-text-fill-color: {DARK_GRAY} !important;
    }}
    [data-baseweb="select"] svg {{
        fill: #666666 !important;
    }}

    #/* Radio */
    #.stRadio label,
    #.stRadio [role="radiogroup"] label,
    #[data-testid="stRadio"] label {{
    #    color: {DARK_GRAY} !important;
    #    font-size: 14px !important;
    #}}
    #[data-baseweb="radio"] > div:first-child {{
    #    width: 18px !important;
    #    height: 18px !important;
    #    border: 2px solid #B0B0B0 !important;
    #    border-radius: 50% !important;
    #    background-color: #FFFFFF !important;
    #}}
    #[data-baseweb="radio"] > div:first-child > div {{
    #    background-color: transparent !important;
    #    width: 0px !important;
    #    height: 0px !important;
    #    border-radius: 50% !important;
    #    transition: all 0.2s ease !important;
    #}}
    #[data-baseweb="radio"]:hover > div:first-child {{
    #    border-color: {PRIMARY_BLUE} !important;
    #}}
    #[data-baseweb="radio"][data-checked="true"] > div:first-child > div {{
    #    background-color: {PRIMARY_BLUE} !important;
    #    width: 10px !important;
    #    height: 10px !important;
    #}}
    #[data-baseweb="radio"][data-checked="true"] > div:first-child {{
    #    border-color: {PRIMARY_BLUE} !important;
    #}}

    /* Botões gerais: azul claro, fonte branca */
    .stButton > button,
    [data-testid="stFormSubmitButton"] > button {{
        background-color: {BUTTON_BLUE} !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 8px 20px !important;
        font-weight: 600 !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.15) !important;
    }}
    .stButton > button:hover,
    [data-testid="stFormSubmitButton"] > button:hover {{
        background-color: {BUTTON_BLUE_HOVER} !important;
        box-shadow: 0 4px 10px rgba(0,0,0,0.2) !important;
        transform: translateY(-1px) !important;
    }}

    /* Botões de download */
    .stDownloadButton > button {{
        background-color: {BUTTON_BLUE} !important;
        color: #FFFFFF !important;
        border-radius: 8px !important;
        border: none !important;
        padding: 8px 20px !important;
        font-weight: 600 !important;
    }}
    .stDownloadButton > button:hover {{
        background-color: {BUTTON_BLUE_HOVER} !important;
    }}

    /* Form card */
    [data-testid="stForm"] {{
        background-color: #FFFFFF !important;
        border: 1px solid #E0E0E0 !important;
        border-radius: 12px !important;
        padding: 20px !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05) !important;
    }}

    /* Expander */
    [data-testid="stExpander"],
    details {{
        background-color: #FFFFFF !important;
        border: 1px solid #E0E0E0 !important;
        border-radius: 8px !important;
    }}

    [data-testid="stExpander"] summary,
    details summary {{
        color: {DARK_GRAY} !important;
        font-weight: 500 !important;
    }}

    /* Tabelas */
    .stDataFrame,
    [data-testid="stDataFrame"],
    table {{
        background-color: #FFFFFF !important;
        border-radius: 8px !important;
        overflow: hidden !important;
    }}
    th {{
        background-color: #F0F0F0 !important;
        color: {DARK_GRAY} !important;
        font-weight: 600 !important;
    }}
    td {{
        background-color: #FFFFFF !important;
        color: {DARK_GRAY} !important;
    }}

    [data-testid="stWidgetLabel"],
    [data-testid="stWidgetLabel"] p {{
        color: #555555 !important;
        font-weight: 500 !important;
        font-size: 14px !important;
    }}

    hr {{
        border-color: #E0E0E0 !important;
    }}

    .stTextArea textarea {{
        min-height: 80px !important;
    }}
    </style>
    """,
    unsafe_allow_html=True
)

if not OPENAI_ENABLED:
    st.warning("Sem conexão com a IA. Os textos automáticos exibirão a mensagem 'Sem conexão com a IA'.")

# =========================================================
# ESCALA 5 NÍVEIS
# =========================================================
LIKERT_OPCOES = {
    1: "1 - Ainda não demonstra",
    2: "2 - Demonstra com muito apoio",
    3: "3 - Em desenvolvimento",
    4: "4 - Quase consolidado",
    5: "5 - Consolidado",
}

LIKERT_LABELS = {
    1: "Ainda não demonstra",
    2: "Demonstra com muito apoio",
    3: "Em desenvolvimento",
    4: "Quase consolidado",
    5: "Consolidado",
}

# =========================================================
# FUNÇÕES DE CÁLCULO / GRÁFICO
# =========================================================
def calcular_scores(respostas_dict):
    df = pd.DataFrame(respostas_dict.values())
    df["resposta_util"] = df["resposta"].replace(0, np.nan)
    dominio_media = (
        df.groupby(["dominio", "dominio_nome"])["resposta_util"]
        .mean()
        .reset_index()
        .rename(columns={"resposta_util": "media_dominio"})
    )
    media_geral = df["resposta_util"].mean()
    return df, dominio_media, media_geral


def plot_radar(dominio_media):
    dominio_media = dominio_media.dropna(subset=["media_dominio"])
    if dominio_media.empty:
        fig, ax = plt.subplots(figsize=(5, 3))
        ax.axis("off")
        ax.text(0.5, 0.5, "Sem dados suficientes\npara o gráfico de radar.", ha="center", va="center")
        return fig

    labels = []
    valores = []
    for _, row in dominio_media.iterrows():
        labels.append(row["dominio_nome"])
        valores.append(row["media_dominio"])

    num_vars = len(labels)
    angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
    valores += valores[:1]
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))
    ax.plot(angles, valores, linewidth=2, linestyle="solid")
    ax.fill(angles, valores, alpha=0.25)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_yticks([1, 2, 3, 4, 5])
    ax.set_yticklabels(["1", "2", "3", "4", "5"], fontsize=8)
    ax.set_ylim(1, 5)
    ax.set_title("Perfil por dimensão (escala interna 1–5)", fontsize=12, pad=20)
    return fig


def get_logo_base64():
    if os.path.exists(LOGO_PATH):
        try:
            with open(LOGO_PATH, "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8")
        except Exception:
            return None
    return None


def texto_sem_ia():
    return "Sem conexão com a IA."


# =========================================================
# IA – RELATÓRIO, SUGESTÕES, PLANO TURMA
# =========================================================
def gerar_relatorio_ia(
    sexo,
    dominio_media,
    media_geral,
    ano_escolar,
    boletim_texto,
    neuroatipico,
    pei_resumo,
    observacoes_gerais,
):
    if not OPENAI_ENABLED:
        return texto_sem_ia()

    dominio_media_valid = dominio_media.dropna(subset=["media_dominio"])
    resumo_dim = []
    nomes_dim = []
    for _, row in dominio_media_valid.iterrows():
        resumo_dim.append(f"- {row['dominio_nome']}: valor médio interno {row['media_dominio']:.2f}")
        nomes_dim.append(f"- {row['dominio_nome']}")
    resumo_dim_str = "\n".join(resumo_dim)
    nomes_dim_str = "\n".join(nomes_dim)

    boletim_info = boletim_texto if boletim_texto else "sem resumo específico informado."
    neuro_txt = (
        "Aluno com necessidades educacionais específicas, com informações complementares registradas em um plano individual."
        if neuroatipico
        else "Aluno sem registro de plano individual específico."
    )
    pei_info = pei_resumo if pei_resumo else "sem registro complementar do plano educacional individualizado."
    obs_info = observacoes_gerais if observacoes_gerais else "sem registro adicional da professora."

    prompt_user = f"""
Você é pedagogo especialista em educação básica.

Escreva um RELATÓRIO DESCRITIVO e INTERPRETATIVO, em português do Brasil,
sobre o desenvolvimento de um estudante, com base em observações organizadas por dimensões,
em informações de boletim escolar (quando disponíveis) e em registros de um plano educacional individualizado (quando houver).

Dados contextuais:
- Etapa / ano escolar: {ano_escolar or "não informado"}
- Sexo declarado: {sexo or "não informado"}
- Situação quanto a necessidades específicas: {neuro_txt}
- Resumo do boletim escolar (quando informado): {boletim_info}
- Informações relevantes do plano educacional individualizado (PEI): {pei_info}
- Observações gerais da professora sobre o estudante: {obs_info}

Valores internos por dimensão (escala 1 a 5, uso apenas como referência técnica):
{resumo_dim_str}

Lista das dimensões (use exatamente esses nomes na interpretação):
{nomes_dim_str}

Regras:
- Escreva texto corrido, em parágrafos, sem títulos formais, voltado a famílias e escola.
- NÃO mencione números, notas, médias ou a expressão "escala".
- Não use termos clínicos (TDAH, TEA etc.).
- Use termos como "a criança", "o estudante", "o aluno".
- Linguagem positiva: fale em avanços, habilidades em desenvolvimento, processos de consolidação,
  evitando frases negativas diretas.
- Considere que o boletim, o PEI e as observações gerais são fontes complementares às observações de sala.
- Se o aluno tem necessidades específicas, faça pelo menos um parágrafo reforçando a importância
  do olhar individual e das adaptações, sem citar siglas ou diagnósticos.

Estrutura:
1. Parágrafo inicial: visão geral do desenvolvimento.
2. Parágrafo(s) de pontos fortes.
3. Parágrafo(s) de habilidades em desenvolvimento.
4. Pelo menos um parágrafo para cada dimensão listada.
5. Parágrafos finais sobre parceria família-escola e próximos passos.
"""

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Você é pedagogo especialista em educação básica, escreve relatórios "
                        "descritivos em linguagem acessível, positiva e profissional."
                    ),
                },
                {"role": "user", "content": prompt_user},
            ],
            temperature=0.65,
            max_tokens=1200,
        )
        return resp.choices[0].message.content.strip()
    except Exception:
        return texto_sem_ia()


def gerar_sugestoes_ia(dominio_media, ano_escolar, neuroatipico, boletim_texto, pei_resumo, observacoes_gerais):
    if not OPENAI_ENABLED:
        return texto_sem_ia()

    dominio_media_valid = dominio_media.dropna(subset=["media_dominio"])
    resumo_dim = []
    nomes_dim = []
    for _, row in dominio_media_valid.iterrows():
        resumo_dim.append(f"- {row['dominio_nome']}: média interna {row['media_dominio']:.2f}")
        nomes_dim.append(f"- {row['dominio_nome']}")
    resumo_dim_str = "\n".join(resumo_dim)
    nomes_dim_str = "\n".join(nomes_dim)

    foco_texto = (
        "plano de estudo complementar para o estudante"
        if ano_tem_boletim(ano_escolar or "")
        else "sugestões de atividades em casa"
    )
    neuro_txt = (
        "Considere que a criança se beneficia de adaptações simples, como tempos diferenciados, apoio visual e instruções em etapas."
        if neuroatipico
        else "Considere que as orientações devem ser gerais, acolhedoras e realistas para famílias diversas."
    )
    boletim_info = boletim_texto if boletim_texto else "sem resumo específico informado."
    pei_info = pei_resumo if pei_resumo else "sem registro complementar do plano educacional individualizado."
    obs_info = observacoes_gerais if observacoes_gerais else "sem registro adicional da professora."

    prompt_user = f"""
Você é pedagogo e vai elaborar um {foco_texto} para famílias.

Médias internas por dimensão (escala técnica 1 a 5, apenas referência):
{resumo_dim_str}

Lista das dimensões:
{nomes_dim_str}

Informações adicionais:
- Resumo do boletim escolar: {boletim_info}
- Principais pontos do PEI (quando houver): {pei_info}
- Observações gerais da professora: {obs_info}
- Orientação geral: {neuro_txt}

Instruções:
- Escreva em português, linguagem simples e acolhedora, voltada a famílias.
- NÃO cite números, notas, médias ou a expressão "escala".
- Não faça diagnóstico clínico.
- Use comunicação positiva, com foco em como a família pode apoiar o estudante.
- Para educação infantil e anos iniciais, foque em brincadeiras, rotinas, leitura, conversas.
- Para anos finais do fundamental e médio, foque em hábitos de estudo, leitura, organização
  e atividades práticas ligadas às áreas de conhecimento.
- Para CADA dimensão, faça pelo menos um parágrafo iniciando pelo nome da dimensão.
"""

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Você gera orientações para famílias sobre como apoiar estudantes em casa, "
                        "sempre com comunicação positiva."
                    ),
                },
                {"role": "user", "content": prompt_user},
            ],
            temperature=0.7,
            max_tokens=1200,
        )
        return resp.choices[0].message.content.strip()
    except Exception:
        return texto_sem_ia()


def gerar_plano_turma_ia(dominio_media_turma, contexto_str=""):
    if not OPENAI_ENABLED:
        return texto_sem_ia()

    dominio_media_valid = dominio_media_turma.dropna(subset=["media_dominio"])
    resumo_dim = []
    nomes_dim = []
    for _, row in dominio_media_valid.iterrows():
        resumo_dim.append(f"- {row['dominio_nome']}: média interna {row['media_dominio']:.2f}")
        nomes_dim.append(f"- {row['dominio_nome']}")
    resumo_dim_str = "\n".join(resumo_dim)
    nomes_dim_str = "\n".join(nomes_dim)

    prompt_user = f"""
Você é pedagogo especialista em planejamento de turma.

Elabore um PLANO DE DESENVOLVIMENTO GLOBAL DA TURMA, em português,
com linguagem voltada à equipe escolar.

Contexto da turma:
{contexto_str}

Médias internas por dimensão (referência técnica, escala 1 a 5):
{resumo_dim_str}

Dimensões avaliadas:
{nomes_dim_str}

Regras:
- Texto em parágrafos, sem bullets.
- Não citar notas ou médias, nem a expressão "escala".
- Comunicação positiva, desafios como "habilidades em desenvolvimento".
- Explique o foco de cada dimensão e sugira estratégias concretas de trabalho com a turma.
- Em cada dimensão, inclua um trecho com "Exemplos práticos: ..." em frases corridas.

Estrutura:
1. Parágrafos iniciais com síntese e "Objetivo geral:".
2. Bloco por dimensão.
3. Parágrafos finais com recomendações de rotina e parceria com famílias.
"""

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Você elabora planos pedagógicos para turmas, com foco em desenvolvimento global."
                    ),
                },
                {"role": "user", "content": prompt_user},
            ],
            temperature=0.7,
            max_tokens=1400,
        )
        return resp.choices[0].message.content.strip()
    except Exception:
        return texto_sem_ia()


# =========================================================
# BANCO DE DADOS
# =========================================================
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS alunos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        escola TEXT,
        turno TEXT,
        ano_escolar TEXT,
        turma TEXT,
        ano_letivo TEXT,
        bimestre TEXT,
        nome_crianca TEXT,
        idade TEXT,
        sexo TEXT,
        nome_professora TEXT,
        neuroatipico INTEGER,
        boletim_texto TEXT,
        media_geral REAL,
        relatorio_texto TEXT,
        sugestoes_texto TEXT,
        observacoes_gerais TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS respostas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        aluno_id INTEGER,
        dominio TEXT,
        dominio_nome TEXT,
        item_codigo TEXT,
        item_texto TEXT,
        resposta INTEGER,
        observacao TEXT,
        FOREIGN KEY(aluno_id) REFERENCES alunos(id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS dominios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        aluno_id INTEGER,
        dominio TEXT,
        dominio_nome TEXT,
        media_dominio REAL,
        FOREIGN KEY(aluno_id) REFERENCES alunos(id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS pei (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        escola TEXT,
        nome_crianca TEXT,
        ano_escolar TEXT,
        ano_letivo TEXT,
        perfil TEXT,
        pontos_fortes TEXT,
        habilidades_desenvolvimento TEXT,
        recursos_apoio TEXT,
        estrategias_metodologicas TEXT,
        adaptacoes_avaliacao TEXT,
        participacao_familia TEXT
    )
    """)

    conn.commit()
    conn.close()


def salvar_no_banco(
    timestamp_str,
    escola,
    turno,
    ano_escolar,
    turma,
    ano_letivo,
    bimestre,
    nome_crianca,
    sexo,
    nome_professora,
    neuroatipico,
    boletim_texto,
    media_geral,
    relatorio_texto,
    sugestoes_texto,
    observacoes_gerais,
    df_itens,
    dominio_media,
):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO alunos (
            timestamp, escola, turno, ano_escolar, turma, ano_letivo, bimestre,
            nome_crianca, idade, sexo, nome_professora, neuroatipico,
            boletim_texto, media_geral, relatorio_texto, sugestoes_texto,
            observacoes_gerais
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            timestamp_str,
            escola,
            turno,
            ano_escolar,
            turma,
            ano_letivo,
            bimestre,
            nome_crianca,
            "",
            sexo,
            nome_professora,
            1 if neuroatipico else 0,
            boletim_texto,
            float(media_geral) if not pd.isna(media_geral) else None,
            relatorio_texto,
            sugestoes_texto,
            observacoes_gerais,
        ),
    )
    aluno_id = cur.lastrowid

    for _, row in df_itens.iterrows():
        cur.execute(
            """
            INSERT INTO respostas (aluno_id, dominio, dominio_nome, item_codigo, item_texto, resposta, observacao)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                aluno_id,
                row["dominio"],
                row["dominio_nome"],
                row["item_codigo"],
                row["item_texto"],
                int(row["resposta"]),
                None,
            ),
        )

    for _, row in dominio_media.iterrows():
        cur.execute(
            """
            INSERT INTO dominios (aluno_id, dominio, dominio_nome, media_dominio)
            VALUES (?, ?, ?, ?)
            """,
            (
                aluno_id,
                row["dominio"],
                row["dominio_nome"],
                float(row["media_dominio"]) if not pd.isna(row["media_dominio"]) else None,
            ),
        )

    conn.commit()
    conn.close()
    return aluno_id


def salvar_pei(
    escola,
    nome_crianca,
    ano_escolar,
    ano_letivo,
    perfil,
    pontos_fortes,
    habilidades_desenvolvimento,
    recursos_apoio,
    estrategias_metodologicas,
    adaptacoes_avaliacao,
    participacao_familia,
):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    cur.execute(
        """
        INSERT INTO pei (
            timestamp, escola, nome_crianca, ano_escolar, ano_letivo,
            perfil, pontos_fortes, habilidades_desenvolvimento,
            recursos_apoio, estrategias_metodologicas,
            adaptacoes_avaliacao, participacao_familia
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            ts,
            escola,
            nome_crianca,
            ano_escolar,
            ano_letivo,
            perfil,
            pontos_fortes,
            habilidades_desenvolvimento,
            recursos_apoio,
            estrategias_metodologicas,
            adaptacoes_avaliacao,
            participacao_familia,
        ),
    )
    conn.commit()
    conn.close()


def carregar_pei_resumo(escola, nome_crianca):
    if not os.path.exists(DB_PATH):
        return ""
    conn = sqlite3.connect(DB_PATH)
    df_pei = pd.read_sql_query(
        """
        SELECT * FROM pei
        WHERE escola = ? AND nome_crianca = ?
        ORDER BY timestamp DESC
        """,
        conn,
        params=(escola, nome_crianca),
    )
    conn.close()
    if df_pei.empty:
        return ""
    row = df_pei.iloc[0]
    textos = []
    if row["perfil"]:
        textos.append(f"Perfil do estudante: {row['perfil']}")
    if row["pontos_fortes"]:
        textos.append(f"Pontos fortes: {row['pontos_fortes']}")
    if row["habilidades_desenvolvimento"]:
        textos.append(f"Habilidades em desenvolvimento: {row['habilidades_desenvolvimento']}")
    if row["recursos_apoio"]:
        textos.append(f"Recursos e apoios: {row['recursos_apoio']}")
    if row["estrategias_metodologicas"]:
        textos.append(f"Estratégias metodológicas: {row['estrategias_metodologicas']}")
    if row["adaptacoes_avaliacao"]:
        textos.append(f"Adaptações para avaliação: {row['adaptacoes_avaliacao']}")
    if row["participacao_familia"]:
        textos.append(f"Participação da família: {row['participacao_familia']}")
    return " ".join(textos)


def montar_historico_aluno(escola, nome_crianca):
    if not os.path.exists(DB_PATH):
        return ""
    conn = sqlite3.connect(DB_PATH)
    df_hist = pd.read_sql_query(
        """
        SELECT timestamp, ano_escolar, ano_letivo, bimestre
        FROM alunos
        WHERE escola = ? AND nome_crianca = ?
        ORDER BY timestamp ASC
        """,
        conn,
        params=(escola, nome_crianca),
    )
    conn.close()
    if df_hist.shape[0] <= 1:
        return ""
    linhas = []
    for _, row in df_hist.iterrows():
        linhas.append(
            f"{row['bimestre'] or ''} - {row['ano_escolar'] or ''} {row['ano_letivo'] or ''} "
            f"(registro em {row['timestamp']})"
        )
    return "<br>".join(linhas)


# =========================================================
# HTML – RELATÓRIO INDIVIDUAL E CONSOLIDADO
# =========================================================
def gerar_html_impressao(
    escola,
    turno,
    ano_escolar,
    turma,
    ano_letivo,
    bimestre,
    crianca,
    professora,
    sexo,
    boletim_texto,
    df_itens,
    dominio_media,
    media_geral,
    relatorio,
    sugestoes,
    radar_b64,
    historico_html,
    pei_resumo_html,
    observacoes_gerais,
):
    df_tmp = df_itens[["dominio_nome", "item_texto", "resposta"]].copy()

    def resp_str(v):
        try:
            v = int(v)
        except Exception:
            return ""
        if v in LIKERT_LABELS:
            return LIKERT_LABELS[v]
        if v == 0:
            return "Não respondido"
        return ""

    df_tmp["Escala descritiva"] = df_tmp["resposta"].apply(resp_str)

    tabela_html = df_tmp[[
        "dominio_nome",
        "item_texto",
        "Escala descritiva",
    ]].rename(columns={
        "dominio_nome": "Dimensão",
        "item_texto": "Descrição",
    }).to_html(index=False, border=0, justify="left")

    relatorio_html = "<br>".join(textwrap.fill(l, 100) for l in relatorio.split("\n"))
    sugestoes_html = "<br>".join(textwrap.fill(l, 100) for l in sugestoes.split("\n"))

    sexo_str = sexo if sexo else "não informado"

    logo_b64 = get_logo_base64()
    logo_tag = f'<img src="data:image/png;base64,{logo_b64}" class="logo" />' if logo_b64 else ""
    radar_tag = f'<img src="data:image/png;base64,{radar_b64}" alt="Radar da criança" />' if radar_b64 else ""

    historico_block = ""
    if historico_html:
        historico_block = f"""
        <h2>Histórico de avaliações</h2>
        <p>Registros anteriores deste estudante na plataforma:</p>
        <p>{historico_html}</p>
        """

    pei_block = ""
    if pei_resumo_html:
        pei_block = f"""
        <h2>Informações do Plano Educacional Individualizado (PEI)</h2>
        <p>{pei_resumo_html}</p>
        """

    obs_block = ""
    if observacoes_gerais:
        obs_texto = textwrap.fill(observacoes_gerais, 100)
        obs_texto_html = obs_texto.replace("\n", "<br>")
        obs_block = f"""
        <h2>Observações da professora</h2>
        <p>{obs_texto_html}</p>
        """

    # -------- AJUSTE 2: boletim como TABELA --------
    boletim_block = ""
    if boletim_texto:
        linhas = [l.strip() for l in boletim_texto.split("\n") if l.strip()]
        if linhas:
            rows_html = []
            for linha in linhas:
                partes = [p.strip() for p in linha.split("|")]
                disc_val = ""
                nota_val = ""
                conteudo_val = ""
                for ptxt in partes:
                    if ptxt.startswith("Disciplina:"):
                        disc_val = ptxt.split("Disciplina:", 1)[1].strip()
                    elif ptxt.startswith("Nota:"):
                        nota_val = ptxt.split("Nota:", 1)[1].strip()
                    elif ptxt.startswith("Conteúdo:"):
                        conteudo_val = ptxt.split("Conteúdo:", 1)[1].strip()
                rows_html.append(
                    f"<tr><td>{disc_val}</td><td>{nota_val}</td><td>{conteudo_val}</td></tr>"
                )
            boletim_tabela_html = (
                "<table>"
                "<thead><tr><th>Disciplina</th><th>Nota</th><th>Conteúdo programático</th></tr></thead>"
                "<tbody>"
                + "\n".join(rows_html)
                + "</tbody></table>"
            )
            boletim_block = f"""
            <h2>Boletim escolar / desempenho formal</h2>
            {boletim_tabela_html}
            """

    html = f"""
    <html>
    <head>
        <meta charset="utf-8">
        <title>Relatório - {crianca}</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 20px;
                color: {DARK_GRAY};
            }}
            h1, h2, h3 {{
                color: {PRIMARY_BLUE};
            }}
            table {{
                border-collapse: collapse;
                width: 100%;
                margin-bottom: 20px;
            }}
            th, td {{
                border: 1px solid #ccc;
                padding: 6px;
                font-size: 12px;
                text-align: left;
            }}
            .logo {{
                position: absolute;
                top: 20px;
                right: 20px;
                height: 80px;
            }}
        </style>
    </head>
    <body>
        {logo_tag}
        <h1>Relatório de desenvolvimento</h1>

        <h2>Dados do estudante</h2>
        <p><b>Escola:</b> {escola}</p>
        <p><b>Turno:</b> {turno}</p>
        <p><b>Ano escolar:</b> {ano_escolar}</p>
        <p><b>Turma:</b> {turma}</p>
        <p><b>Ano letivo:</b> {ano_letivo}</p>
        <p><b>Bimestre:</b> {bimestre}</p>
        <p><b>Nome do estudante:</b> {crianca}</p>
        <p><b>Sexo:</b> {sexo_str}</p>
        <p><b>Professora responsável:</b> {professora}</p>

        {pei_block}
        {boletim_block}

        <h3>Perfil por dimensão (uso interno da escola)</h3>
        {radar_tag}

        <h3>Respostas por item (escala descritiva)</h3>
        {tabela_html}

        <h2>Relatório individual</h2>
        <p>{relatorio_html}</p>

        <h2>Plano de estudo complementar / orientações para a família</h2>
        <p>{sugestoes_html}</p>
    </body>
    </html>
    """
    return html


def gerar_html_relatorio_professora(
    nome_professora,
    escola,
    turno,
    turma,
    ano_letivo,
    n_alunos,
    media_geral_prof,
    dominio_media_prof,
    plano_prof,
    radar_b64
):
    dominios_html = dominio_media_prof.to_html(index=False, border=0, justify="left")
    plano_html = "<br>".join(textwrap.fill(l, 100) for l in plano_prof.split("\n"))

    logo_b64 = get_logo_base64()
    logo_tag = f'<img src="data:image/png;base64,{logo_b64}" class="logo" />' if logo_b64 else ""

    html = f"""
    <html>
    <head>
        <meta charset="utf-8">
        <title>Relatório - Professora {nome_professora}</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 20px;
                color: {DARK_GRAY};
            }}
            h1, h2, h3 {{
                color: {PRIMARY_BLUE};
            }}
            table {{
                border-collapse: collapse;
                width: 100%;
                margin-bottom: 20px;
            }}
            th, td {{
                border: 1px solid #ccc;
                padding: 6px;
                font-size: 12px;
                text-align: left;
            }}
            .logo {{
                position: absolute;
                top: 20px;
                right: 20px;
                height: 80px;
            }}
        </style>
    </head>
    <body>
        {logo_tag}
        <h1>Relatório consolidado da turma</h1>

        <h2>Dados gerais</h2>
        <p><b>Escola:</b> {escola or ""}</p>
        <p><b>Turno:</b> {turno or ""}</p>
        <p><b>Turma:</b> {turma or "Não especificada"}</p>
        <p><b>Ano letivo:</b> {ano_letivo or ""}</p>
        <p><b>Professora:</b> {nome_professora}</p>
        <p><b>Número de estudantes avaliados:</b> {n_alunos}</p>
        <p><b>Média geral (escala interna 1–5):</b> {media_geral_prof:.2f}</p>

        <h2>Médias por dimensão</h2>
        {dominios_html}

        <h2>Perfil por dimensão (gráfico de radar)</h2>
        <img src="data:image/png;base64,{radar_b64}" alt="Radar da turma" />

        <h2>Plano de desenvolvimento da turma</h2>
        <p>{plano_html}</p>
    </body>
    </html>
    """
    return html


# =========================================================
# ESTADO STREAMLIT
# =========================================================
if "resultado" not in st.session_state:
    st.session_state["resultado"] = None

if "edit_id" not in st.session_state:
    st.session_state["edit_id"] = None

if "reprint_id" not in st.session_state:
    st.session_state["reprint_id"] = None

if "aluno_cadastrado" not in st.session_state:
    st.session_state["aluno_cadastrado"] = False

if "boletim_df" not in st.session_state:
    st.session_state["boletim_df"] = None
    st.session_state["ano_escolar_boletim"] = None
    st.session_state["nome_crianca_boletim"] = None

if "edit_loaded" not in st.session_state:
    st.session_state["edit_loaded"] = False

if "nome_social" not in st.session_state:
    st.session_state["nome_social"] = ""

def resetar_avaliacao():
    st.session_state["escola"] = ""
    st.session_state["turno"] = ""
    st.session_state["ano_escolar"] = ""
    st.session_state["turma_crianca"] = ""
    st.session_state["ano_letivo"] = ""
    st.session_state["nome_crianca"] = ""
    st.session_state["sexo_crianca"] = ""
    st.session_state["nome_professora"] = ""
    st.session_state["bimestre"] = ""
    st.session_state["neuroatipico"] = False    
    st.session_state["boletim_texto"] = ""
    st.session_state["observacoes_gerais"] = ""
    st.session_state["aluno_cadastrado"] = False
    st.session_state["resultado"] = None
    st.session_state["boletim_df"] = None
    st.session_state["ano_escolar_boletim"] = None
    st.session_state["nome_crianca_boletim"] = None
    st.session_state["edit_id"] = None
    st.session_state["edit_loaded"] = False


def carregar_avaliacao_para_form(aluno_id):
    if not os.path.exists(DB_PATH):
        return
    conn = sqlite3.connect(DB_PATH)
    df_alunos = pd.read_sql_query("SELECT * FROM alunos WHERE id = ?", conn, params=(aluno_id,))
    df_resp = pd.read_sql_query(
        "SELECT dominio, dominio_nome, item_codigo, item_texto, resposta, observacao FROM respostas WHERE aluno_id = ?",
        conn,
        params=(aluno_id,),
    )
    conn.close()
    if df_alunos.empty:
        return
    row = df_alunos.iloc[0]

    st.session_state["escola"] = row["escola"] or ""
    st.session_state["turno"] = row["turno"] or ""
    st.session_state["ano_escolar"] = row["ano_escolar"] or ANOS_ESCOLARES[0]
    st.session_state["turma_crianca"] = row["turma"] or ""
    st.session_state["ano_letivo"] = row["ano_letivo"] or ""
    st.session_state["nome_crianca"] = row["nome_crianca"] or ""
    st.session_state["nome_social"] = st.session_state.get("nome_social", "")
    st.session_state["sexo_crianca"] = row["sexo"] or ""
    st.session_state["nome_professora"] = row["nome_professora"] or ""
    st.session_state["bimestre"] = row["bimestre"] or ""
    st.session_state["neuroatipico"] = bool(row["neuroatipico"])
    st.session_state["boletim_texto"] = row["boletim_texto"] or ""
    st.session_state["observacoes_gerais"] = row.get("observacoes_gerais", "") or ""

    # Carrega as respostas numéricas (1–5) nos widgets de escala
    for _, r in df_resp.iterrows():
        dom_code = r["dominio"]
        item_code = r["item_codigo"]
        valor = r["resposta"]
        key = f"{dom_code}_{item_code}"

        try:
            valor_int = int(valor)
        except Exception:
            valor_int = None

        if valor_int in LIKERT_OPCOES:
            st.session_state[key] = valor_int
        else:
            # fallback: valor central da escala
            st.session_state[key] = 3

    st.session_state["aluno_cadastrado"] = True
    st.session_state["resultado"] = None


# =========================================================
# LAYOUT – TABS
# =========================================================
tab_avaliar, tab_consulta, tab_pei = st.tabs(
    ["Nova avaliação", "Consultas / Relatórios", "PEI – Plano Individual"]
)
# Se houver uma avaliação marcada para edição, carrega antes de desenhar os widgets
if st.session_state.get("edit_id") is not None and not st.session_state.get("edit_loaded", False):
    carregar_avaliacao_para_form(st.session_state["edit_id"])
    st.session_state["edit_loaded"] = True

# ---------------------------------------------------------
# ABA 1 – NOVA AVALIAÇÃO
# ---------------------------------------------------------
with tab_avaliar:
    col_title, col_logo = st.columns([5, 1])
    with col_title:
        st.markdown(
            '<div class="ade-title">Plataforma ADE – Avaliação e Desenvolvimento Educacional</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="ade-subtitle">Instrumento digital para registro pedagógico, relatórios descritivos e acompanhamento do desenvolvimento dos estudantes.</div>',
            unsafe_allow_html=True,
        )
    with col_logo:
        if os.path.exists(LOGO_PATH):
            st.image(LOGO_PATH, width=120)
        else:
            st.caption("Logo da escola pode ser inserida aqui.")

    st.write("---")

    st.markdown("### Ações rápidas")
    col_ar1, col_ar2 = st.columns(2)
    with col_ar1:
        if st.button("Iniciar nova avaliação"):
            resetar_avaliacao()
    with col_ar2:
        if os.path.exists(DB_PATH):
            conn = sqlite3.connect(DB_PATH)
            df_alunos_all = pd.read_sql_query(
                "SELECT id, escola, nome_crianca, ano_escolar, turma, timestamp FROM alunos ORDER BY timestamp DESC",
                conn,
            )
            conn.close()
            if not df_alunos_all.empty:
                opcoes = ["(Selecionar avaliação para carregar)"]
                mapa = {}
                for _, row in df_alunos_all.iterrows():
                    label = f"{row['id']} – {row['nome_crianca']} – {row['escola']} – {row['ano_escolar']} – {row['turma']} ({row['timestamp']})"
                    opcoes.append(label)
                    mapa[label] = int(row["id"])
                escolha = st.selectbox("Continuar avaliação já registrada:", opcoes)
                if escolha != "(Selecionar avaliação para carregar)":
                    if st.button("Carregar avaliação selecionada"):
                        carregar_avaliacao_para_form(mapa[escolha])
                        st.success("Avaliação carregada no formulário.")
            else:
                st.caption("Nenhuma avaliação registrada ainda para carregamento.")
        else:
            st.caption("Nenhuma avaliação registrada ainda para carregamento.")

    st.write("---")

    st.markdown("### Cadastro do estudante")

    with st.form("form_cadastro_aluno"):
        colc1, colc2 = st.columns(2)
        with colc1:
            escola = st.text_input("Nome da escola", key="escola")
            turno = st.selectbox(
                "Turno",
                ["", "Matutino", "Vespertino", "Noturno", "Integral"],
                key="turno",
            )
            ano_escolar = st.selectbox(
                "Ano escolar",
                ANOS_ESCOLARES,
                key="ano_escolar",
            )
        with colc2:
            turma = st.text_input("Turma", key="turma_crianca")
            ano_letivo = st.text_input("Ano letivo (ex.: 2025)", key="ano_letivo")
            bimestre = st.selectbox(
                "Bimestre de avaliação",
                ["", "1º bimestre", "2º bimestre", "3º bimestre", "4º bimestre"],
                key="bimestre",
            )

        colc3, colc4 = st.columns(2)
        with colc3:
            nome_crianca = st.text_input("Nome do aluno", key="nome_crianca")
            nome_social = st.text_input("Nome social (opcional)", key="nome_social")
        with colc4:
            sexo = st.selectbox(
                "Sexo do aluno",
                ["", "Masculino", "Feminino", "Outro", "Prefere não informar"],
                key="sexo_crianca",
            )
            nome_professora = st.text_input(
                "Nome da professora/professor",
                key="nome_professora",
            )

        neuroatipico = st.checkbox(
            "Aluno neuroatípico (necessidades educacionais específicas)",
            key="neuroatipico",
        )

        cadastrar = st.form_submit_button("Cadastrar estudante")

    if cadastrar:
        if not escola or not nome_crianca or not nome_professora:
            st.error("Preencha pelo menos: escola, nome do aluno e nome da professora/professor.")
        else:
            st.session_state["aluno_cadastrado"] = True
            st.success("Estudante cadastrado. O instrumento de avaliação será exibido abaixo.")

    # -------- APENAS MOSTRAR QUESTIONÁRIO APÓS CADASTRO --------
    if st.session_state.get("aluno_cadastrado"):
        escola = st.session_state.get("escola", "")
        nome_crianca = st.session_state.get("nome_crianca", "")
        ano_escolar = st.session_state.get("ano_escolar", "")
        neuro_flag = st.session_state.get("neuroatipico", False)

        mostrar_avaliacao = True

        # Se for neuroatípico, exige PEI preenchido antes
        if neuro_flag:
            pei_resumo_check = carregar_pei_resumo(escola, nome_crianca)
            if not pei_resumo_check:
                st.warning(
                    "Para alunos neuroatípicos, é obrigatório preencher o PEI antes do boletim e da escala "
                    "de desenvolvimento. Vá na aba 'PEI – Plano Individual', registre o plano e depois retorne "
                    "para continuar a avaliação."
                )
                mostrar_avaliacao = False

        if mostrar_avaliacao:
            st.write("---")

            st.markdown("### Boletim escolar / desempenho formal")
            if ano_tem_boletim(ano_escolar):
                disciplinas_base = get_disciplinas_boletim_mec(ano_escolar)

                # Inicializa ou reaproveita tabela do boletim
                precisa_novo_df = (
                    st.session_state.get("boletim_df") is None
                    or st.session_state.get("ano_escolar_boletim") != ano_escolar
                    or st.session_state.get("nome_crianca_boletim") != nome_crianca
                )

                if precisa_novo_df:
                    boletim_df = pd.DataFrame({
                        "Disciplina": disciplinas_base,
                        "Nota": ["" for _ in disciplinas_base],
                        "Conteúdo programático": ["" for _ in disciplinas_base],
                    })
                    st.session_state["boletim_df"] = boletim_df
                    st.session_state["ano_escolar_boletim"] = ano_escolar
                    st.session_state["nome_crianca_boletim"] = nome_crianca
                else:
                    boletim_df = st.session_state["boletim_df"]

                st.caption("Preencha a nota e o conteúdo programático trabalhado em cada disciplina.")
                boletim_editado = st.data_editor(
                    boletim_df,
                    num_rows="dynamic",
                    use_container_width=True,
                    key="boletim_editor",
                )
                st.session_state["boletim_df"] = boletim_editado

                # Converte o boletim em texto para salvar no banco e usar no relatório
                linhas_boletim = []
                for _, row_b in boletim_editado.iterrows():
                    disc = str(row_b.get("Disciplina", "")).strip()
                    nota_b = str(row_b.get("Nota", "")).strip()
                    conteudo = str(row_b.get("Conteúdo programático", "")).strip()
                    if disc or nota_b or conteudo:
                        partes = []
                        if disc:
                            partes.append(f"Disciplina: {disc}")
                        if nota_b:
                            partes.append(f"Nota: {nota_b}")
                        if conteudo:
                            partes.append(f"Conteúdo: {conteudo}")
                        linhas_boletim.append(" | ".join(partes))
                st.session_state["boletim_texto"] = "\n".join(linhas_boletim)
            else:
                st.session_state["boletim_texto"] = ""
                st.caption("Para esta etapa, o foco principal são os registros de desenvolvimento global.")

            st.write("---")

            instrumento = get_instrumento_para_ano(ano_escolar)

            st.markdown("### Escala de desenvolvimento")
            st.markdown(
                "Escala de 1 a 5 para cada habilidade observada: "
                "1 = Ainda não demonstra &nbsp;&nbsp;|&nbsp;&nbsp; "
                "2 = Demonstra com muito apoio &nbsp;&nbsp;|&nbsp;&nbsp; "
                "3 = Em desenvolvimento &nbsp;&nbsp;|&nbsp;&nbsp; "
                "4 = Quase consolidado &nbsp;&nbsp;|&nbsp;&nbsp; "
                "5 = Consolidado",
                unsafe_allow_html=True,
            )

            # -------- FORMULÁRIO DE ESCALA – RADIO (CLIQUE DIRETO) --------
            with st.form("form_avaliacao"):
                respostas = {}
                for dom_code, dom_data in instrumento.items():
                    st.markdown(f"#### {dom_data['nome']}")
                    for item_code, item_text in dom_data["itens"]:
                        key = f"{dom_code}_{item_code}"

                        st.markdown(f"**{item_text}**")

                        valor = st.radio(
                            label="",
                            options=[1, 2, 3, 4, 5],
                            format_func=lambda x: LIKERT_OPCOES[x],
                            key=key,
                            horizontal=True,
                        )

                        respostas[item_code] = {
                            "dominio": dom_code,
                            "dominio_nome": dom_data["nome"],
                            "item_codigo": item_code,
                            "item_texto": item_text,
                            "resposta": valor,  # já é inteiro 1–5
                        }

                st.write("---")
                observacoes_gerais_form = st.text_area(
                    "Observações gerais sobre o estudante (opcional):",
                    key="observacoes_gerais",
                    height=120,
                )

                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    salvar_sem_relatorio = st.form_submit_button("Salvar avaliação (sem gerar relatório)")
                with col_btn2:
                    enviado = st.form_submit_button("Gerar relatório com IA")

            if salvar_sem_relatorio or enviado:
                escola = st.session_state.get("escola", "")
                turno = st.session_state.get("turno", "")
                ano_escolar = st.session_state.get("ano_escolar", "")
                turma = st.session_state.get("turma_crianca", "")
                ano_letivo = st.session_state.get("ano_letivo", "")
                bimestre = st.session_state.get("bimestre", "")
                nome_crianca = st.session_state.get("nome_crianca", "")
                sexo = st.session_state.get("sexo_crianca", "")
                nome_professora = st.session_state.get("nome_professora", "")
                neuroatipico = st.session_state.get("neuroatipico", False)

                # -------- AJUSTE 1: recalcular boletim_texto com o DF atual --------
                boletim_texto = ""
                if ano_tem_boletim(ano_escolar):
                    boletim_df_atual = st.session_state.get("boletim_df")
                    if boletim_df_atual is not None:
                        linhas_boletim = []
                        for _, row_b in boletim_df_atual.iterrows():
                            disc = str(row_b.get("Disciplina", "")).strip()
                            nota_b = str(row_b.get("Nota", "")).strip()
                            conteudo = str(row_b.get("Conteúdo programático", "")).strip()
                            if disc or nota_b or conteudo:
                                partes = []
                                if disc:
                                    partes.append(f"Disciplina: {disc}")
                                if nota_b:
                                    partes.append(f"Nota: {nota_b}")
                                if conteudo:
                                    partes.append(f"Conteúdo: {conteudo}")
                                linhas_boletim.append(" | ".join(partes))
                        boletim_texto = "\n".join(linhas_boletim)
                st.session_state["boletim_texto"] = boletim_texto

                observacoes_gerais = st.session_state.get("observacoes_gerais", "")

                if not escola or not nome_crianca or not nome_professora:
                    st.error("Preencha o cadastro do estudante antes de salvar ou gerar o relatório.")
                else:
                    # Radio sempre retorna 1–5, mas mantemos checagem de segurança
                    faltantes = [
                        cod for cod, r in respostas.items()
                        if r["resposta"] is None
                    ]
                    if faltantes:
                        st.error("Responda todas as perguntas da escala de desenvolvimento antes de salvar ou gerar o relatório.")
                    else:
                        for r in respostas.values():
                            r["resposta"] = int(r["resposta"])

                        df_itens, dominio_media, media_geral = calcular_scores(respostas)

                        pei_resumo_texto = carregar_pei_resumo(escola, nome_crianca)
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

                        if salvar_sem_relatorio and not enviado:
                            aluno_id = salvar_no_banco(
                                timestamp,
                                escola,
                                turno,
                                ano_escolar,
                                turma,
                                ano_letivo,
                                bimestre,
                                nome_crianca,
                                sexo,
                                nome_professora,
                                neuroatipico,
                                boletim_texto,
                                media_geral,
                                "",
                                "",
                                observacoes_gerais,
                                df_itens,
                                dominio_media,
                            )
                            st.success("Avaliação salva no banco de dados. Você poderá gerar o relatório depois na aba 'Consultas / Relatórios'.")
                            st.session_state["resultado"] = None

                        if enviado:
                            relatorio_generico = gerar_relatorio_ia(
                                sexo,
                                dominio_media,
                                media_geral,
                                ano_escolar,
                                boletim_texto,
                                neuroatipico,
                                pei_resumo_texto,
                                observacoes_gerais,
                            )
                            sugestoes_auto = gerar_sugestoes_ia(
                                dominio_media,
                                ano_escolar,
                                neuroatipico,
                                boletim_texto,
                                pei_resumo_texto,
                                observacoes_gerais,
                            )

                            aluno_id = salvar_no_banco(
                                timestamp,
                                escola,
                                turno,
                                ano_escolar,
                                turma,
                                ano_letivo,
                                bimestre,
                                nome_crianca,
                                sexo,
                                nome_professora,
                                neuroatipico,
                                boletim_texto,
                                media_geral,
                                relatorio_generico,
                                sugestoes_auto,
                                observacoes_gerais,
                                df_itens,
                                dominio_media,
                            )

                            st.session_state["resultado"] = {
                                "aluno_id": aluno_id,
                                "escola": escola,
                                "turno": turno,
                                "ano_escolar": ano_escolar,
                                "turma": turma,
                                "ano_letivo": ano_letivo,
                                "bimestre": bimestre,
                                "nome_crianca": nome_crianca,
                                "sexo": sexo,
                                "nome_professora": nome_professora,
                                "neuroatipico": neuroatipico,
                                "boletim_texto": boletim_texto,
                                "df_itens": df_itens,
                                "dominio_media": dominio_media,
                                "media_geral": media_geral,
                                "relatorio": relatorio_generico,
                                "sugestoes": sugestoes_auto,
                                "observacoes_gerais": observacoes_gerais,
                            }

    if st.session_state.get("resultado") is not None:
        data = st.session_state["resultado"]
        df_itens = data["df_itens"]
        dominio_media = data["dominio_media"]
        media_geral = data["media_geral"]
        observacoes_gerais = data.get("observacoes_gerais", "")

        st.success("Avaliação processada. Revise o relatório e as orientações antes de gerar o arquivo para impressão.")

        col_a, col_b = st.columns([1, 1])
        with col_a:
            st.markdown("### Médias por dimensão (escala interna 1–5)")
            df_show = dominio_media[["dominio_nome", "media_dominio"]].copy()
            df_show = df_show.rename(columns={
                "dominio_nome": "Dimensão",
                "media_dominio": "Média (1–5)",
            })
            st.dataframe(df_show.style.format({"Média (1–5)": "{:.2f}"}))
            if not pd.isna(media_geral):
                st.markdown(f"**Média geral na escala interna (desconsiderando dados ausentes):** {media_geral:.2f}")
            else:
                st.markdown("**Média geral:** sem cálculo (muitas respostas ausentes).")
        with col_b:
            st.markdown("### Gráfico de radar (uso interno)")
            fig = plot_radar(dominio_media)
            st.pyplot(fig)

        st.write("---")

        relatorio_editado = st.text_area(
            "Relatório individual do aluno (edite se desejar):",
            value=data["relatorio"],
            height=260,
            key="relatorio_editado",
        )

        sugestoes_editadas = st.text_area(
            "Plano de estudo complementar / orientações para a família (edite se desejar):",
            value=data["sugestoes"],
            height=260,
            key="sugestoes_editadas",
        )

        st.write("---")
        salvar_final = st.button("Salvar relatório final e gerar arquivo para impressão")

        if salvar_final:
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE alunos
                SET relatorio_texto = ?, sugestoes_texto = ?, observacoes_gerais = ?
                WHERE id = ?
                """,
                (
                    relatorio_editado,
                    sugestoes_editadas,
                    observacoes_gerais,
                    data["aluno_id"],
                ),
            )
            conn.commit()
            conn.close()

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_name = data["nome_crianca"].replace(" ", "_")

            img_bytes = io.BytesIO()
            fig = plot_radar(dominio_media)
            fig.savefig(img_bytes, format="png", bbox_inches="tight")
            img_bytes.seek(0)
            radar_b64 = base64.b64encode(img_bytes.getvalue()).decode("utf-8")

            historico_html = montar_historico_aluno(
                data["escola"],
                data["nome_crianca"],
            )
            pei_resumo_html = carregar_pei_resumo(
                data["escola"],
                data["nome_crianca"],
            )

            html_relatorio = gerar_html_impressao(
                data["escola"],
                data["turno"],
                data["ano_escolar"],
                data["turma"],
                data["ano_letivo"],
                data["bimestre"],
                data["nome_crianca"],
                data["nome_professora"],
                data["sexo"],
                data["boletim_texto"],
                df_itens,
                dominio_media,
                media_geral,
                relatorio_editado,
                sugestoes_editadas,
                radar_b64,
                historico_html,
                pei_resumo_html,
                observacoes_gerais,
            )

            html_path = os.path.join(BASE_DIR, f"{safe_name}_{timestamp}.html")
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html_relatorio)

            st.success(f"Avaliação e relatório final salvos. Arquivo HTML gerado em: {html_path}")

            st.download_button(
                label="Baixar relatório para impressão (.html)",
                data=html_relatorio,
                file_name=f"relatorio_{safe_name}.html",
                mime="text/html",
            )

# ---------------------------------------------------------
# ABA 2 – CONSULTAS / RELATÓRIOS CONSOLIDADOS
# ---------------------------------------------------------
with tab_consulta:
    st.markdown("## Consultas e relatórios consolidados")

    if not os.path.exists(DB_PATH):
        st.info("Ainda não há banco de dados criado. Salve ao menos uma avaliação na aba 'Nova avaliação'.")
    else:
        conn = sqlite3.connect(DB_PATH)
        df_alunos = pd.read_sql_query("SELECT * FROM alunos", conn)
        df_dom = pd.read_sql_query("SELECT * FROM dominios", conn)
        conn.close()

        if df_alunos.empty:
            st.info("Nenhuma avaliação registrada até o momento.")
        else:
            escolas = ["(Todas)"] + sorted(df_alunos["escola"].dropna().unique().tolist())
            turnos = ["(Todos)"] + sorted(df_alunos["turno"].dropna().unique().tolist())
            profs = ["(Todos)"] + sorted(df_alunos["nome_professora"].dropna().unique().tolist())
            turmas = ["(Todas)"] + sorted(df_alunos["turma"].dropna().unique().tolist())
            alunos_list = ["(Todos)"] + sorted(df_alunos["nome_crianca"].dropna().unique().tolist())

            colf1, colf2, colf3 = st.columns(3)
            with colf1:
                filtro_escola = st.selectbox("Filtrar por escola", escolas)
            with colf2:
                filtro_turno = st.selectbox("Filtrar por turno", turnos)
            with colf3:
                filtro_prof = st.selectbox("Filtrar por professora", profs)

            colf4, colf5 = st.columns(2)
            with colf4:
                filtro_turma = st.selectbox("Filtrar por turma", turmas)
            with colf5:
                filtro_aluno = st.selectbox("Filtrar por aluno", alunos_list)

            df_filt = df_alunos.copy()
            if filtro_escola != "(Todas)":
                df_filt = df_filt[df_filt["escola"] == filtro_escola]
            if filtro_turno != "(Todos)":
                df_filt = df_filt[df_filt["turno"] == filtro_turno]
            if filtro_prof != "(Todos)":
                df_filt = df_filt[df_filt["nome_professora"] == filtro_prof]
            if filtro_turma != "(Todas)":
                df_filt = df_filt[df_filt["turma"] == filtro_turma]
            if filtro_aluno != "(Todos)":
                df_filt = df_filt[df_filt["nome_crianca"] == filtro_aluno]

            st.markdown("### Avaliações encontradas")
            if df_filt.empty:
                st.info("Nenhuma avaliação encontrada para o filtro selecionado.")
            else:
                df_filt_sorted = df_filt.sort_values("timestamp", ascending=False)

                header_cols = st.columns([2, 2, 1.5, 1.5, 2, 1.2, 1, 1, 1])
                headers = [
                    "Data/Hora",
                    "Aluno",
                    "Escola",
                    "Turma",
                    "Professora",
                    "Bimestre",
                    "Reimprimir",
                    "Editar",
                    "Excluir",
                ]
                for col, h in zip(header_cols, headers):
                    col.markdown(f"**{h}**")

                for _, row in df_filt_sorted.iterrows():
                    c1, c2, c3, c4, c5, c6, c7, c8, c9 = st.columns([2, 2, 1.5, 1.5, 2, 1.2, 1, 1, 1])
                    c1.write(row["timestamp"])
                    c2.write(row["nome_crianca"])
                    c3.write(row["escola"] or "")
                    c4.write(f"{row['ano_escolar'] or ''} / {row['turma'] or ''}")
                    c5.write(row["nome_professora"] or "")
                    c6.write(row["bimestre"] or "")

                    reprint_key = f"reprint_{row['id']}"
                    edit_key = f"edit_{row['id']}"
                    del_key = f"del_{row['id']}"

                    if c7.button("Reimprimir", key=reprint_key):
                        st.session_state["reprint_id"] = row["id"]
                        st.success("Botão de download gerado abaixo na página.")
                        st.rerun()

                    if c8.button("Editar", key=edit_key):
                        st.session_state["edit_id"] = row["id"]
                        st.session_state["edit_loaded"] = False
                        # Força um novo rerun para a aba "Nova avaliação" já vir preenchida
                        st.rerun()

                    if c9.button("Excluir", key=del_key):
                        conn = sqlite3.connect(DB_PATH)
                        cur = conn.cursor()
                        cur.execute("DELETE FROM respostas WHERE aluno_id = ?", (row["id"],))
                        cur.execute("DELETE FROM dominios WHERE aluno_id = ?", (row["id"],))
                        cur.execute("DELETE FROM alunos WHERE id = ?", (row["id"],))
                        conn.commit()
                        conn.close()
                        st.success("Avaliação excluída com sucesso.")
                        st.rerun()

                if st.session_state.get("reprint_id") is not None:
                    selected_id = st.session_state["reprint_id"]
                    conn = sqlite3.connect(DB_PATH)
                    df_res = pd.read_sql_query(
                        "SELECT dominio, dominio_nome, item_codigo, item_texto, resposta, observacao FROM respostas WHERE aluno_id = ?",
                        conn,
                        params=(selected_id,),
                    )
                    df_dom_aluno = pd.read_sql_query(
                        "SELECT dominio, dominio_nome, media_dominio FROM dominios WHERE aluno_id = ?",
                        conn,
                        params=(selected_id,),
                    )
                    df_al = pd.read_sql_query(
                        "SELECT * FROM alunos WHERE id = ?",
                        conn,
                        params=(selected_id,),
                    )
                    conn.close()

                    if not df_al.empty and not df_res.empty and not df_dom_aluno.empty:
                        row_aluno = df_al.iloc[0]
                        dominio_media_aluno = df_dom_aluno.rename(
                            columns={"dominio_nome": "dominio_nome", "media_dominio": "media_dominio"},
                        )

                        fig_aluno = plot_radar(dominio_media_aluno)
                        img_bytes_aluno = io.BytesIO()
                        fig_aluno.savefig(img_bytes_aluno, format="png", bbox_inches="tight")
                        img_bytes_aluno.seek(0)
                        radar_b64_aluno = base64.b64encode(img_bytes_aluno.getvalue()).decode("utf-8")

                        historico_html = montar_historico_aluno(
                            row_aluno["escola"],
                            row_aluno["nome_crianca"],
                        )
                        pei_resumo_html = carregar_pei_resumo(
                            row_aluno["escola"],
                            row_aluno["nome_crianca"],
                        )
                        obs_gerais = row_aluno.get("observacoes_gerais", "") if "observacoes_gerais" in row_aluno else ""

                        html_sel = gerar_html_impressao(
                            row_aluno["escola"],
                            row_aluno["turno"],
                            row_aluno["ano_escolar"],
                            row_aluno["turma"],
                            row_aluno["ano_letivo"],
                            row_aluno["bimestre"],
                            row_aluno["nome_crianca"],
                            row_aluno["nome_professora"],
                            row_aluno["sexo"],
                            row_aluno["boletim_texto"] or "",
                            df_res,
                            dominio_media_aluno,
                            row_aluno["media_geral"],
                            row_aluno["relatorio_texto"] or "",
                            row_aluno["sugestoes_texto"] or "",
                            radar_b64_aluno,
                            historico_html,
                            pei_resumo_html,
                            obs_gerais,
                        )

                        st.download_button(
                            label="Baixar relatório da criança selecionada (.html)",
                            data=html_sel,
                            file_name=f"relatorio_{row_aluno['nome_crianca'].replace(' ', '_')}.html",
                            mime="text/html",
                        )
                    else:
                        st.info("Não há dados detalhados suficientes para reimprimir essa avaliação.")
                    # opcional: limpar para não reutilizar automaticamente
                    # st.session_state["reprint_id"] = None

                if not df_filt.empty:
                    df_merged = df_dom.merge(
                        df_filt[["id", "escola", "turno", "turma", "nome_professora", "nome_crianca"]],
                        left_on="aluno_id",
                        right_on="id",
                        how="inner",
                    )

                    if df_merged.empty:
                        st.info("Nenhum dado detalhado para o filtro selecionado.")
                    else:
                        st.markdown("### Visão macro por escola, turno, turma e professora")

                        colm1, colm2 = st.columns(2)
                        with colm1:
                            st.markdown("**Médias por escola (todas as dimensões)**")
                            macro_escola = (
                                df_merged.groupby("escola")["media_dominio"]
                                .mean()
                                .reset_index()
                                .rename(columns={"escola": "Escola", "media_dominio": "Média global (1–5)"})
                            )
                            st.dataframe(macro_escola.style.format({"Média global (1–5)": "{:.2f}"}))

                        with colm2:
                            st.markdown("**Médias por turno (todas as dimensões)**")
                            macro_turno = (
                                df_merged.groupby("turno")["media_dominio"]
                                .mean()
                                .reset_index()
                                .rename(columns={"turno": "Turno", "media_dominio": "Média global (1–5)"})
                            )
                            st.dataframe(macro_turno.style.format({"Média global (1–5)": "{:.2f}"}))

                        colm3, colm4 = st.columns(2)
                        with colm3:
                            st.markdown("**Médias por turma (todas as dimensões)**")
                            macro_turma = (
                                df_merged.groupby("turma")["media_dominio"]
                                .mean()
                                .reset_index()
                                .rename(columns={"turma": "Turma", "media_dominio": "Média global (1–5)"})
                            )
                            st.dataframe(macro_turma.style.format({"Média global (1–5)": "{:.2f}"}))

                        with colm4:
                            st.markdown("**Médias por professora (todas as dimensões)**")
                            macro_prof = (
                                df_merged.groupby("nome_professora")["media_dominio"]
                                .mean()
                                .reset_index()
                                .rename(columns={"nome_professora": "Professora", "media_dominio": "Média global (1–5)"})
                            )
                            st.dataframe(macro_prof.style.format({"Média global (1–5)": "{:.2f}"}))

                        st.markdown("### Relatório consolidado por dimensão (recorte atual)")
                        dim_consol = (
                            df_merged.groupby("dominio_nome")["media_dominio"]
                            .mean()
                            .reset_index()
                            .rename(columns={"dominio_nome": "Dimensão", "media_dominio": "Média (1–5)"})
                        )
                        st.dataframe(dim_consol.style.format({"Média (1–5)": "{:.2f}"}))

                        st.download_button(
                            label="Baixar consolidado em CSV (dimensões - recorte atual)",
                            data=dim_consol.to_csv(index=False, encoding="utf-8-sig"),
                            file_name="consolidado_turma_dimensoes.csv",
                            mime="text/csv",
                        )

                        st.write("---")
                        st.markdown("### Relatório individualizado por professora")

                        if st.button("Gerar relatório consolidado da professora"):
                            if filtro_prof == "(Todos)":
                                st.warning("Selecione uma professora específica no filtro para gerar o relatório individualizado.")
                            else:
                                df_alunos_prof = df_alunos[df_alunos["nome_professora"] == filtro_prof]
                                if filtro_escola != "(Todas)":
                                    df_alunos_prof = df_alunos_prof[df_alunos_prof["escola"] == filtro_escola]
                                if filtro_turma != "(Todas)":
                                    df_alunos_prof = df_alunos_prof[df_alunos_prof["turma"] == filtro_turma]

                                if df_alunos_prof.empty:
                                    st.info("Não há avaliações registradas para essa professora com o filtro atual.")
                                else:
                                    df_prof_merged = df_dom.merge(
                                        df_alunos_prof[
                                            ["id", "escola", "turno", "turma", "nome_professora", "nome_crianca", "ano_letivo"]
                                        ],
                                        left_on="aluno_id",
                                        right_on="id",
                                        how="inner",
                                    )

                                    if df_prof_merged.empty:
                                        st.info("Não há dados detalhados para essa professora com o filtro atual.")
                                    else:
                                        n_alunos_prof = df_alunos_prof.shape[0]
                                        media_geral_prof = df_alunos_prof["media_geral"].mean()

                                        escola_prof = df_alunos_prof["escola"].iloc[0]
                                        turno_prof = df_alunos_prof["turno"].iloc[0]
                                        turma_prof = (
                                            filtro_turma if filtro_turma != "(Todas)" else df_alunos_prof["turma"].iloc[0]
                                        )
                                        ano_letivo_prof = df_alunos_prof["ano_letivo"].iloc[0]

                                        dominio_media_prof = (
                                            df_prof_merged.groupby("dominio_nome")["media_dominio"]
                                            .mean()
                                            .reset_index()
                                            .rename(columns={"dominio_nome": "Dimensão", "media_dominio": "Média (1–5)"})
                                        )

                                        colp1, colp2 = st.columns(2)
                                        with colp1:
                                            st.markdown("#### Médias por dimensão (turma da professora)")
                                            st.dataframe(
                                                dominio_media_prof.style.format({"Média (1–5)": "{:.2f}"}),
                                            )

                                        with colp2:
                                            st.markdown("#### Gráfico de radar da turma da professora")
                                            dominio_media_prof_plot = dominio_media_prof.rename(
                                                columns={"Dimensão": "dominio_nome", "Média (1–5)": "media_dominio"},
                                            )
                                            if "dominio" not in dominio_media_prof_plot.columns:
                                                dominio_media_prof_plot["dominio"] = ""
                                            fig_prof = plot_radar(dominio_media_prof_plot)
                                            st.pyplot(fig_prof)

                                        dominio_media_prof_base = dominio_media_prof.rename(
                                            columns={"Dimensão": "dominio_nome", "Média (1–5)": "media_dominio"},
                                        )
                                        contexto_parts_prof = [
                                            f"Relatório individualizado da professora {filtro_prof}.",
                                            f"Escola: {escola_prof}.",
                                            f"Turno: {turno_prof}.",
                                            f"Turma: {turma_prof}.",
                                            f"Ano letivo: {ano_letivo_prof}.",
                                            f"Número de estudantes avaliados: {n_alunos_prof}.",
                                        ]
                                        contexto_prof_str = " ".join(contexto_parts_prof)

                                        plano_prof = gerar_plano_turma_ia(
                                            dominio_media_prof_base,
                                            contexto_prof_str,
                                        )

                                        plano_prof_editado = st.text_area(
                                            "Plano de desenvolvimento global da turma (edite se desejar):",
                                            value=plano_prof,
                                            height=350,
                                            key="plano_prof_texto",
                                        )

                                        img_prof_bytes = io.BytesIO()
                                        fig_prof.savefig(img_prof_bytes, format="png", bbox_inches="tight")
                                        img_prof_bytes.seek(0)
                                        radar_b64 = base64.b64encode(img_prof_bytes.getvalue()).decode("utf-8")

                                        html_prof = gerar_html_relatorio_professora(
                                            nome_professora=filtro_prof,
                                            escola=escola_prof,
                                            turno=turno_prof,
                                            turma=turma_prof,
                                            ano_letivo=ano_letivo_prof,
                                            n_alunos=n_alunos_prof,
                                            media_geral_prof=media_geral_prof if not pd.isna(media_geral_prof) else 0.0,
                                            dominio_media_prof=dominio_media_prof,
                                            plano_prof=plano_prof_editado,
                                            radar_b64=radar_b64,
                                        )

                                        safe_prof = filtro_prof.replace(" ", "_")
                                        st.download_button(
                                            label="Exportar relatório da professora (.html)",
                                            data=html_prof,
                                            file_name=f"relatorio_professora_{safe_prof}.html",
                                            mime="text/html",
                                        )

# ---------------------------------------------------------
# ABA 3 – PEI – PLANO EDUCACIONAL INDIVIDUAL
# ---------------------------------------------------------
with tab_pei:
    st.markdown("## Plano Educacional Individualizado (PEI)")
    st.markdown(
        "Registro de informações para estudantes com necessidades educacionais específicas. "
        "Os dados do PEI podem complementar os relatórios de desempenho, independentemente do ano escolar."
    )

    init_db()

    escola_pei_default = ""
    nome_pei_default = ""
    ano_escolar_pei_default = ANOS_ESCOLARES[0]
    ano_letivo_pei_default = ""

    session_has_neuro = bool(
        st.session_state.get("aluno_cadastrado")
        and st.session_state.get("neuroatipico")
        and st.session_state.get("escola")
        and st.session_state.get("nome_crianca")
    )

    df_alunos_pei = None
    mapa_pei = {}
    escolha_pei = None

    if os.path.exists(DB_PATH):
        conn = sqlite3.connect(DB_PATH)
        df_alunos_pei = pd.read_sql_query(
            """
            SELECT DISTINCT escola, nome_crianca, ano_escolar, ano_letivo, neuroatipico
            FROM alunos
            WHERE neuroatipico = 1
            ORDER BY escola, nome_crianca
            """,
            conn,
        )
        conn.close()

        if df_alunos_pei is not None and not df_alunos_pei.empty:
            opcoes_pei = ["(Selecionar aluno neuroatípico cadastrado)"]
            mapa_pei = {}
            default_index = 0

            sess_escola = st.session_state.get("escola", "")
            sess_nome = st.session_state.get("nome_crianca", "")
            sess_ano_escolar = st.session_state.get("ano_escolar", "")
            sess_ano_letivo = st.session_state.get("ano_letivo", "")

            for _, row in df_alunos_pei.iterrows():
                label = f"{row['nome_crianca']} – {row['escola']} – {row['ano_escolar']} ({row['ano_letivo']})"
                opcoes_pei.append(label)
                mapa_pei[label] = row

                if session_has_neuro:
                    if (
                        row["escola"] == sess_escola
                        and row["nome_crianca"] == sess_nome
                        and row["ano_escolar"] == sess_ano_escolar
                        and row["ano_letivo"] == sess_ano_letivo
                    ):
                        default_index = len(opcoes_pei) - 1

            escolha_pei = st.selectbox(
                "Vincular PEI a um aluno já cadastrado:",
                opcoes_pei,
                index=default_index,
            )

            if escolha_pei != "(Selecionar aluno neuroatípico cadastrado)":
                row_sel = mapa_pei[escolha_pei]
                escola_pei_default = row_sel["escola"] or ""
                nome_pei_default = row_sel["nome_crianca"] or ""
                ano_escolar_pei_default = row_sel["ano_escolar"] or ANOS_ESCOLARES[0]
                ano_letivo_pei_default = row_sel["ano_letivo"] or ""
        else:
            st.caption("Ainda não há alunos neuroatípicos com avaliações registradas no banco de dados.")

    if session_has_neuro and not escola_pei_default and not nome_pei_default:
        escola_pei_default = st.session_state.get("escola", "")
        nome_pei_default = st.session_state.get("nome_crianca", "")
        ano_escolar_pei_default = st.session_state.get("ano_escolar", ANOS_ESCOLARES[0])
        ano_letivo_pei_default = st.session_state.get("ano_letivo", "")

        if escola_pei_default and nome_pei_default:
            st.info(
                f"PEI vinculado automaticamente ao aluno neuroatípico atualmente cadastrado: "
                f"{nome_pei_default} – {escola_pei_default} – {ano_escolar_pei_default} ({ano_letivo_pei_default})."
            )

    with st.form("form_pei"):
        colp1, colp2 = st.columns(2)
        with colp1:
            escola_pei = st.text_input("Escola", escola_pei_default)
            nome_crianca_pei = st.text_input("Nome do aluno", nome_pei_default)

            if ano_escolar_pei_default in ANOS_ESCOLARES:
                idx_ano = ANOS_ESCOLARES.index(ano_escolar_pei_default)
            else:
                idx_ano = 0

            ano_escolar_pei = st.selectbox(
                "Ano escolar",
                ANOS_ESCOLARES,
                index=idx_ano,
            )
        with colp2:
            ano_letivo_pei = st.text_input("Ano letivo (ex.: 2025)", ano_letivo_pei_default)

        st.markdown("### Perfil e necessidades")
        perfil = st.text_area("Perfil do estudante (rotina, formas de comunicação, interesses)", height=100)
        pontos_fortes = st.text_area("Pontos fortes e potencialidades observadas", height=80)
        habilidades_desenvolvimento = st.text_area(
            "Habilidades em desenvolvimento que exigem maior apoio",
            height=80,
        )

        st.markdown("### Apoios e estratégias")
        recursos_apoio = st.text_area(
            "Recursos e apoios utilizados (apoio em sala, recursos visuais, tecnologia assistiva etc.)",
            height=80,
        )
        estrategias_metodologicas = st.text_area(
            "Estratégias metodológicas que favorecem a participação (ex.: instruções em etapas, atividades práticas, materiais visuais)",
            height=80,
        )
        adaptacoes_avaliacao = st.text_area(
            "Adaptações nas situações de avaliação (tempo ampliado, leitura das questões, formatos alternativos)",
            height=80,
        )
        participacao_familia = st.text_area(
            "Registro sobre participação da família e acordos de acompanhamento conjunto",
            height=80,
        )

        salvar_pei_btn = st.form_submit_button("Salvar PEI do aluno")

    if salvar_pei_btn:
        if not escola_pei or not nome_crianca_pei:
            st.error("Preencha pelo menos a escola e o nome do aluno para salvar o PEI.")
        else:
            salvar_pei(
                escola_pei,
                nome_crianca_pei,
                ano_escolar_pei,
                ano_letivo_pei,
                perfil,
                pontos_fortes,
                habilidades_desenvolvimento,
                recursos_apoio,
                estrategias_metodologicas,
                adaptacoes_avaliacao,
                participacao_familia,
            )
            st.success("PEI salvo com sucesso. As informações serão consideradas nos relatórios dos estudantes marcados como neuroatípicos.")
