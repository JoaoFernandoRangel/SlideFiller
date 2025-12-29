import streamlit as st
import requests
import json
import time
import os
from openai import OpenAI

#First commit on develop

# ---------------- CONFIGURAÇÕES ---------------- #
USE_GEMINI = False  # <<<<< Mude para True se quiser usar o Gemini
if USE_GEMINI:
    modelo_IA = "Gemini free tier"
else:
    modelo_IA = "gpt-4o"

# Pega chaves do Streamlit Secrets
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
MAIN_API_KEY = st.secrets["MAIN_API_KEY"]
RESERVE_API_KEY = st.secrets["RESERVE_API_KEY"]
GOOGLE_URL = st.secrets["GOOGLE_URL"]
FOLDER_URL = st.secrets["FOLDER_URL"]

# OPENAI_API_KEY = ""
# MAIN_API_KEY = ""
# RESERVE_API_KEY = ""
# GOOGLE_URL = ""
# FOLDER_URL = ""

# Cria cliente OpenAI
client = OpenAI(api_key=OPENAI_API_KEY)

# Template base
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


# ---------------- FUNÇÕES ---------------- #
def chamar_openai(historia: str, tentativas=3) -> dict:
    prompt = f"""
Você é um extrator de informações médicas.  
Sua tarefa é preencher o JSON fornecido com base no texto do paciente.  

Instruções:  
1. Se a informação não estiver no texto → deixe vazio.  
2. Não faça suposições nem remova informações.  
3. Peso em quilogramas, altura em metros. Os valores serão usados em contas.
4. Pode inferir sexo pelo nome.  
5. Em "antecedentes pessoais", campos não citados → preencher com "Nega".
6. Se encontrar a sigla PO, ela quer dizer Pós Operatório, o nome ao lado deve ser listado em cirurgias.
7. Corrija letras maiúsculas e formate corretamente.
8. Responda apenas com o JSON.
Texto do paciente: 
{historia}

JSON base:
{json.dumps(JSON_TEMPLATE, indent=2, ensure_ascii=False)}

Responda SOMENTE com o JSON preenchido. 
"""

    for tentativa in range(1, tentativas + 1):
        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "Você é um assistente útil e preciso.",
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=1000,
            )

            resposta = response.choices[0].message.content.strip()
            resposta = resposta.replace("```json", "").replace("```", "").strip()
            return json.loads(resposta)

        except json.JSONDecodeError:
            st.warning(f"⚠️ Erro ao parsear JSON. Tentativa {tentativa}/{tentativas}...")
            time.sleep(2)
        except Exception as e:
            st.error(f"❌ Erro na API OpenAI: {e}")
            time.sleep(2)

    st.error("🚨 Não foi possível obter resposta da OpenAI após várias tentativas.")
    return {}


def chamar_gemini(historia: str, questionario: bool, tentativas=3) -> dict:
    std_prompt = f"""
Você é um extrator de informações médicas.  
Sua tarefa é preencher o JSON fornecido com base no texto do paciente.  

Instruções:  
1. Se a informação não estiver no texto → deixe vazio.  
2. Não faça suposições nem remova informações.  
3. Peso em quilogramas, altura em metros. Retorne somente os números, eles serão usados para cálculos, não adicione as unidades.  
4. Pode inferir sexo pelo nome.  
5. Em "antecedentes pessoais", campos não citados → preencher com "Nega".
6. Se encontrar a sigla PO, ela quer dizer Pós Operatório, o nome ao lado deve ser listado em cirurgias.
7. Corrija letras maiúsculas e formate corretamente.
8. Responda apenas com o JSON.
9. Não remova nenhuma parte do texto, 
Texto do paciente:  
{historia}  
JSON base:  
{json.dumps(JSON_TEMPLATE, indent=2, ensure_ascii=False)}  
"""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={RESERVE_API_KEY}"
    headers = {"Content-Type": "application/json"}
    payload = {"contents": [{"parts": [{"text": std_prompt}]}]}

    for tentativa in range(1, tentativas + 1):
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        data = response.json()

        if "error" in data:
            if data["error"].get("code") == 503:
                st.warning(
                    f"⚠️ Gemini sobrecarregado. Tentando novamente ({tentativa}/{tentativas})..."
                )
                time.sleep(3)
                continue
            else:
                st.error("❌ Erro na API Gemini (extração de JSON)")
                st.json(data)
                return {}

        try:
            resposta = data["candidates"][0]["content"]["parts"][0]["text"].strip()
            resposta = resposta.replace("```json", "").replace("```", "").strip()
            json_resp = json.loads(resposta)
            break
        except Exception:
            st.error("⚠️ Erro ao parsear JSON retornado pelo Gemini.")
            st.json(data)
            return {}

    # Reescrever HDA se for questionário
    if questionario:
        quest_prompt = f"""
        Você é um médico neurocirurgião. 
        Reescreva a história abaixo usando linguagem técnica, de forma breve e objetiva.
        História:
        {json_resp['data']["hda"]}
        """

        payload2 = {"contents": [{"parts": [{"text": quest_prompt}]}]}
        for tentativa in range(1, tentativas + 1):
            response2 = requests.post(url, headers=headers, data=json.dumps(payload2))
            data2 = response2.json()
            try:
                reescrita = data2["candidates"][0]["content"]["parts"][0][
                    "text"
                ].strip()
                json_resp["data"]["hda"] = reescrita
                break
            except Exception:
                st.warning("⚠️ Erro ao reescrever HDA.")
                continue

    return json_resp


