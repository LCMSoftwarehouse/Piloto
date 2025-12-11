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
import tempfile
if os.environ.get("STREAMLIT_SHARING_MODE") or os.path.exists("/mount/src"):
    # Estamos no Streamlit Cloud
    DATA_DIR = tempfile.gettempdir()
else:
    # Estamos em ambiente local
    DATA_DIR = os.path.join(BASE_DIR, "data")
    os.makedirs(DATA_DIR, exist_ok=True)

LOGO_FILE = "image.png"
LOGO_PATH = os.path.join(BASE_DIR, LOGO_FILE)

DB_PATH = os.path.join(DATA_DIR, "avaliacoes_maplebear.db")

# Paleta Maple Bear
MAPLE_RED = "#E2231A"
MAPLE_GOLD = "#F9C23C"
MAPLE_DARK = "#333333"
MAPLE_BG = "#FFF5E9"

# =========================================================
# CONFIG STREAMLIT
# =========================================================
st.set_page_config(
    page_title="Avaliação de Alfabetização - Maple Bear",
    layout="wide"
)

st.markdown(
    f"""
    <style>
    /* ============================================
       TEMA CLARO MODERNO - MAPLE BEAR
       ============================================ */
    
    :root, html, body {{
        color-scheme: light only !important;
    }}
    
    /* Fundo principal */
    html, body, .main, .stApp, 
    [data-testid="stAppViewContainer"],
    [data-testid="stHeader"],
    [data-testid="stToolbar"],
    [data-testid="stDecoration"],
    [data-testid="stStatusWidget"],
    .block-container {{
        background-color: {MAPLE_BG} !important;
        color: {MAPLE_DARK} !important;
    }}
    
    /* Sidebar */
    [data-testid="stSidebar"],
    [data-testid="stSidebarContent"],
    section[data-testid="stSidebar"] > div {{
        background-color: #FFFFFF !important;
    }}
    
    /* ============================================
       TEXTOS E LABELS
       ============================================ */
    p, span, label, div, li, td, th,
    .stMarkdown, .stText,
    [data-testid="stMarkdownContainer"],
    [data-testid="stMarkdownContainer"] p,
    [data-testid="stMarkdownContainer"] span {{
        color: {MAPLE_DARK} !important;
    }}
    
    /* Títulos - cor mais elegante */
    h1, h2, h3,
    [data-testid="stMarkdownContainer"] h1,
    [data-testid="stMarkdownContainer"] h2,
    [data-testid="stMarkdownContainer"] h3 {{
        color: {MAPLE_RED} !important;
    }}
    
    /* Subtítulos h4, h5, h6 - cinza escuro */
    h4, h5, h6,
    [data-testid="stMarkdownContainer"] h4,
    [data-testid="stMarkdownContainer"] h5,
    [data-testid="stMarkdownContainer"] h6 {{
        color: {MAPLE_DARK} !important;
    }}
    
    .maple-title {{
        color: {MAPLE_RED} !important;
        font-weight: 700;
        font-size: 32px;
    }}
    .maple-subtitle {{
        color: #666666 !important;
        font-size: 16px;
    }}
    
    /* ============================================
       INPUTS DE TEXTO - MODERNO
       ============================================ */
    input, textarea,
    .stTextInput input,
    .stTextArea textarea,
    [data-testid="stTextInput"] input,
    [data-testid="stTextArea"] textarea,
    [data-baseweb="input"] input,
    [data-baseweb="textarea"] textarea {{
        background-color: #FFFFFF !important;
        color: {MAPLE_DARK} !important;
        border: 2px solid #D0D0D0 !important;
        border-radius: 8px !important;
        -webkit-text-fill-color: {MAPLE_DARK} !important;
        padding: 10px 12px !important;
        transition: border-color 0.2s ease !important;
    }}
    
    input:focus, textarea:focus,
    .stTextInput input:focus,
    .stTextArea textarea:focus {{
        border-color: {MAPLE_RED} !important;
        outline: none !important;
        box-shadow: 0 0 0 3px rgba(226, 35, 26, 0.1) !important;
    }}
    
    input::placeholder, textarea::placeholder {{
        color: #AAAAAA !important;
        -webkit-text-fill-color: #AAAAAA !important;
    }}
    
    [data-baseweb="input"],
    [data-baseweb="textarea"],
    [data-baseweb="base-input"] {{
        background-color: #FFFFFF !important;
        border-radius: 8px !important;
    }}
    
    /* ============================================
       SELECTBOX / DROPDOWN - BORDAS VISÍVEIS
       ============================================ */
    [data-baseweb="select"] > div {{
        background-color: #FFFFFF !important;
        border: 2px solid #D0D0D0 !important;
        border-radius: 8px !important;
        min-height: 42px !important;
    }}
    
    [data-baseweb="select"] > div:hover {{
        border-color: #B0B0B0 !important;
    }}
    
    [data-baseweb="select"] > div:focus-within {{
        border-color: {MAPLE_RED} !important;
        box-shadow: 0 0 0 3px rgba(226, 35, 26, 0.1) !important;
    }}
    
    /* Esconde completamente o input de digitação dentro do select */
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
    
    /* Remove a borda do container interno do input */
    [data-baseweb="select"] [data-baseweb="input"] {{
        border: none !important;
        background: transparent !important;
    }}
    
    /* Dropdown menu */
    [data-baseweb="popover"],
    [data-baseweb="menu"],
    ul[role="listbox"],
    [data-baseweb="menu"] ul {{
        background-color: #FFFFFF !important;
        border: 1px solid #D0D0D0 !important;
        border-radius: 8px !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1) !important;
    }}
    
    ul[role="listbox"] li,
    [data-baseweb="menu"] li {{
        background-color: #FFFFFF !important;
        color: {MAPLE_DARK} !important;
    }}
    
    ul[role="listbox"] li:hover,
    [data-baseweb="menu"] li:hover {{
        background-color: #FFF0E8 !important;
    }}
    
    /* Texto dentro do select */
    [data-baseweb="select"] span,
    [data-baseweb="select"] div {{
        color: {MAPLE_DARK} !important;
        -webkit-text-fill-color: {MAPLE_DARK} !important;
    }}
    
    /* Ícone seta do dropdown */
    [data-baseweb="select"] svg {{
        fill: #666666 !important;
    }}
    
    /* ============================================
       RADIO BUTTONS - ESTILO MODERNO
       ============================================ */
    .stRadio label,
    .stRadio [role="radiogroup"] label,
    [data-testid="stRadio"] label {{
        color: {MAPLE_DARK} !important;
        font-size: 14px !important;
    }}
    
    /* Container do radio - bolinha externa (borda) */
    [data-baseweb="radio"] > div:first-child {{
        width: 20px !important;
        height: 20px !important;
        border: 2px solid #B0B0B0 !important;
        border-radius: 50% !important;
        background-color: #FFFFFF !important;
        transition: all 0.2s ease !important;
    }}
    
    /* Bolinha interna - ESCONDIDA por padrão */
    [data-baseweb="radio"] > div:first-child > div {{
        background-color: transparent !important;
        width: 0px !important;
        height: 0px !important;
        border-radius: 50% !important;
        transition: all 0.2s ease !important;
    }}
    
    /* Hover na bolinha - só muda a borda */
    [data-baseweb="radio"]:hover > div:first-child {{
        border-color: {MAPLE_RED} !important;
    }}
    
    /* Radio SELECIONADO - bolinha interna vermelha aparece */
    [data-baseweb="radio"]:has(input:checked) > div:first-child > div,
    [data-baseweb="radio"][data-checked="true"] > div:first-child > div {{
        background-color: {MAPLE_RED} !important;
        width: 10px !important;
        height: 10px !important;
    }}
    
    /* Quando selecionado, borda também fica vermelha */
    [data-baseweb="radio"]:has(input:checked) > div:first-child,
    [data-baseweb="radio"][data-checked="true"] > div:first-child {{
        border-color: {MAPLE_RED} !important;
        background-color: #FFFFFF !important;
    }}
    
    /* ============================================
       CHECKBOX - ESTILO MODERNO
       ============================================ */
    .stCheckbox label,
    [data-testid="stCheckbox"] label {{
        color: {MAPLE_DARK} !important;
    }}
    
    [data-baseweb="checkbox"] > div:first-child {{
        width: 20px !important;
        height: 20px !important;
        border: 2px solid #B0B0B0 !important;
        border-radius: 4px !important;
        background-color: #FFFFFF !important;
        transition: all 0.2s ease !important;
    }}
    
    [data-baseweb="checkbox"]:hover > div:first-child {{
        border-color: {MAPLE_RED} !important;
    }}
    
    [data-baseweb="checkbox"][data-checked="true"] > div:first-child {{
        background-color: {MAPLE_RED} !important;
        border-color: {MAPLE_RED} !important;
    }}
    
    /* ============================================
       BOTÕES - MODERNO
       ============================================ */
    .stButton > button,
    [data-testid="stFormSubmitButton"] > button {{
        background-color: {MAPLE_RED} !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 10px 24px !important;
        font-weight: 600 !important;
        transition: all 0.2s ease !important;
        box-shadow: 0 2px 4px rgba(226, 35, 26, 0.2) !important;
    }}
    
    .stButton > button:hover,
    [data-testid="stFormSubmitButton"] > button:hover {{
        background-color: #C41E17 !important;
        box-shadow: 0 4px 8px rgba(226, 35, 26, 0.3) !important;
        transform: translateY(-1px) !important;
    }}
    
    /* Download button */
    .stDownloadButton > button {{
        background-color: {MAPLE_GOLD} !important;
        color: {MAPLE_DARK} !important;
        box-shadow: 0 2px 4px rgba(249, 194, 60, 0.3) !important;
    }}
    
    .stDownloadButton > button:hover {{
        background-color: #E5B035 !important;
    }}
    
    /* ============================================
       TABS
       ============================================ */
    .stTabs [data-baseweb="tab-list"] {{
        background-color: transparent !important;
        gap: 8px !important;
    }}
    
    .stTabs [data-baseweb="tab"] {{
        color: #666666 !important;
        background-color: transparent !important;
        border-radius: 8px 8px 0 0 !important;
        padding: 10px 20px !important;
    }}
    
    .stTabs [data-baseweb="tab"][aria-selected="true"] {{
        color: {MAPLE_RED} !important;
        font-weight: 600 !important;
        border-bottom: 3px solid {MAPLE_RED} !important;
    }}
    
    /* ============================================
       FORMS
       ============================================ */
    [data-testid="stForm"] {{
        background-color: #FFFFFF !important;
        border: 1px solid #E8E8E8 !important;
        border-radius: 12px !important;
        padding: 24px !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04) !important;
    }}
    
    /* ============================================
       EXPANDER
       ============================================ */
    [data-testid="stExpander"],
    details {{
        background-color: #FFFFFF !important;
        border: 1px solid #E8E8E8 !important;
        border-radius: 8px !important;
    }}
    
    [data-testid="stExpander"] summary,
    details summary {{
        color: {MAPLE_DARK} !important;
        font-weight: 500 !important;
    }}
    
    /* ============================================
       DATAFRAME / TABELAS
       ============================================ */
    .stDataFrame,
    [data-testid="stDataFrame"],
    table {{
        background-color: #FFFFFF !important;
        border-radius: 8px !important;
        overflow: hidden !important;
    }}
    
    th {{
        background-color: #F8F8F8 !important;
        color: {MAPLE_DARK} !important;
        font-weight: 600 !important;
    }}
    
    td {{
        background-color: #FFFFFF !important;
        color: {MAPLE_DARK} !important;
    }}
    
    /* ============================================
       ALERTAS
       ============================================ */
    .stAlert {{
        border-radius: 8px !important;
    }}
    
    /* ============================================
       LABELS DOS WIDGETS
       ============================================ */
    [data-testid="stWidgetLabel"],
    [data-testid="stWidgetLabel"] p {{
        color: #555555 !important;
        font-weight: 500 !important;
        font-size: 14px !important;
    }}
    
    /* ============================================
       DIVIDERS
       ============================================ */
    hr {{
        border-color: #E8E8E8 !important;
    }}
    
    /* ============================================
       TEXT AREA
       ============================================ */
    .stTextArea textarea {{
        min-height: 120px !important;
    }}
    
    </style>
    """,
    unsafe_allow_html=True
)

