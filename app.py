import streamlit as st
import requests
import json
import time


MAIN_API_KEY = st.secrets["MAIN_API_KEY"]
RESERVE_API_KEY = st.secrets["RESERVE_API_KEY"]
GOOGLE_URL = st.secrets["GOOGLE_URL"]
FOLDER_URL = st.secrets["FOLDER_URL"]

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


def printValueOnTerminal(value):
    print(f"Valor impresso: {value}")


def chamar_gemini(historia: str, questionario: bool, tentativas=3) -> dict:
    std_prompt = f"""
Você é um extrator de informações médicas.  
Sua tarefa é preencher o JSON fornecido com base no texto do paciente.  

Instruções:  
1. Se a informação não estiver no texto → deixe vazio.  
2. Não faça suposições nem remova informações.  
3. Peso em quilogramas, altura em metros.  
4. Pode inferir sexo pelo nome.  
5. Em "antecedentes pessoais", campos não citados → preencher com "Nega".
6. Se encontrar a sigla PO, ela quer dizer Pós Operatório, o nome ao lado deve ser listado em cirurgias.
7. Corrija as letras maiúsculas dos textos. Formate-os corretamente.
8. Responda apenas com o JSON, sem explicações.
Texto do paciente:  
{historia}  
JSON base:  
{json.dumps(JSON_TEMPLATE, indent=2, ensure_ascii=False)}  

Responda apenas com o JSON preenchido.
"""
    print(f"\n\nValor questionário: {questionario}\n\n")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={RESERVE_API_KEY}"
    headers = {"Content-Type": "application/json"}

    # --------------------
    # 1ª chamada: extrair informações no JSON
    # --------------------
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
            print(f"Abaixo a primeira resposta do Gemini:\n{json_resp}\n----\n\n\n")
            break
        except Exception as e:
            st.error("⚠️ Erro ao parsear JSON retornado pelo Gemini.")
            st.json(data)
            raise e
    else:
        st.error(
            "🚨 Não foi possível obter resposta do Gemini após várias tentativas (JSON)."
        )
        return {}

    # --------------------
    # 2ª chamada: reescrever HDA (se questionário=True)
    # --------------------
    if questionario:
        quest_prompt = f"""
        Você é um médico neurocirurgião que irá apresentar para outros neurocirurgiões essa história de doença de um paciente. 
        Reescreva a história abaixo para usar termos técnicos e jargão médico, seja o mais breve possível. 
        Não adicione floreios nas frases nem conjunções bonitas, seja curto e direto.
        História:
        {json_resp['data']["hda"]}
        """

        payload2 = {"contents": [{"parts": [{"text": quest_prompt}]}]}

        for tentativa in range(1, tentativas + 1):
            response2 = requests.post(url, headers=headers, data=json.dumps(payload2))
            data2 = response2.json()

            if "error" in data2:
                if data2["error"].get("code") == 503:
                    st.warning(
                        f"⚠️ Gemini sobrecarregado (HDA). Tentando novamente ({tentativa}/{tentativas})..."
                    )
                    time.sleep(3)
                    continue
                else:
                    st.error("❌ Erro na API Gemini (reescrita de HDA)")
                    st.json(data2)
                    return json_resp

            try:
                reescrita = data2["candidates"][0]["content"]["parts"][0][
                    "text"
                ].strip()
            
                print(f"\n\n\nvar reescrita:{reescrita}\n\n\n")
                print(f"Primeira história:\n{json_resp["data"]["hda"]}\n")
                json_resp["data"]["hda"] = reescrita
                print(f"Segunda história:\n{json_resp["data"]["hda"]}\n")
                break
            except Exception as e:
                st.error("⚠️ Erro ao parsear resposta da HDA.")
                st.json(data2)
                raise e
        else:
            st.error(
                "🚨 Não foi possível obter resposta do Gemini após várias tentativas (HDA)."
            )

    return json_resp


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
st.header(f"Slides no Google Drive: [Abrir pasta]({FOLDER_URL})")

st.checkbox(
    "Sua história é um questionário?",
    value=False,
    key="is_questionario",
    # on_change=printValueOnTerminal(st.session_state["is_questionario"]),
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
                resultado = chamar_gemini(
                    st.session_state["historia"], st.session_state["is_questionario"]
                )
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
                    # print(url)

                    # print(
                    #     "Enviando para o Apps Script:",
                    #     json.dumps(resultado, indent=2, ensure_ascii=False),
                    # )

                    response = requests.post(url, json=resultado, timeout=10)
                    response.raise_for_status()

                    st.success(
                        "✅ Slide gerado com sucesso! Verifique a pasta Automações."
                    )
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
