import streamlit as st
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
import requests
import json
import os
import time

load_dotenv()
API_KEY = "AIzaSyB1BA-t7-L5XPuPqw3-LyY5fukjUH0M0yM"
GOOGLE_URL = "https://script.google.com/macros/s/AKfycbxXNgiEuXcCh962TMSMl72fCfNE0mxnLQvz_aYuMPelgCun1sfFT8-wZXSeYtAqGasmaQ/exec"
FOLDER_URL = "https://drive.google.com/drive/u/0/folders/1Z0CKEqwS80c9BFODVcsm9cYrZmK4ol5M"


# Template do JSON
JSON_TEMPLATE = {
    "data": {
        "nome do paciente": "",
        "idade": "",
        "sexo": "",
        "etnia": "",
        "procedente": "",
        "data de nascimento": "",
        "prontuario": "",
        "prec cp": "",
        "contato": "",
        "posto e graduacao": "",
        "queixa principal": "",
        "hda": "",
        "retorno1": {"data": "", "info": ""},
        "retorno2": {"data": "", "info": ""},
        "retorno3": {"data": "", "info": ""},
        "antecedentes pessoais": {
            "alergias": [],
            "comorbidades": [],
            "habitos e vicios": [],
            "cirurgias previas": "",
            "medicamentos em uso continuo": [],
        },
        "exame fisico geral": {"peso": "", "altura": "", "info1": "", "info2": ""},
        "exame neurologico": {"info1": "", "info2": "", "info3": ""},
        "exames complementares": [{"tipo": "", "data": "", "laudo": ""}],
    }
}


def chamar_gemini(historia: str, tentativas=3) -> dict:
    prompt = f"""
Você é um extrator de informações.
Receba o seguinte texto de paciente e preencha o JSON fornecido.
Se a informação não estiver no texto, mantenha o campo vazio. Não faça nenhuma suposição nem remova nenhuma informação.

Texto:
{historia}

JSON base:
{json.dumps(JSON_TEMPLATE, indent=2, ensure_ascii=False)}

Responda SOMENTE com o JSON preenchido. Valores de peso e altura devem vir em quilograma e metros. 
Na seção de antecedentes pessoais os campos não listados devem ser completados com a palavra "nega".
"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={API_KEY}"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    headers = {"Content-Type": "application/json"}

    for tentativa in range(1, tentativas + 1):
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        data = response.json()

        if "error" in data:
            if data["error"].get("code") == 503:
                st.warning(
                    f"⚠️ Gemini sobrecarregado. Tentando novamente ({tentativa}/{tentativas})..."
                )
                time.sleep(3)  # aguarda 3 segundos
                continue
            else:
                st.error("❌ Erro na API Gemini")
                st.json(data)
                return {}

        try:
            resposta = data["candidates"][0]["content"]["parts"][0]["text"].strip()
            resposta = resposta.replace("```json", "").replace("```", "").strip()
            return json.loads(resposta)
        except Exception as e:
            st.error("⚠️ Erro ao parsear JSON retornado pelo Gemini.")
            st.json(data)
            raise e

    st.error("🚨 Não foi possível obter resposta do Gemini após várias tentativas.")
    return {}


# ---------------- layout: 3 colunas (esquerda, botão, direita) -------------
# CSS para aumentar a largura do botão
st.markdown(
    """
    <style>
    div.stButton > button:first-child {
        width: 700px;  /* ajuste para a largura desejada */
        height: 50px;  /* opcional: altura maior */

    }
    </style>
    """,
    unsafe_allow_html=True,
)
st.header(
    f"Slides no Google Drive: [Abrir pasta]({FOLDER_URL})"
)

# Inicializa se não existir
if "json_to_send" not in st.session_state:
    st.session_state["json_to_send"] = {}

# Botão único para processar e gerar slide
if st.button("Gerar Slide", key="btn_gerar_slide"):
    if not st.session_state.get("historia", "").strip():
        st.warning("Cole a história antes de gerar os slides.")
    else:
        with st.spinner("🔎 Processando dados e gerando slide..."):
            try:
                # Passo 1: processar com Gemini
                resultado = chamar_gemini(st.session_state["historia"])
                if not resultado:
                    st.error("Não foi possível obter dados estruturados do Gemini.")
                else:
                    # Salva estados
                    st.session_state["json_editavel"] = json.dumps(
                        resultado, indent=2, ensure_ascii=False
                    )
                    st.session_state["json_to_send"] = resultado

                    # Passo 2: enviar para o Apps Script
                    url = GOOGLE_URL
                    print(url)

                    # print(
                    #     "Enviando para o Apps Script:",
                    #     json.dumps(resultado, indent=2, ensure_ascii=False),
                    # )

                    response = requests.post(url, json=resultado, timeout=10)
                    response.raise_for_status()

                    st.success("✅ Slide gerado com sucesso! Verifique a pasta Automações.")
                    print(json.dumps(response.json(), indent=2, ensure_ascii=False))

            except Exception as e:
                st.error(f"Erro durante o processamento/envio: {e}")


# col_left, col_right = st.columns([6, 6])
# # with col_left:

# --- coluna esquerda: história clínica (editable) ---
st.subheader("História Clínica")
historia = st.text_area(
    "Cole abaixo a história do paciente.",
    placeholder="Cole a história clínica aqui...",
    height=400,
    key="historia",  # mantém o valor em session_state
)


# # --- coluna direita: JSON (inicia com template; depois mostra o resultado) ---
# with col_right:
#     st.subheader("Dado estruturado")

#     # key = "json_editavel" permite que a área preserve edições do usuário
#     json_editado = st.text_area(
#         "Informações detalhadas sobre o paciente (JSON)",
#         height=400,
#         key="json_editavel",
#         placeholder=json.dumps(JSON_TEMPLATE, indent=2, ensure_ascii=False),
#     )