if not OPENAI_ENABLED:
    st.warning(
        "OPENAI_API_KEY não configurada no código. "
        "Os textos automáticos serão gerados por regra interna (sem API)."
    )

# =========================================================
# ESTRUTURA DA ESCALA / ITENS
# =========================================================
LIKERT_OPCOES = {
    0: "N/A - Não aplicável (habilidade ainda não apresentada)",
    1: "1 - Não aparente",
    2: "2 - Em desenvolvimento",
    3: "3 - Bem desenvolvido",
}

DOMAINS = {
    "A": {
        "nome": "Habilidades Sociais",
        "itens": [
            ("A1", "Demonstra respeito e interage adequadamente com professores."),
            ("A2", "Demonstra respeito e interage adequadamente com colegas."),
            ("A3", "Adapta-se a novas situações e mudanças."),
            ("A4", "Segue regras e rotinas."),
            ("A5", "Aguarda a própria vez em jogos e interações com colegas."),
            ("A6", "Estabelece relações entre suas atitudes e as respectivas consequências."),
            ("A7", "Coopera e compartilha com outras crianças."),
        ],
    },
    "B": {
        "nome": "Cuidados Pessoais",
        "itens": [
            ("B1", "Usa o toalete adequadamente."),
            ("B2", "Demonstra habilidades adequadas de lavar as mãos."),
            ("B3", "Veste-se e calça-se de maneira apropriada."),
            ("B4", "Demonstra maneiras apropriadas ao alimentar-se."),
            ("B5", "Organiza-se, guardando pertences pessoais e limpando o ambiente após as atividades."),
            ("B6", "Demonstra cuidados com a mochila, seu conteúdo e com materiais de sala de aula."),
        ],
    },
    "C": {
        "nome": "Desenvolvimento Cognitivo",
        "itens": [
            ("C1", "Faz triagem e classifica objetos."),
            ("C2", "Demonstra compreensão de conceitos numéricos até 10 (reconhecimento do numeral, contagem em ordem crescente e decrescente, correspondência termo a termo)."),
            ("C3", "Reconhece sequências lógicas e padrões repetitivos."),
            ("C4", "Identifica formas básicas."),
            ("C5", "Identifica cores básicas."),
            ("C6", "Demonstra compreensão dos conceitos estudados em Ciências."),
            ("C7", "Participa dos experimentos de Ciências."),
            ("C8", "Participa dos experimentos de Matemática."),
            ("C9", "Demonstra interesse por literatura, canções e músicas infantis."),
            ("C10", "Demonstra ter cuidado apropriado com os livros, incluindo a habilidade de virar páginas e segurar o livro da maneira correta."),
            ("C11", "Faz associações entre as imagens dos livros e a história lida."),
            ("C12", "Experimenta o uso de palavras em inglês."),
            ("C13", "Expressa-se de maneira criativa."),
            ("C14", "Demonstra interesse em participar de atividades de dramatização com o uso de adereços."),
        ],
    },
    "D": {
        "nome": "Habilidades Motoras",
        "itens": [
            ("D1", "Manuseia apropriadamente tesoura, giz de cera, lápis, pincéis, etc."),
            ("D2", "Demonstra habilidade para montar quebra-cabeças e construir com blocos."),
            ("D3", "Demonstra desenvolvimento da coordenação visomotora."),
            ("D4", "Demonstra interesse em atividades físicas e movimentos corporais."),
            ("D5", "Demonstra ter consciência do próprio corpo e do ambiente físico."),
            ("D6", "Realiza variedade de movimentos corporais como pular, correr, rolar, rastejar, etc."),
        ],
    },
}

DOMAINS_EN = {
    "A": "Social skills",
    "B": "Self-care",
    "C": "Cognitive development",
    "D": "Motor skills",
}

ITEMS_EN = {
    "A1": "Shows respect and interacts appropriately with teachers.",
    "A2": "Shows respect and interacts appropriately with classmates.",
    "A3": "Adapts to new situations and changes.",
    "A4": "Follows rules and routines.",
    "A5": "Waits for their turn in games and interactions with peers.",
    "A6": "Understands the relationship between attitudes and their consequences.",
    "A7": "Cooperates and shares with other children.",
    "B1": "Uses the toilet appropriately.",
    "B2": "Shows appropriate handwashing skills.",
    "B3": "Dresses and puts on shoes appropriately.",
    "B4": "Shows appropriate manners during meals.",
    "B5": "Organizes personal belongings and cleans the space after activities.",
    "B6": "Takes care of the backpack, its contents and classroom materials.",
    "C1": "Sorts and classifies objects.",
    "C2": "Understands numerical concepts up to 10.",
    "C3": "Recognizes logical sequences and repeating patterns.",
    "C4": "Identifies basic shapes.",
    "C5": "Identifies basic colors.",
    "C6": "Shows understanding of Science concepts studied.",
    "C7": "Takes part in Science experiments.",
    "C8": "Takes part in Math activities and experiments.",
    "C9": "Shows interest in literature, songs and children's music.",
    "C10": "Handles books appropriately, turns pages and holds them correctly.",
    "C11": "Makes connections between the images in books and the story read.",
    "C12": "Experiments with using words in English.",
    "C13": "Expresses themselves creatively.",
    "C14": "Shows interest in role-play activities with props.",
    "D1": "Handles scissors, crayons, pencils and brushes appropriately.",
    "D2": "Shows ability to assemble puzzles and build with blocks.",
    "D3": "Shows development of hand–eye coordination.",
    "D4": "Shows interest in physical activities and body movements.",
    "D5": "Shows awareness of their own body and physical environment.",
    "D6": "Performs a variety of movements such as jumping, running, rolling and crawling.",
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
        dom_code = row.get("dominio", "")
        pt = row["dominio_nome"]
        en = DOMAINS_EN.get(dom_code, "")
        if en:
            labels.append(f"{pt}\n({en})")
        else:
            labels.append(pt)
        valores.append(row["media_dominio"])

    num_vars = len(labels)
    angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
    valores += valores[:1]
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))
    ax.plot(angles, valores, linewidth=2, linestyle='solid', color=MAPLE_RED)
    ax.fill(angles, valores, alpha=0.25, color=MAPLE_RED)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_yticks([0, 1, 2, 3])
    ax.set_yticklabels(["0", "1", "2", "3"], fontsize=8)
    ax.set_ylim(0, 3)
    ax.set_title("Perfil por dimensão (escala interna 1–3)", fontsize=12, color=MAPLE_DARK, pad=20)
    return fig


def get_logo_base64():
    if os.path.exists(LOGO_PATH):
        try:
            with open(LOGO_PATH, "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8")
        except Exception:
            return None
    return None