def processa_questionario_e_historia(historia):
    tentativas = 3
    prompt = f"""
    Você é um extrator de informações médicas.  
    Sua tarefa é preencher o JSON fornecido com base no texto do paciente. 
    O texto é uma história que foi escrita por um colega médico acompanhado de um questionário preenchido pelo paciente.

    Instruções:  
    1. Se a informação não estiver no texto → deixe vazio.  
    2. Não faça suposições nem remova informações.  
    3. Peso em quilogramas, altura em metros. Retorne somente os números, eles serão usados para cálculos, não adicione as unidades.  
    4. Pode inferir sexo pelo nome.  
    5. Em "antecedentes pessoais", campos não citados → preencher com "Nega".
    6. Se encontrar a sigla PO, ela quer dizer Pós Operatório, o nome ao lado deve ser listado em cirurgias.
    7. Corrija letras maiúsculas e formate corretamente.
    8. Responda apenas com o JSON.
    9. Não remova nenhuma parte do texto, 
    Texto do paciente:  
    {historia}  
    JSON base:  
    {json.dumps(JSON_TEMPLATE, indent=2, ensure_ascii=False)}  
    """
    if USE_GEMINI:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={RESERVE_API_KEY}"
        headers = {"Content-Type": "application/json"}
        payload = {"contents": [{"parts": [{"text": prompt}]}]}

        for tentativa in range(1, tentativas + 1):
            response = requests.post(url, headers=headers, data=json.dumps(payload))
            data = response.json()

            if "error" in data:
                if data["error"].get("code") == 503:
                    st.warning(
                        f"⚠️ Gemini sobrecarregado. Tentando novamente ({tentativa}/{tentativas})..."
                    )
                    time.sleep(3)
                    continue
                else:
                    st.error("❌ Erro na API Gemini (extração de JSON)")
                    st.json(data)
                    return {}

            try:
                resposta = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                resposta = resposta.replace("```json", "").replace("```", "").strip()
                json_resp = json.loads(resposta)
                break
            except Exception:
                st.error("⚠️ Erro ao parsear JSON retornado pelo Gemini.")
                st.json(data)
                return {}
    else:
        for tentativa in range(1, tentativas + 1):
            try:
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {
                            "role": "system",
                            "content": "Você é um assistente útil e preciso.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens=1000,
                )

                resposta = response.choices[0].message.content.strip()
                resposta = resposta.replace("```json", "").replace("```", "").strip()
                return json.loads(resposta)

            except json.JSONDecodeError:
                st.warning(
                    f"⚠️ Erro ao parsear JSON. Tentativa {tentativa}/{tentativas}..."
                )
                time.sleep(2)
            except Exception as e:
                st.error(f"❌ Erro na API OpenAI: {e}")
                time.sleep(2)

        st.error("🚨 Não foi possível obter resposta da OpenAI após várias tentativas.")
        return {}


# Função unificada
def processar_texto(historia, questionario, isMixed):
    if isMixed:
        return processa_questionario_e_historia(historia)
    if USE_GEMINI:
        st.info("🧠 Usando modelo: **Gemini**")
        return chamar_gemini(historia, questionario)
    else:
        st.info("💡 Usando modelo: **OpenAI GPT**")
        return chamar_openai(historia)


# ---------------- INTERFACE ---------------- #
st.markdown(
    """
    <style>
    div.stButton > button:first-child {
        width: 700px;
        height: 50px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.header(f"Slides no Google Drive: [Abrir pasta]({FOLDER_URL})")
if st.button("Gerar Slide", key="btn_gerar_slide"):
    if not st.session_state.get("historia", "").strip():
        st.warning("Cole a história antes de gerar os slides.")
    else:
        with st.spinner("🔎 Processando dados e gerando slide..."):
            try:
                resultado = processar_texto( 
                    st.session_state["historia"],
                    st.session_state["is_questionario"],
                    st.session_state["is_mixed"],
                )
                if not resultado:
                    st.error("Não foi possível obter dados estruturados.")
                else:
                    st.session_state["json_editavel"] = json.dumps(
                        resultado, indent=2, ensure_ascii=False
                    )
                    st.session_state["json_to_send"] = resultado
                    response = requests.post(GOOGLE_URL, json=resultado, timeout=10)
                    response.raise_for_status()
                    st.success(
                        "✅ Slide gerado com sucesso! Verifique a pasta Automações."
                    )
            except Exception as e:
                st.error(f"Erro durante o processamento/envio: {e}")
st.checkbox("Sua história é um questionário?", value=False, key="is_questionario")
st.checkbox(
    "Sua história é uma mistura de questionário e história normal?",
    value=False,
    key="is_mixed",
)

if "json_to_send" not in st.session_state:
    st.session_state["json_to_send"] = {}

st.text(f"Esse site usa o modelo: {modelo_IA}")

st.subheader("História Clínica")
historia = st.text_area(
    "Cole abaixo a história do paciente.",
    placeholder="Cole a história clínica aqui...",
    height=400,
    key="historia",
)
