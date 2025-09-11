import streamlit as st
import os
from openai import OpenAI
import json
import time
from dotenv import load_dotenv

load_dotenv()

# Cria cliente OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

st.title("OpenAI API com gpt-4o-mini (v1.x)")

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

# Área de texto do Streamlit
historia = st.text_area("Digite seu prompt:")


# Função para chamar OpenAI
def chamar_openai(historia: str, tentativas=3) -> dict:
    prompt = f"""
Você é um extrator de informações.
Receba o seguinte texto de paciente e preencha o JSON fornecido.
Se a informação não estiver no texto, mantenha o campo vazio. Não faça nenhuma suposição nem remova nenhuma informação.
Valores de peso e altura devem vir em quilograma e metros. 
Na seção de antecedentes pessoais os campos não listados devem ser completados com a palavra "Nega".
Pode inferir o genero a partir do nome.

Texto:
{historia}

JSON base:
{json.dumps(JSON_TEMPLATE, indent=2, ensure_ascii=False)}

Responda SOMENTE com o JSON preenchido. 
"""

    for tentativa in range(1, tentativas + 1):
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
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
            # Remove blocos de código caso existam
            resposta = resposta.replace("```json", "").replace("```", "").strip()
            return json.loads(resposta)

        except json.JSONDecodeError:
            st.warning(f"⚠️ Erro ao parsear JSON. Tentativa {tentativa}/{tentativas}...")
            time.sleep(2)
            continue
        except Exception as e:
            st.error(f"❌ Erro na API OpenAI: {e}")
            time.sleep(2)
            continue

    st.error("🚨 Não foi possível obter resposta da OpenAI após várias tentativas.")
    return {}


# Botão para gerar resposta
if st.button("Gerar resposta"):
    if historia.strip():
        resultado = chamar_openai(historia)
        if resultado:
            st.json(resultado)
        else:
            st.warning("Não foi possível gerar o JSON.")
    else:
        st.warning("Por favor, digite um prompt")