# =========================================================
# TEXTOS BASE (SEM IA) – COMUNICAÇÃO POSITIVA
# =========================================================
def gerar_relatorio_texto_base(idade, sexo, dominio_media, media_geral):
    dominio_media = dominio_media.dropna(subset=["media_dominio"])
    texto = []

    texto.append("Relatório descritivo de desenvolvimento na Educação Infantil")
    texto.append("")
    if idade:
        texto.append(f"Criança avaliada com aproximadamente {idade}.")
    else:
        texto.append("Criança avaliada em processo de desenvolvimento na Educação Infantil.")
    if sexo:
        texto.append(f"Sexo informado: {sexo}.")
    texto.append(
        "Este relatório apresenta, em linguagem simples e objetiva, como a criança tem se desenvolvido "
        "nas habilidades sociais, cognitivas, motoras e de cuidados pessoais, com base em observações "
        "realizadas na rotina escolar."
    )
    texto.append("")

    if pd.isna(media_geral):
        texto.append(
            "Neste momento, existem poucas situações observadas para uma análise global das habilidades, "
            "e já é possível descrever aspectos relevantes percebidos pela professora."
        )
    elif media_geral >= 2.6:
        texto.append(
            "De forma geral, a criança demonstra comportamentos e habilidades bem consolidados para a faixa etária, "
            "participando com interesse das atividades, interagindo com colegas e professores e utilizando com frequência "
            "as habilidades avaliadas."
        )
    elif media_geral >= 1.8:
        texto.append(
            "No conjunto das observações, a criança apresenta um desenvolvimento em andamento, alternando momentos de maior segurança "
            "com outros em que se beneficia de apoio e de oportunidades extras de prática nas diferentes habilidades."
        )
    else:
        texto.append(
            "As observações indicam que a criança se encontra em fase inicial em várias habilidades, "
            "o que inspira um acompanhamento próximo e propostas intencionais que favoreçam o avanço nas dimensões sociais, "
            "cognitivas, motoras e de cuidados pessoais."
        )
    texto.append("")

    if not dominio_media.empty:
        texto.append("A seguir, apresentamos uma análise organizada por áreas de desenvolvimento observadas:")
        texto.append("")

    for _, row in dominio_media.iterrows():
        dom_nome = row["dominio_nome"]
        m = row["media_dominio"]

        texto.append(f"{dom_nome}:")
        if "Habilidades Sociais" in dom_nome:
            if m >= 2.6:
                texto.append(
                    "A criança costuma se relacionar bem com colegas e professores, demonstra respeito nas interações e participa "
                    "das atividades em grupo, conseguindo, na maior parte do tempo, seguir regras, combinar turnos de fala e cooperar "
                    "em jogos e brincadeiras."
                )
            elif m >= 1.8:
                texto.append(
                    "A criança apresenta habilidades sociais em desenvolvimento, alternando momentos de interações muito positivas "
                    "com outros em que se fortalece com intervenções do adulto para lidar com regras, "
                    "esperar a sua vez ou considerar as consequências de suas atitudes."
                )
            else:
                texto.append(
                    "As habilidades sociais da criança encontram-se em fase inicial, com grande potencial de crescimento. Em muitas situações, "
                    "o apoio dos adultos contribui para que siga regras, espere a sua vez e mantenha interações respeitosas com colegas e adultos, "
                    "favorecendo avanços consistentes ao longo do tempo."
                )

        elif "Cuidados Pessoais" in dom_nome:
            if m >= 2.6:
                texto.append(
                    "No que se refere aos cuidados pessoais, a criança costuma usar o toalete de forma adequada, cuida da higiene das mãos, "
                    "alimenta-se com boas maneiras e demonstra organização com pertences, materiais de sala e mochila, condutas importantes "
                    "para sua autonomia no dia a dia."
                )
            elif m >= 1.8:
                texto.append(
                    "A criança demonstra avanços em cuidados pessoais, alternando momentos de maior autonomia com situações em que se beneficia "
                    "de lembretes em relação à higiene, à organização dos pertences e às rotinas de sala."
                )
            else:
                texto.append(
                    "Os cuidados pessoais da criança estão em construção, com muitas oportunidades para desenvolvimento. A cada lembrete sobre higiene, "
                    "modos à mesa, organização de materiais e guarda de pertences, a criança amplia sua autonomia e fortalece hábitos saudáveis."
                )

        elif "Desenvolvimento Cognitivo" in dom_nome:
            if m >= 2.6:
                texto.append(
                    "No campo cognitivo, a criança demonstra boa participação em atividades de Matemática, Ciências, linguagem e expressão, "
                    "mostrando curiosidade, interesse por livros, histórias, experimentos e desafios, além de realizar associações e classificações "
                    "com segurança em muitas situações."
                )
            elif m >= 1.8:
                texto.append(
                    "O desenvolvimento cognitivo da criança está em andamento. Ela participa das propostas, demonstra curiosidade "
                    "e realiza classificações, contagens, identificações de formas, cores e elementos das histórias, "
                    "ao mesmo tempo em que se beneficia de reforço em determinadas situações para consolidar essas habilidades."
                )
            else:
                texto.append(
                    "As habilidades cognitivas avaliadas, como classificação, compreensão de quantidades, identificação de formas e cores, "
                    "participação em experimentos e interesse por histórias, encontram-se em fase inicial de consolidação, "
                    "o que inspira o planejamento de situações contextualizadas e o apoio próximo durante as atividades."
                )

        elif "Habilidades Motoras" in dom_nome:
            if m >= 2.6:
                texto.append(
                    "Em relação às habilidades motoras, a criança apresenta bom controle em atividades de coordenação motora fina e grossa, "
                    "manuseando materiais de escrita, tesoura, blocos e participando de movimentos corporais variados com interesse "
                    "e boa consciência do próprio corpo e do espaço."
                )
            elif m >= 1.8:
                texto.append(
                    "As habilidades motoras estão em construção. Em várias situações, a criança demonstra boa coordenação e, em outras, "
                    "apresenta desafios pontuais no manuseio de materiais finos ou na execução de movimentos mais coordenados, "
                    "beneficiando-se de tempo e oportunidades adicionais para praticar."
                )
            else:
                texto.append(
                    "A coordenação motora, tanto fina quanto grossa, encontra-se em fase inicial de consolidação. "
                    "Tarefas que demandam controle de mãos e dedos e movimentos corporais mais amplos representam oportunidades ricas "
                    "para planejar atividades específicas de fortalecimento motor e percepção corporal."
                )
        else:
            if m >= 2.6:
                texto.append(
                    "Nesta área, a criança apresenta habilidades bem desenvolvidas para a faixa etária, com comportamentos que aparecem de forma frequente e segura."
                )
            elif m >= 1.8:
                texto.append(
                    "Nesta área, as habilidades seguem em desenvolvimento, com avanços importantes e pontos que se fortalecem à medida que a criança vivencia novas situações."
                )
            else:
                texto.append(
                    "Nesta área, a criança se encontra em fase inicial e se beneficia de intervenções frequentes e propostas específicas para avançar."
                )

        texto.append("")

    texto.append(
        "Essas informações formam um retrato em determinado momento, que ajuda a escola e a família a acompanhar "
        "o desenvolvimento da criança e a planejar, em parceria, experiências que valorizem suas conquistas e ofereçam apoio nas áreas "
        "que permanecem em construção."
    )

    return "\n".join(texto)


def gerar_sugestoes_base(dominio_media):
    dominio_media = dominio_media.dropna(subset=["media_dominio"])
    texto = []
    texto.append("Sugestões de atividades em casa para apoiar o desenvolvimento da criança")
    texto.append("")
    texto.append(
        "As sugestões a seguir são voltadas às famílias e indicam maneiras simples de, no dia a dia, fortalecer as habilidades "
        "observadas na escola. As propostas funcionam como oportunidades naturais de conversa, brincadeira e convivência."
    )
    texto.append("")

    if dominio_media.empty:
        texto.append(
            "Neste momento, as observações indicam que as necessidades específicas estão bem contempladas pelas rotinas atuais. "
            "Manter conversas, brincadeiras, momentos de leitura e rotina organizada em casa contribui de forma consistente para o desenvolvimento da criança."
        )
        return "\n".join(texto)

    for _, row in dominio_media.iterrows():
        dom_nome = row["dominio_nome"]

        if "Habilidades Sociais" in dom_nome:
            texto.append(f"{dom_nome} – Como a família pode apoiar em casa:")
            texto.append(
                "Em casa, as habilidades sociais se fortalecem quando a família combina regras simples com a criança, como guardar brinquedos após o uso, "
                "esperar a vez para falar e pedir as coisas com gentileza. Exemplos práticos incluem brincar de jogos de tabuleiro ou cartas em família, "
                "reforçando a ideia de esperar sua vez; incentivar a criança a cumprimentar as pessoas; "
                "conversar sobre situações do dia e ajudá-la a refletir sobre sentimentos próprios e dos colegas."
            )
            texto.append("")

        elif "Cuidados Pessoais" in dom_nome:
            texto.append(f"{dom_nome} – Como a família pode apoiar em casa:")
            texto.append(
                "Os cuidados pessoais se desenvolvem na rotina, quando a criança recebe pequenas responsabilidades compatíveis com a idade. "
                "Exemplos práticos incluem combinar que a criança guarde os próprios brinquedos após brincar; envolvê-la no preparo da mesa, "
                "levando talheres ou guardanapos; observar junto os passos para lavar bem as mãos; "
                "organizar um momento diário para conferir a mochila, ajudando a criança a perceber o que precisa levar ou trazer da escola."
            )
            texto.append("")

        elif "Desenvolvimento Cognitivo" in dom_nome:
            texto.append(f"{dom_nome} – Como a família pode apoiar em casa:")
            texto.append(
                "O desenvolvimento cognitivo ganha força em situações simples do cotidiano. "
                "Exemplos práticos incluem contar objetos em casa, separar brinquedos por cor ou tamanho, "
                "observar juntos elementos da natureza e conversar sobre o que percebem; "
                "reservar um momento para leitura de histórias, perguntando o que a criança entendeu, quem são os personagens e o que ela imagina que acontecerá em seguida. "
                "Cantar músicas, rimas e parlendas também estimula a atenção e a linguagem."
            )
            texto.append("")

        elif "Habilidades Motoras" in dom_nome:
            texto.append(f"{dom_nome} – Como a família pode apoiar em casa:")
            texto.append(
                "As habilidades motoras se desenvolvem com brincadeiras que envolvem movimento e uso das mãos. "
                "Exemplos práticos incluem oferecer tempo para desenhar, pintar, rasgar e colar papéis, montar blocos de encaixe ou quebra-cabeças; "
                "brincar de pular, correr, dançar, equilibrar-se em linhas no chão ou em colchões; "
                "criar pequenos circuitos com almofadas, cadeiras e cordas, sempre com segurança e supervisão."
            )
            texto.append("")
        else:
            texto.append(f"{dom_nome} – Como a família pode apoiar em casa:")
            texto.append(
                "Em casa, momentos de convivência, conversa e brincadeiras que envolvem essa área oferecem ricas oportunidades de aprendizagem. "
                "Sentar-se com a criança, ouvi-la com atenção, propor jogos simples e valorizar suas conquistas favorece muito o desenvolvimento."
            )
            texto.append("")

    return "\n".join(texto)

# =========================================================
# IA – RELATÓRIO, SUGESTÕES, PLANO TURMA (PROMPTS POSITIVOS)
# =========================================================
def gerar_relatorio_ia(idade, sexo, dominio_media, media_geral):
    if not OPENAI_ENABLED:
        return gerar_relatorio_texto_base(idade, sexo, dominio_media, media_geral)

    dominio_media_valid = dominio_media.dropna(subset=["media_dominio"])
    resumo_dim = []
    nomes_dim = []
    for _, row in dominio_media_valid.iterrows():
        resumo_dim.append(f"- {row['dominio_nome']}: valor médio interno {row['media_dominio']:.2f}")
        nomes_dim.append(f"- {row['dominio_nome']}")
    resumo_dim_str = "\n".join(resumo_dim)
    nomes_dim_str = "\n".join(nomes_dim)

    prompt_user = f"""
Você é pedagogo especialista em educação infantil.

Sua tarefa é escrever um RELATÓRIO DESCRITIVO e INTERPRETATIVO, em português do Brasil,
sobre o desenvolvimento de uma criança em processo de alfabetização e educação infantil,
com base em observações organizadas por dimensões.

PÚBLICO-ALVO PRINCIPAL: pais, mães e responsáveis, embora o relatório também possa ser lido pela equipe escolar.
A linguagem deve ser acessível, acolhedora e clara, evitando jargões técnicos excessivos,
sem perder o tom profissional.

Dados contextuais (sem identificação nominal):
- Idade aproximada declarada: {idade if idade else "não informada"}
- Sexo declarado: {sexo if sexo else "não informado"}

Você recebeu, internamente, valores numéricos que indicam a consistência de comportamentos
observados em cada dimensão, em uma escala de 1 a 3 (1 = não aparente, 2 = em desenvolvimento, 3 = bem desenvolvido).
Esses valores servem apenas como referência interna. NÃO escreva números, notas ou médias no relatório.

IMPORTANTE:
- Existe uma categoria interna "Não aplicável" (N/A), usada quando a habilidade ainda não foi apresentada.
- IGNORE completamente essa categoria: não use essas informações na interpretação e NÃO mencione a expressão "não aplicável", "N/A" ou equivalentes no texto.
- Em conformidade com a BNCC, NÃO rotule a criança com “nota” ou conceito numérico e não use termos que soem como aprovação/reprovação.

Dimensões avaliadas e seus níveis internos (para sua referência, NÃO escrever os valores numéricos):
{resumo_dim_str}

Lista das dimensões (use exatamente esses nomes na interpretação):
{nomes_dim_str}

REGRAS IMPORTANTES DO TEXTO (apenas parágrafos, sem títulos formais):
- Escreva um texto corrido, em parágrafos.
- NÃO escreva números de notas, pontuações ou médias numéricas.
- NUNCA use termos como "nota", "pontuação", "média".
- Não faça diagnóstico clínico (não citar TDAH, TEA etc.).
- Use termos como "a criança", "a criança avaliada", "ela" ou "o estudante" (sem nome).
- Utilize comunicação positiva: evite frases na negativa e construa sempre descrições em termos de potencial, avanços e habilidades em desenvolvimento.
- Evite usar a palavra "não" para descrever a criança; prefira expressões como "em desenvolvimento", "em fase inicial", "em processo de consolidação" ou "beneficia-se de apoio".
- Quando precisar indicar algo ainda não consolidado, formule de maneira afirmativa, por exemplo: "a criança está em desenvolvimento nessa habilidade" em vez de "a criança não consegue ainda".

ESTRUTURA DO RELATÓRIO (apenas parágrafos, sem títulos formais):

1. Parágrafo inicial:
   - Visão geral do desenvolvimento da criança, mencionando que o texto
     se baseia em observações do cotidiano escolar.

2. Parágrafo(s) sobre pontos fortes:
   - Destaque em quais dimensões a criança se mostra mais segura.

3. Parágrafo(s) sobre aspectos em desenvolvimento:
   - Descreva em que situações a criança ainda oscila ou se beneficia de apoio,
     em linguagem de "habilidades em construção" e "processos de consolidação".

4. Bloco por dimensão:
   - Para CADA dimensão da lista fornecida, escreva ao menos um parágrafo específico
     descrevendo a criança naquela dimensão (pontos fortes e aspectos em desenvolvimento).

5. Parágrafo(s) finais:
   - Indique, em linguagem acessível, como família e escola podem atuar em parceria
     para apoiar o desenvolvimento da criança, sempre em tom positivo e encorajador.
"""

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Você é um pedagogo especialista em educação infantil e alfabetização, "
                        "com experiência na elaboração de relatórios descritivos para famílias e escolas. "
                        "Você escreve sempre com comunicação positiva, evitando frases na negativa e priorizando descrições de avanços, "
                        "potenciais e habilidades em desenvolvimento."
                    ),
                },
                {"role": "user", "content": prompt_user},
            ],
            temperature=0.65,
            max_tokens=1200,
        )
        return resp.choices[0].message.content.strip()
    except Exception:
        return gerar_relatorio_texto_base(idade, sexo, dominio_media, media_geral)


def gerar_sugestoes_ia(dominio_media):
    if not OPENAI_ENABLED:
        return gerar_sugestoes_base(dominio_media)

    dominio_media_valid = dominio_media.dropna(subset=["media_dominio"])
    resumo_dim = []
    nomes_dim = []
    for _, row in dominio_media_valid.iterrows():
        resumo_dim.append(f"- {row['dominio_nome']}: média interna {row['media_dominio']:.2f}")
        nomes_dim.append(f"- {row['dominio_nome']}")
    resumo_dim_str = "\n".join(resumo_dim)
    nomes_dim_str = "\n".join(nomes_dim)

    prompt_user = f"""
Você é pedagogo especialista em educação infantil.

Com base nas médias internas por dimensão abaixo (escala 1 a 3), elabore SUGESTÕES DE ATIVIDADES
para pais e responsáveis ajudarem a criança EM CASA.

Médias internas por dimensão (para sua referência, NÃO citar números no texto):
{resumo_dim_str}

Lista das dimensões (use exatamente esses nomes como referência):
{nomes_dim_str}

INSTRUÇÕES:
- Escreva em português, com linguagem simples, acolhedora e encorajadora, voltada a famílias.
- NÃO cite números de médias nem use os termos "nota", "pontuação" ou "média".
- Não faça diagnóstico clínico.
- NÃO mencione a existência de itens "não aplicáveis" ou qualquer expressão equivalente.
- Utilize comunicação positiva: evite frases na negativa e foque em como a família pode fortalecer habilidades que estão em desenvolvimento.
- Evite usar a palavra "não" para descrever a criança; prefira expressões como "em desenvolvimento", "em fase inicial", "em processo de consolidação" ou "pode se beneficiar de".
- PARA CADA dimensão da lista acima, produza PELO MENOS UM PARÁGRAFO específico,
  começando o parágrafo pelo nome da dimensão (por exemplo: "Habilidades Sociais: ...").
- Em cada parágrafo, descreva:
  * o foco daquela dimensão (o que ela observa);
  * exemplos práticos de atividades e atitudes que podem ser realizadas em casa, no dia a dia,
    para fortalecer a criança naquela área (ex.: brincadeiras, conversas, pequenas responsabilidades).
- Use frases corridas, sem bullets e sem numeração, sempre valorizando o papel da família como parceira do processo.
"""

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Você gera orientações para famílias sobre como apoiar crianças da educação infantil em casa, "
                        "sempre usando comunicação positiva e destacando avanços e habilidades em desenvolvimento."
                    ),
                },
                {"role": "user", "content": prompt_user},
            ],
            temperature=0.7,
            max_tokens=1200,
        )
        return resp.choices[0].message.content.strip()
    except Exception:
        return gerar_sugestoes_base(dominio_media)


def gerar_plano_turma_base(dominio_media_turma, contexto_str=""):
    dominio_media_turma = dominio_media_turma.dropna(subset=["media_dominio"])
    texto = []
    texto.append("Plano de desenvolvimento global da turma em Educação Infantil")
    texto.append("")
    if contexto_str:
        texto.append(contexto_str)
        texto.append("")

    texto.append(
        "Objetivo geral: apoiar o desenvolvimento da turma nas habilidades sociais, cognitivas, motoras e de cuidados pessoais, "
        "organizando ações coletivas e acompanhando as necessidades individuais, de forma contínua e articulada ao cotidiano escolar."
    )
    texto.append("")
    texto.append(
        "A seguir, apresenta-se uma leitura global da turma com base nas dimensões avaliadas, "
        "com orientações e exemplos práticos para o planejamento pedagógico."
    )
    texto.append("")

    for _, row in dominio_media_turma.iterrows():
        dom_nome = row["dominio_nome"]
        m = row["media_dominio"]

        if "Habilidades Sociais" in dom_nome:
            texto.append(f"{dom_nome}:")
            if m >= 2.5:
                texto.append(
                    "De modo geral, a turma demonstra boas habilidades sociais, com relações positivas entre as crianças "
                    "e respeito às orientações dos adultos."
                )
                texto.append(
                    "Exemplos práticos: manter rodas de conversa com combinados construídos com a turma; propor jogos cooperativos; "
                    "usar histórias e dramatizações para discutir atitudes e consequências no convívio."
                )
            else:
                texto.append(
                    "As habilidades sociais do grupo estão em desenvolvimento, especialmente em situações que envolvem regras, "
                    "espera da vez, resolução de conflitos e cooperação."
                )
                texto.append(
                    "Exemplos práticos: organizar brincadeiras com regras simples e claras; reforçar combinados com apoio visual; "
                    "trabalhar situações-problema em histórias e dramatizações, estimulando as crianças a pensar em soluções coletivas."
                )
            texto.append("")

        elif "Cuidados Pessoais" in dom_nome:
            texto.append(f"{dom_nome}:")
            if m >= 2.5:
                texto.append(
                    "No conjunto, a turma apresenta boa autonomia em cuidados pessoais, como higiene, alimentação e organização de pertences."
                )
                texto.append(
                    "Exemplos práticos: manter rotinas visuais de higiene; propor momentos em que as crianças sejam responsáveis por organizar o espaço; "
                    "reforçar positivamente atitudes de cuidado e responsabilidade com materiais."
                )
            else:
                texto.append(
                    "Os hábitos de higiene, organização de materiais e autonomia em cuidados com o próprio corpo e pertences seguem em construção no grupo."
                )
                texto.append(
                    "Exemplos práticos: construir, com a turma, painéis de rotinas (lavar mãos, guardar materiais, cuidar da mochila); "
                    "criar jogos simbólicos de organização da sala; combinar momentos fixos para verificar materiais antes de ir embora."
                )
            texto.append("")

        elif "Desenvolvimento Cognitivo" in dom_nome:
            texto.append(f"{dom_nome}:")
            if m >= 2.5:
                texto.append(
                    "A turma mostra bom envolvimento em propostas de classificação, contagem, identificação de formas e cores, "
                    "bem como em experiências de Ciências e atividades de linguagem."
                )
                texto.append(
                    "Exemplos práticos: desenvolver projetos de investigação (plantas, animais, fenômenos simples); "
                    "propor jogos com quantidades e comparação; organizar cantinhos de leitura com reconto de histórias e brincadeiras com rimas."
                )
            else:
                texto.append(
                    "O desenvolvimento cognitivo do grupo está em construção, e propostas que conectem Matemática, Ciências e linguagem "
                    "a situações significativas para as crianças tendem a favorecer avanços importantes."
                )
                texto.append(
                    "Exemplos práticos: usar materiais concretos na contagem e classificação; realizar experiências simples com registro coletivo; "
                    "ler e reler histórias, convidando as crianças a comentar imagens, personagens e fatos."
                )
            texto.append("")

        elif "Habilidades Motoras" in dom_nome:
            texto.append(f"{dom_nome}:")
            if m >= 2.5:
                texto.append(
                    "Em média, a turma apresenta boa coordenação motora fina e grossa, participando das propostas que envolvem movimentos e uso de materiais de escrita."
                )
                texto.append(
                    "Exemplos práticos: manter circuitos motores variados; oferecer atividades de recorte, colagem e desenho; "
                    "combinar brincadeiras tradicionais que envolvam correr, pular, rolar e equilibrar-se."
                )
            else:
                texto.append(
                    "As habilidades motoras do grupo seguem em desenvolvimento, especialmente na manipulação de materiais finos e em movimentos coordenados "
                    "do corpo."
                )
                texto.append(
                    "Exemplos práticos: propor exercícios graduais de recorte; usar blocos de construção e encaixe; "
                    "organizar percursos motores simples, aumentando o nível de desafio conforme a turma avança."
                )
            texto.append("")
        else:
            texto.append(f"{dom_nome}:")
            texto.append(
                "Para esta área, recomenda-se planejar sequências didáticas que combinem momentos de exploração livre, atividades dirigidas "
                "e acompanhamento individualizado."
            )
            texto.append("")

    texto.append(
        "Recomenda-se que o planejamento da turma inclua, ao longo da semana, momentos diários de leitura, jogos orais, "
        "atividades de exploração de quantidades, experiências de Ciências, propostas de movimento e situações de cuidado e organização. "
        "O acompanhamento contínuo das crianças, com registros simples dos avanços, permite ajustar as intervenções e fortalecer a parceria com as famílias."
    )

    return "\n".join(texto)


def gerar_plano_turma_ia(dominio_media_turma, contexto_str=""):
    if not OPENAI_ENABLED:
        return gerar_plano_turma_base(dominio_media_turma, contexto_str)

    dominio_media_valid = dominio_media_turma.dropna(subset=["media_dominio"])
    resumo_dim = []
    nomes_dim = []
    for _, row in dominio_media_valid.iterrows():
        resumo_dim.append(f"- {row['dominio_nome']}: média interna {row['media_dominio']:.2f}")
        nomes_dim.append(f"- {row['dominio_nome']}")
    resumo_dim_str = "\n".join(resumo_dim)
    nomes_dim_str = "\n".join(nomes_dim)

    prompt_user = f"""
Você é pedagogo especialista em alfabetização e formação de professores.

Elabore um PLANO DE DESENVOLVIMENTO GLOBAL DA TURMA em educação infantil,
em português do Brasil, com linguagem voltada à professora e à coordenação pedagógica.

Contexto da turma (resumo fornecido pela escola, se houver):
{contexto_str}

Você recebeu médias internas (escala 1 a 3) para cada dimensão, apenas para referência.
NÃO escreva essas médias nem números no texto.

IMPORTANTE:
- Existe, internamente, a categoria "Não aplicável" (N/A), usada quando algumas habilidades ainda não foram apresentadas.
- IGNORE completamente essa categoria, sem mencioná-la no texto.
- Utilize comunicação positiva: evite frases na negativa e apresente os desafios sempre como oportunidades de desenvolvimento.
- Evite usar a palavra "não" para descrever as crianças ou a turma; prefira expressões como "em desenvolvimento", "em fase inicial", "em processo de consolidação" ou "beneficia-se de apoio".

Dimensões avaliadas e níveis internos (para sua referência, NÃO citar valores):
{resumo_dim_str}

Lista das dimensões (use exatamente esses nomes):
{nomes_dim_str}

ESTRUTURA DO TEXTO (apenas parágrafos, sem bullets):

1. Parágrafo(s) iniciais:
   - Síntese do cenário da turma, destacando pontos fortes e desafios entendidos como aspectos em desenvolvimento.
   - Inclua explicitamente um parágrafo iniciado por "Objetivo geral:", descrevendo o objetivo global do plano, em tom propositivo.

2. Bloco por dimensão:
   - Para CADA dimensão da lista, escreva pelo menos um parágrafo:
     * explicando o que aquela dimensão observa na prática da turma;
     * indicando se, de modo geral, o grupo se apresenta mais consolidado ou em desenvolvimento naquela área;
     * sugerindo estratégias pedagógicas concretas para o trabalho coletivo.
   - Na mesma dimensão, inclua um trecho com a expressão "Exemplos práticos:" seguida de 2 a 4 exemplos em frases corridas
     (sem bullets e sem numeração), descrevendo ações possíveis da professora.

3. Parágrafo(s) finais:
   - Organize recomendações globais de planejamento (leitura diária, jogos orais, atividades com quantidades, experiências de Ciências,
     propostas motoras, cuidados pessoais, participação das famílias),
     articulando a visão de turma com acompanhamento individual das crianças que demandam maior apoio, sempre com tom positivo e encorajador.
"""

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Você elabora planos pedagógicos para turmas da educação infantil, com foco em alfabetização e desenvolvimento global, "
                        "sempre usando comunicação positiva e destacando tanto conquistas quanto habilidades em desenvolvimento."
                    ),
                },
                {"role": "user", "content": prompt_user},
            ],
            temperature=0.7,
            max_tokens=1400,
        )
        return resp.choices[0].message.content.strip()
    except Exception:
        return gerar_plano_turma_base(dominio_media_turma, contexto_str)

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
        nome_crianca TEXT,
        idade TEXT,
        sexo TEXT,
        turma TEXT,
        nome_professora TEXT,
        media_geral REAL
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

    cur.execute("PRAGMA table_info(alunos)")
    cols = [row[1] for row in cur.fetchall()]

    if "sexo" not in cols:
        cur.execute("ALTER TABLE alunos ADD COLUMN sexo TEXT")

    if "relatorio_texto" not in cols:
        cur.execute("ALTER TABLE alunos ADD COLUMN relatorio_texto TEXT")

    if "sugestoes_texto" not in cols:
        cur.execute("ALTER TABLE alunos ADD COLUMN sugestoes_texto TEXT")

    if "trimestre" not in cols:
        cur.execute("ALTER TABLE alunos ADD COLUMN trimestre TEXT")

    conn.commit()
    conn.close()


def salvar_no_banco(timestamp_str, nome_crianca, idade, sexo, turma, trimestre,
                    nome_professora, media_geral, relatorio_texto,
                    sugestoes_texto, df_itens, dominio_media):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO alunos (timestamp, nome_crianca, idade, sexo, turma, nome_professora, media_geral, relatorio_texto, sugestoes_texto, trimestre)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (timestamp_str, nome_crianca, idade, sexo, turma, nome_professora,
         float(media_geral) if not pd.isna(media_geral) else None,
         relatorio_texto, sugestoes_texto, trimestre)
    )
    aluno_id = cur.lastrowid

    for _, row in df_itens.iterrows():
        cur.execute(
            """
            INSERT INTO respostas (aluno_id, dominio, dominio_nome, item_codigo, item_texto, resposta)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                aluno_id,
                row["dominio"],
                row["dominio_nome"],
                row["item_codigo"],
                row["item_texto"],
                int(row["resposta"]),
            )
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
            )
        )

    conn.commit()
    conn.close()

# =========================================================
# HTML – CRIANÇA / PROFESSORA
# =========================================================
def gerar_html_impressao(crianca, professora, idade, sexo, turma, trimestre,
                         df_itens, dominio_media, media_geral,
                         relatorio, sugestoes, radar_b64):
    df_tmp = df_itens[["dominio_nome", "item_codigo", "item_texto", "resposta"]].copy()

    def resp_str(v):
        try:
            v = int(v)
        except Exception:
            return ""
        if v == 0:
            return "Não se aplica"
        elif v == 1:
            return "Não aparente"
        elif v == 2:
            return "Em desenvolvimento"
        elif v == 3:
            return "Bem desenvolvido"
        else:
            return ""

    df_tmp["resposta_exibicao"] = df_tmp["resposta"].apply(resp_str)

    tabela_html = df_tmp[[
        "dominio_nome", "item_codigo", "item_texto", "resposta_exibicao"
    ]].rename(columns={
        "dominio_nome": "Dimensão",
        "item_codigo": "Item",
        "item_texto": "Descrição",
        "resposta_exibicao": "Resposta (descrição da escala)",
    }).to_html(index=False, border=0, justify="left")

    relatorio_html = "<br>".join(textwrap.fill(l, 100) for l in relatorio.split("\n"))
    sugestoes_html = "<br>".join(textwrap.fill(l, 100) for l in sugestoes.split("\n"))

    idade_str = idade if idade else "não informada"
    sexo_str = sexo if sexo else "não informado"
    trimestre_str = trimestre if trimestre else "não informado"

    logo_b64 = get_logo_base64()
    if logo_b64:
        logo_tag = f'<img src="data:image/png;base64,{logo_b64}" class="logo" />'
    else:
        logo_tag = ""

    radar_tag = ""
    if radar_b64:
        radar_tag = f'<img src="data:image/png;base64,{radar_b64}" alt="Radar da criança" />'

    html = f"""
    <html>
    <head>
        <meta charset="utf-8">
        <title>Relatório - {crianca}</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 20px;
                color: {MAPLE_DARK};
            }}
            h1, h2, h3 {{
                color: {MAPLE_RED};
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
        <h1>Avaliação de Desenvolvimento (Educação Infantil)</h1>

        <h2>Dados da criança</h2>
        <p><b>Nome:</b> {crianca}</p>
        <p><b>Idade (informada pela professora):</b> {idade_str}</p>
        <p><b>Sexo:</b> {sexo_str}</p>
        <p><b>Turma/Ano:</b> {turma}</p>
        <p><b>Trimestre de referência:</b> {trimestre_str}</p>
        <p><b>Professora responsável:</b> {professora}</p>

        <h3>Gráfico de radar (perfil da criança por dimensão)</h3>
        {radar_tag}

        <h3>Respostas por item (escala descritiva)</h3>
        {tabela_html}

        <h2>Relatório individual</h2>
        <p>{relatorio_html}</p>

        <h2>Sugestões de atividades em casa</h2>
        <p>{sugestoes_html}</p>
    </body>
    </html>
    """
    return html


def gerar_html_relatorio_professora(
    nome_professora,
    turma,
    n_alunos,
    media_geral_prof,
    dominio_media_prof,
    plano_prof,
    radar_b64
):
    dominios_html = dominio_media_prof.to_html(index=False, border=0, justify="left")
    plano_html = "<br>".join(textwrap.fill(l, 100) for l in plano_prof.split("\n"))
    turma_str = turma if turma else "Não especificada"

    logo_b64 = get_logo_base64()
    if logo_b64:
        logo_tag = f'<img src="data:image/png;base64,{logo_b64}" class="logo" />'
    else:
        logo_tag = ""

    html = f"""
    <html>
    <head>
        <meta charset="utf-8">
        <title>Relatório - Professora {nome_professora}</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 20px;
                color: {MAPLE_DARK};
            }}
            h1, h2, h3 {{
                color: {MAPLE_RED};
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
        <h1>Relatório da turma - Professora {nome_professora}</h1>

        <h2>Resumo geral</h2>
        <p><b>Turma:</b> {turma_str}</p>
        <p><b>Número de crianças avaliadas:</b> {n_alunos}</p>
        <p><b>Média geral da turma (escala interna 1–3, desconsiderando N/A):</b> {media_geral_prof:.2f}</p>

        <h2>Médias por dimensão</h2>
        {dominios_html}

        <h2>Gráfico de radar (médias por dimensão)</h2>
        <img src="data:image/png;base64,{radar_b64}" alt="Radar da turma" />

        <h2>Plano de desenvolvimento global da turma</h2>
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


# =========================================================
# FUNÇÃO AJUSTADA – RESET DA AVALIAÇÃO
# =========================================================
def resetar_avaliacao():
    # =============================
    # CAMPOS DE CADASTRO
    # =============================
    st.session_state["nome_crianca"] = ""
    st.session_state["idade_crianca"] = ""
    st.session_state["nome_professora"] = ""
    st.session_state["turma_crianca"] = ""

    # Sexo: volta para a primeira opção do selectbox
    st.session_state["sexo_crianca"] = ""

    # Trimestre: volta para a primeira opção do selectbox
    st.session_state["trimestre_ref"] = ""

    # =============================
    # RESPOSTAS DOS ITENS (RADIOS)
    # =============================
    for dom_code, dom_data in DOMAINS.items():
        for item_code, _ in dom_data["itens"]:
            key = f"{dom_code}_{item_code}"
            # Deixa o radio SEM seleção
            st.session_state[key] = None

    # =============================
    # RESULTADO GERADO
    # =============================
    st.session_state["resultado"] = None


# =========================================================
# LAYOUT – TABS
# =========================================================
tab_avaliar, tab_consulta = st.tabs(["Nova avaliação", "Consultas / Relatórios"])

# ---------------------------------------------------------
# ABA 1 – NOVA AVALIAÇÃO
# ---------------------------------------------------------
with tab_avaliar:
    col_title, col_logo = st.columns([5, 1])
    with col_title:
        st.markdown(
            '<div class="maple-title">Avaliação de Desenvolvimento (4–5 anos)</div>',
            unsafe_allow_html=True
        )
        st.markdown(
            '<div class="maple-subtitle">Escala docente em formato numérico (N/A, 1, 2, 3), organizada em áreas de desenvolvimento. Os resultados numéricos são de uso interno da escola.</div>',
            unsafe_allow_html=True
        )
    with col_logo:
        if os.path.exists(LOGO_PATH):
            st.image(LOGO_PATH, width=120)

    st.write("---")

    st.markdown("### Ações rápidas")
    if st.button("Avaliar novo aluno"):
        resetar_avaliacao()

    st.write("---")

    with st.form("form_avaliacao"):
        col1, col2 = st.columns(2)
        with col1:
            nome_crianca = st.text_input(
                "Nome da criança",
                key="nome_crianca"
            )
            idade = st.text_input(
                "Idade (texto livre, ex.: '5 anos', '4 anos e 6 meses')",
                key="idade_crianca"
            )
        with col2:
            sexo = st.selectbox(
                "Sexo da criança",
                ["Masculino", "Feminino"],
                key="sexo_crianca"
            )
            nome_professora = st.text_input(
                "Nome da professora",
                key="nome_professora"
            )

        col3, col4 = st.columns(2)
        with col3:
            turma = st.text_input(
                "Turma / Ano (opcional)",
                key="turma_crianca"
            )
        with col4:
            trimestre_opcoes = ["1º trimestre", "2º trimestre", "3º trimestre"]
            trimestre = st.selectbox(
                "Trimestre de referência",
                trimestre_opcoes,
                index=0,
                key="trimestre_ref"
            )

        st.markdown("### Escala de avaliação")
        st.markdown(
            "N/A = Não aplicável (habilidade ainda não apresentada) &nbsp;&nbsp;|&nbsp;&nbsp; "
            "1 = Não aparente &nbsp;&nbsp;|&nbsp;&nbsp; "
            "2 = Em desenvolvimento &nbsp;&nbsp;|&nbsp;&nbsp; "
            "3 = Bem desenvolvido",
            unsafe_allow_html=True
        )

        respostas = {}
        for dom_code, dom_data in DOMAINS.items():
            st.markdown(f"#### {dom_data['nome']}")
            if dom_code in DOMAINS_EN:
                st.markdown(
                    f'<div style="font-size:0.85rem; color:#555;"><em>{DOMAINS_EN[dom_code]}</em></div>',
                    unsafe_allow_html=True
                )
            for item_code, item_text in dom_data["itens"]:
                key = f"{dom_code}_{item_code}"

                st.markdown(f"**{item_code} - {item_text}**")
                if item_code in ITEMS_EN:
                    st.markdown(
                        f'<div style="font-size:0.85rem; color:#555; margin-bottom:0.25rem;"><em>{ITEMS_EN[item_code]}</em></div>',
                        unsafe_allow_html=True
                    )

                valor = st.radio(
                    label="Selecione uma opção:",
                    options=[0, 1, 2, 3],
                    format_func=lambda x: LIKERT_OPCOES[x],
                    horizontal=True,
                    key=key,
                    index=None,
                )

                respostas[item_code] = {
                    "dominio": dom_code,
                    "dominio_nome": dom_data["nome"],
                    "item_codigo": item_code,
                    "item_texto": item_text,
                    "resposta": valor,
                }

        enviado = st.form_submit_button("Gerar relatório")

    if enviado:
        if not nome_crianca or not nome_professora:
            st.error("Preencha pelo menos o nome da criança e o nome da professora.")
        else:
            faltantes = [cod for cod, r in respostas.items() if r["resposta"] is None]
            if faltantes:
                st.error("Responda todas as perguntas antes de gerar o relatório.")
            else:
                for r in respostas.values():
                    r["resposta"] = int(r["resposta"])

                df_itens, dominio_media, media_geral = calcular_scores(respostas)

                relatorio_generico = gerar_relatorio_ia(
                    idade,
                    sexo,
                    dominio_media,
                    media_geral,
                )
                relatorio_auto = f"Relatório individual de {nome_crianca}\n\n{relatorio_generico}"

                sugestoes_auto = gerar_sugestoes_ia(dominio_media)

                st.session_state["resultado"] = {
                    "nome_crianca": nome_crianca,
                    "idade": idade,
                    "sexo": sexo,
                    "nome_professora": nome_professora,
                    "turma": turma,
                    "trimestre": trimestre,
                    "df_itens": df_itens,
                    "dominio_media": dominio_media,
                    "media_geral": media_geral,
                    "relatorio": relatorio_auto,
                    "sugestoes": sugestoes_auto,
                }

    if st.session_state.get("resultado") is not None:
        data = st.session_state["resultado"]
        df_itens = data["df_itens"]
        dominio_media = data["dominio_media"]
        media_geral = data["media_geral"]

        st.success("Avaliação processada. Revise o relatório antes de salvar/gerar arquivo.")

        col_a, col_b = st.columns([1, 1])
        with col_a:
            st.markdown("### Médias por dimensão (escala interna 1–3)")
            df_show = dominio_media[["dominio", "dominio_nome", "media_dominio"]].copy()
            df_show["Dimensão"] = df_show.apply(
                lambda row: f"{row['dominio_nome']} ({DOMAINS_EN.get(row['dominio'], '')})"
                if row["dominio"] in DOMAINS_EN else row["dominio_nome"],
                axis=1
            )
            df_show = df_show[["Dimensão", "media_dominio"]]
            df_show = df_show.rename(columns={"media_dominio": "Média (1–3)"})
            st.dataframe(df_show.style.format({"Média (1–3)": "{:.2f}"}))
            if not pd.isna(media_geral):
                st.markdown(
                    f"**Média geral na escala interna (desconsiderando N/A, uso pedagógico):** "
                    f"{media_geral:.2f}"
                )
            else:
                st.markdown(
                    "**Média geral na escala interna:** sem cálculo (muitas respostas N/A)"
                )
        with col_b:
            st.markdown("### Gráfico radar (uso pedagógico interno)")
            fig = plot_radar(dominio_media)
            st.pyplot(fig)

        st.write("---")

        relatorio_editado = st.text_area(
            "Relatório individual da criança (edite se desejar):",
            value=data["relatorio"],
            height=260,
            key="relatorio_editado",
        )

        sugestoes_editadas = st.text_area(
            "Sugestões de atividades em casa para a família (edite se desejar):",
            value=data["sugestoes"],
            height=260,
            key="sugestoes_editadas",
        )

        st.write("---")
        salvar = st.button("Salvar avaliação e gerar relatório para impressão")

        if salvar:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_name = data["nome_crianca"].replace(" ", "_")
            file_base = f"{safe_name}_{timestamp}"

            img_bytes = io.BytesIO()
            fig.savefig(img_bytes, format="png", bbox_inches="tight")
            img_bytes.seek(0)
            radar_b64 = base64.b64encode(img_bytes.getvalue()).decode("utf-8")

            salvar_no_banco(
                timestamp,
                data["nome_crianca"],
                data["idade"],
                data["sexo"],
                data["turma"],
                data["trimestre"],
                data["nome_professora"],
                media_geral,
                relatorio_editado,
                sugestoes_editadas,
                df_itens,
                dominio_media,
            )

            html_relatorio = gerar_html_impressao(
                data["nome_crianca"],
                data["nome_professora"],
                data["idade"],
                data["sexo"],
                data["turma"],
                data["trimestre"],
                df_itens,
                dominio_media,
                media_geral,
                relatorio_editado,
                sugestoes_editadas,
                radar_b64,
            )
            html_path = os.path.join(BASE_DIR, f"{file_base}.html")
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html_relatorio)

            csv_itens_path = os.path.join(BASE_DIR, f"{file_base}_itens.csv")
            df_itens.to_csv(csv_itens_path, index=False, encoding="utf-8-sig")

            csv_dom_path = os.path.join(BASE_DIR, f"{file_base}_dominios.csv")
            dominio_media.to_csv(csv_dom_path, index=False, encoding="utf-8-sig")

            img_path = os.path.join(BASE_DIR, f"{file_base}_radar.png")
            with open(img_path, "wb") as f:
                f.write(img_bytes.getvalue())

            st.success(f"Avaliação salva no banco de dados e arquivos gerados em: {BASE_DIR}")

            st.download_button(
                label="Baixar relatório para impressão (.html)",
                data=html_relatorio,
                file_name=f"relatorio_{safe_name}.html",
                mime="text/html",
            )

            with st.expander("Ver respostas por item (uso interno)"):
                df_show_items = df_itens[["dominio_nome", "item_codigo", "item_texto", "resposta"]].copy()
                df_show_items["Resposta (escala descritiva)"] = df_show_items["resposta"].apply(
                    lambda v: LIKERT_OPCOES.get(int(v), "")
                )
                df_show_items = df_show_items.rename(columns={
                    "dominio_nome": "Dimensão",
                    "item_codigo": "Item",
                    "item_texto": "Descrição",
                })
                st.dataframe(df_show_items[["Dimensão", "Item", "Descrição", "Resposta (escala descritiva)"]])

# ---------------------------------------------------------
# ABA 2 – CONSULTAS
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
            profs = ["(Todos)"] + sorted(df_alunos["nome_professora"].dropna().unique().tolist())
            turmas = ["(Todos)"] + sorted(df_alunos["turma"].dropna().unique().tolist())
            alunos = ["(Todos)"] + sorted(df_alunos["nome_crianca"].dropna().unique().tolist())

            colf1, colf2, colf3 = st.columns(3)
            with colf1:
                filtro_prof = st.selectbox("Filtrar por professora", profs)
            with colf2:
                filtro_turma = st.selectbox("Filtrar por turma", turmas)
            with colf3:
                filtro_aluno = st.selectbox("Filtrar por criança", alunos)

            df_filt = df_alunos.copy()
            if filtro_prof != "(Todos)":
                df_filt = df_filt[df_filt["nome_professora"] == filtro_prof]
            if filtro_turma != "(Todos)":
                df_filt = df_filt[df_filt["turma"] == filtro_turma]
            if filtro_aluno != "(Todos)":
                df_filt = df_filt[df_filt["nome_crianca"] == filtro_aluno]

            st.markdown("### Avaliações encontradas")
            if df_filt.empty:
                st.info("Nenhuma avaliação encontrada para o filtro selecionado.")
            else:
                df_filt_sorted = df_filt.sort_values("timestamp", ascending=False)

                header_cols = st.columns([2, 2, 1.5, 1.2, 2, 1.2, 1, 1, 1])
                headers = ["Data/Hora", "Criança", "Idade", "Sexo", "Turma / Professora", "Trimestre", "Reimprimir", "Editar", "Excluir"]
                for col, h in zip(header_cols, headers):
                    col.markdown(f"**{h}**")

                for _, row in df_filt_sorted.iterrows():
                    c1, c2, c3, c4, c5, c6, c7, c8, c9 = st.columns([2, 2, 1.5, 1.2, 2, 1.2, 1, 1, 1])
                    c1.write(row["timestamp"])
                    c2.write(row["nome_crianca"])
                    c3.write(row["idade"] if row["idade"] else "")
                    c4.write(row["sexo"] if row.get("sexo", "") else "")
                    c5.write(f"{row['turma'] or ''} / {row['nome_professora'] or ''}")
                    c6.write(row["trimestre"] if row.get("trimestre", "") else "")

                    reprint_key = f"reprint_{row['id']}"
                    edit_key = f"edit_{row['id']}"
                    del_key = f"del_{row['id']}"

                    if c7.button("Reimprimir", key=reprint_key):
                        st.session_state["reprint_id"] = row["id"]
                    if c8.button("Editar", key=edit_key):
                        st.session_state["edit_id"] = row["id"]
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

                # Reimpressão
                if st.session_state.get("reprint_id") is not None:
                    selected_id = st.session_state["reprint_id"]
                    conn = sqlite3.connect(DB_PATH)
                    df_res = pd.read_sql_query(
                        "SELECT dominio_nome, item_codigo, item_texto, resposta FROM respostas WHERE aluno_id = ?",
                        conn,
                        params=(selected_id,)
                    )
                    df_dom_aluno = pd.read_sql_query(
                        "SELECT dominio_nome, media_dominio, dominio FROM dominios WHERE aluno_id = ?",
                        conn,
                        params=(selected_id,)
                    )
                    conn.close()

                    df_row = df_alunos[df_alunos["id"] == selected_id]
                    if not df_row.empty and not df_res.empty and not df_dom_aluno.empty:
                        row_aluno = df_row.iloc[0]
                        dominio_media_aluno = df_dom_aluno.rename(
                            columns={"dominio_nome": "dominio_nome", "media_dominio": "media_dominio"}
                        )

                        relatorio_texto_salvo = row_aluno["relatorio_texto"] if row_aluno["relatorio_texto"] else ""
                        sugestoes_texto_salvo = row_aluno["sugestoes_texto"] if row_aluno["sugestoes_texto"] else ""

                        fig_aluno = plot_radar(dominio_media_aluno)
                        img_bytes_aluno = io.BytesIO()
                        fig_aluno.savefig(img_bytes_aluno, format="png", bbox_inches="tight")
                        img_bytes_aluno.seek(0)
                        radar_b64_aluno = base64.b64encode(img_bytes_aluno.getvalue()).decode("utf-8")

                        html_sel = gerar_html_impressao(
                            row_aluno["nome_crianca"],
                            row_aluno["nome_professora"],
                            row_aluno["idade"],
                            row_aluno["sexo"],
                            row_aluno["turma"],
                            row_aluno["trimestre"],
                            df_res,
                            dominio_media_aluno,
                            row_aluno["media_geral"],
                            relatorio_texto_salvo,
                            sugestoes_texto_salvo,
                            radar_b64_aluno,
                        )

                        st.download_button(
                            label="Baixar relatório da criança selecionada (.html)",
                            data=html_sel,
                            file_name=f"relatorio_{row_aluno['nome_crianca'].replace(' ', '_')}.html",
                            mime="text/html",
                        )
                    else:
                        st.info("Não há dados detalhados suficientes para reimprimir essa avaliação.")

                # Edição
                if st.session_state.get("edit_id") is not None:
                    edit_id = st.session_state["edit_id"]
                    df_edit = df_alunos[df_alunos["id"] == edit_id]
                    if df_edit.empty:
                        st.session_state["edit_id"] = None
                    else:
                        row_edit = df_edit.iloc[0]

                        conn = sqlite3.connect(DB_PATH)
                        df_resp_edit = pd.read_sql_query(
                            "SELECT dominio, dominio_nome, item_codigo, item_texto, resposta FROM respostas WHERE aluno_id = ?",
                            conn,
                            params=(edit_id,)
                        )
                        conn.close()

                        st.write("---")
                        st.markdown("### Editar avaliação selecionada")

                        with st.form("form_editar_avaliacao"):
                            col_ed1, col_ed2 = st.columns(2)
                            with col_ed1:
                                novo_nome = st.text_input("Nome da criança", value=row_edit["nome_crianca"] or "")
                                nova_idade = st.text_input("Idade (texto livre)", value=row_edit["idade"] or "")
                            with col_ed2:
                                novo_sexo = st.selectbox(
                                    "Sexo da criança",
                                    ["Masculino", "Feminino"],
                                    index=0 if (row_edit["sexo"] or "Masculino") == "Masculino" else 1,
                                )
                                nova_prof = st.text_input("Nome da professora", value=row_edit["nome_professora"] or "")

                            col_ed3, col_ed4 = st.columns(2)
                            with col_ed3:
                                nova_turma = st.text_input("Turma / Ano", value=row_edit["turma"] or "")
                            with col_ed4:
                                trimestre_opcoes_ed = ["1º trimestre", "2º trimestre", "3º trimestre"]
                                valor_tri_atual = row_edit["trimestre"] if row_edit["trimestre"] else "1º trimestre"
                                idx_tri = (
                                    trimestre_opcoes_ed.index(valor_tri_atual)
                                    if valor_tri_atual in trimestre_opcoes_ed
                                    else 0
                                )
                                novo_trimestre = st.selectbox(
                                    "Trimestre de referência",
                                    trimestre_opcoes_ed,
                                    index=idx_tri,
                                )

                            novo_relatorio_texto = st.text_area(
                                "Relatório individual da criança",
                                value=row_edit["relatorio_texto"] or "",
                                height=260,
                            )
                            novas_sugestoes_texto = st.text_area(
                                "Sugestões de atividades em casa para a família",
                                value=row_edit["sugestoes_texto"] or "",
                                height=260,
                            )

                            st.markdown("#### Ajustar respostas das perguntas (escala N/A, 1, 2, 3)")
                            st.markdown(
                                "N/A = Não aplicável (habilidade ainda não apresentada) &nbsp;&nbsp;|&nbsp;&nbsp; "
                                "1 = Não aparente &nbsp;&nbsp;|&nbsp;&nbsp; "
                                "2 = Em desenvolvimento &nbsp;&nbsp;|&nbsp;&nbsp; "
                                "3 = Bem desenvolvido",
                                unsafe_allow_html=True
                            )

                            novas_respostas = {}

                            for dom_code, dom_data in DOMAINS.items():
                                st.markdown(f"##### {dom_data['nome']}")
                                for item_code, item_text in dom_data["itens"]:
                                    row_item = df_resp_edit[df_resp_edit["item_codigo"] == item_code]
                                    if not row_item.empty:
                                        valor_atual = int(row_item.iloc[0]["resposta"])
                                    else:
                                        valor_atual = 2
                                    key_edit = f"edit_{edit_id}_{item_code}"
                                    novo_valor = st.radio(
                                        label=f"{item_code} - {item_text}",
                                        options=[0, 1, 2, 3],
                                        format_func=lambda x: LIKERT_OPCOES[x],
                                        index=[0, 1, 2, 3].index(valor_atual),
                                        horizontal=True,
                                        key=key_edit,
                                    )
                                    novas_respostas[item_code] = {
                                        "dominio": dom_code,
                                        "dominio_nome": dom_data["nome"],
                                        "item_codigo": item_code,
                                        "item_texto": item_text,
                                        "resposta": int(novo_valor),
                                    }

                            salvar_edicao = st.form_submit_button("Salvar alterações")

                        if salvar_edicao:
                            df_itens_novo, dominio_media_novo, media_geral_novo = calcular_scores(novas_respostas)

                            conn = sqlite3.connect(DB_PATH)
                            cur = conn.cursor()

                            cur.execute(
                                """
                                UPDATE alunos
                                SET nome_crianca = ?, idade = ?, sexo = ?, turma = ?, nome_professora = ?,
                                    relatorio_texto = ?, sugestoes_texto = ?, media_geral = ?, trimestre = ?
                                WHERE id = ?
                                """,
                                (
                                    novo_nome,
                                    nova_idade,
                                    novo_sexo,
                                    nova_turma,
                                    nova_prof,
                                    novo_relatorio_texto,
                                    novas_sugestoes_texto,
                                    float(media_geral_novo) if not pd.isna(media_geral_novo) else None,
                                    novo_trimestre,
                                    edit_id,
                                )
                            )

                            cur.execute("DELETE FROM respostas WHERE aluno_id = ?", (edit_id,))
                            cur.execute("DELETE FROM dominios WHERE aluno_id = ?", (edit_id,))

                            for _, row_it in df_itens_novo.iterrows():
                                cur.execute(
                                    """
                                    INSERT INTO respostas (aluno_id, dominio, dominio_nome, item_codigo, item_texto, resposta)
                                    VALUES (?, ?, ?, ?, ?, ?)
                                    """,
                                    (
                                        edit_id,
                                        row_it["dominio"],
                                        row_it["dominio_nome"],
                                        row_it["item_codigo"],
                                        row_it["item_texto"],
                                        int(row_it["resposta"]),
                                    )
                                )

                            for _, row_dm in dominio_media_novo.iterrows():
                                cur.execute(
                                    """
                                    INSERT INTO dominios (aluno_id, dominio, dominio_nome, media_dominio)
                                    VALUES (?, ?, ?, ?)
                                    """,
                                    (
                                        edit_id,
                                        row_dm["dominio"],
                                        row_dm["dominio_nome"],
                                        float(row_dm["media_dominio"]) if not pd.isna(row_dm["media_dominio"]) else None,
                                    )
                                )

                            conn.commit()
                            conn.close()
                            st.session_state["edit_id"] = None
                            st.success("Avaliação atualizada com sucesso.")
                            st.rerun()

            # Visões consolidadas / plano professora
            if not df_filt.empty:
                df_merged = df_dom.merge(
                    df_filt[["id", "turma", "nome_professora", "nome_crianca"]],
                    left_on="aluno_id",
                    right_on="id",
                    how="inner"
                )

                if df_merged.empty:
                    st.info("Nenhum dado detalhado para o filtro selecionado.")
                else:
                    st.markdown("### Visão macro por turma e por professora")

                    colm1, colm2 = st.columns(2)
                    with colm1:
                        st.markdown("**Médias por turma (todas as dimensões)**")
                        macro_turma = (
                            df_merged.groupby("turma")["media_dominio"]
                            .mean()
                            .reset_index()
                            .rename(columns={"turma": "Turma", "media_dominio": "Média global (1–3)"})
                        )
                        st.dataframe(macro_turma.style.format({"Média global (1–3)": "{:.2f}"}))

                    with colm2:
                        st.markdown("**Médias por professora (todas as dimensões)**")
                        macro_prof = (
                            df_merged.groupby("nome_professora")["media_dominio"]
                            .mean()
                            .reset_index()
                            .rename(columns={"nome_professora": "Professora", "media_dominio": "Média global (1–3)"})
                        )
                        st.dataframe(macro_prof.style.format({"Média global (1–3)": "{:.2f}"}))

                    st.markdown("### Relatório consolidado por dimensão (recorte atual)")
                    dim_consol = (
                        df_merged.groupby("dominio_nome")["media_dominio"]
                        .mean()
                        .reset_index()
                        .rename(columns={"dominio_nome": "Dimensão", "media_dominio": "Média (1–3)"})
                    )
                    st.dataframe(dim_consol.style.format({"Média (1–3)": "{:.2f}"}))

                    st.download_button(
                        label="Baixar consolidado em CSV (dimensões - recorte atual)",
                        data=dim_consol.to_csv(index=False, encoding="utf-8-sig"),
                        file_name="consolidado_turma_dimensoes.csv",
                        mime="text/csv",
                    )

                    st.write("---")
                    st.markdown("### Relatório individualizado por professora")

                    if st.button("Gerar relatório individualizado da professora"):
                        if filtro_prof == "(Todos)":
                            st.warning("Selecione uma professora específica no filtro para gerar o relatório individualizado.")
                        else:
                            df_alunos_prof = df_alunos[df_alunos["nome_professora"] == filtro_prof]
                            if filtro_turma != "(Todos)":
                                df_alunos_prof = df_alunos_prof[df_alunos_prof["turma"] == filtro_turma]

                            if df_alunos_prof.empty:
                                st.info("Não há avaliações registradas para essa professora com o filtro atual.")
                            else:
                                df_prof_merged = df_dom.merge(
                                    df_alunos_prof[["id", "turma", "nome_professora", "nome_crianca"]],
                                    left_on="aluno_id",
                                    right_on="id",
                                    how="inner"
                                )

                                if df_prof_merged.empty:
                                    st.info("Não há dados detalhados para essa professora com o filtro atual.")
                                else:
                                    n_alunos_prof = df_alunos_prof.shape[0]
                                    media_geral_prof = df_alunos_prof["media_geral"].mean()

                                    st.markdown(f"**Professora:** {filtro_prof}")
                                    if filtro_turma != "(Todos)":
                                        st.markdown(f"**Turma:** {filtro_turma}")
                                        turma_prof_str = filtro_turma
                                    else:
                                        turma_prof_str = ""
                                    st.markdown(f"**Número de crianças avaliadas:** {n_alunos_prof}")
                                    if not pd.isna(media_geral_prof):
                                        st.markdown(f"**Média geral da turma (escala 1–3, desconsiderando N/A):** {media_geral_prof:.2f}")
                                    else:
                                        st.markdown("**Média geral da turma:** sem cálculo (muitas respostas N/A)")

                                    dominio_media_prof = (
                                        df_prof_merged.groupby("dominio_nome")["media_dominio"]
                                        .mean()
                                        .reset_index()
                                        .rename(columns={"dominio_nome": "Dimensão", "media_dominio": "Média (1–3)"})
                                    )

                                    colp1, colp2 = st.columns(2)
                                    with colp1:
                                        st.markdown("#### Médias por dimensão (turma da professora)")
                                        st.dataframe(
                                            dominio_media_prof.style.format({"Média (1–3)": "{:.2f}"}),
                                        )

                                    with colp2:
                                        st.markdown("#### Gráfico radar da turma da professora")
                                        dominio_media_prof_plot = dominio_media_prof.rename(
                                            columns={"Dimensão": "dominio_nome", "Média (1–3)": "media_dominio"}
                                        )
                                        if "dominio" not in dominio_media_prof_plot.columns:
                                            dominio_media_prof_plot["dominio"] = ""
                                        fig_prof = plot_radar(dominio_media_prof_plot)
                                        st.pyplot(fig_prof)

                                    dominio_media_prof_base = dominio_media_prof.rename(
                                        columns={"Dimensão": "dominio_nome", "Média (1–3)": "media_dominio"}
                                    )
                                    contexto_parts_prof = [f"Relatório individualizado da professora {filtro_prof}."]
                                    if turma_prof_str:
                                        contexto_parts_prof.append(f"Turma: {turma_prof_str}.")
                                    contexto_parts_prof.append(f"Número de crianças avaliadas: {n_alunos_prof}.")
                                    contexto_prof_str = " ".join(contexto_parts_prof)

                                    plano_prof = gerar_plano_turma_ia(dominio_media_prof_base, contexto_prof_str)

                                    plano_prof_editado = st.text_area(
                                        "Plano de desenvolvimento global da turma da professora (edite se desejar):",
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
                                        turma=turma_prof_str,
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
