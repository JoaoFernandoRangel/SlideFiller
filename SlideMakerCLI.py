import requests
import json
import time
import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GOOGLE_URL = os.getenv("GOOGLE_URL_ENDPOINT")

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
    """Envia o texto ao Gemini e retorna JSON estruturado"""
    prompt = f"""
Você é um extrator de informações.
Receba o seguinte texto de paciente e preencha o JSON fornecido.
Se a informação não estiver no texto, mantenha o campo vazio. Não faça nenhuma suposição nem remova nenhuma informação.
Valores de peso e altura devem vir em quilograma e metros, me de em números para poder processar depois sem problemas. Pode inferir o sexo a partir do nome.
Na seção de antecedentes pessoais os campos não listados devem ser completados com a palavra "Nega". Corrija as letras maiusculas.
Texto:
{historia}

JSON base:
{json.dumps(JSON_TEMPLATE, indent=2, ensure_ascii=False)}

Responda SOMENTE com o JSON preenchido. 
"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    headers = {"Content-Type": "application/json"}

    for tentativa in range(1, tentativas + 1):
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        data = response.json()

        if "error" in data:
            if data["error"].get("code") == 503:
                print(
                    f"⚠️ Gemini sobrecarregado. Tentando novamente ({tentativa}/{tentativas})..."
                )
                time.sleep(3)
                continue
            else:
                print("❌ Erro na API Gemini:")
                print(json.dumps(data, indent=2, ensure_ascii=False))
                return {}

        try:
            resposta = data["candidates"][0]["content"]["parts"][0]["text"].strip()
            resposta = resposta.replace("```json", "").replace("```", "").strip()
            return json.loads(resposta)
        except Exception as e:
            print("⚠️ Erro ao parsear JSON retornado pelo Gemini.")
            print(json.dumps(data, indent=2, ensure_ascii=False))
            raise e

    print("🚨 Não foi possível obter resposta do Gemini após várias tentativas.")
    return {}


def processar_historias(arquivo="historias.txt"):
    """Lê o arquivo, processa cada história e gera slides via Apps Script"""
    with open(arquivo, "r", encoding="utf-8") as file:
        historias = file.read().split("----")

    for idx, historia in enumerate(historias, start=1):
        historia = historia.strip()
        if not historia:
            continue

        print(f"\n=== Processando história {idx} ===")
        resultado = chamar_gemini(historia)

        if not resultado:
            print("⚠️ Não foi possível obter dados estruturados.")
            continue

        # Enviar para Google Apps Script
        try:
            response = requests.post(GOOGLE_URL, json=resultado, timeout=10)
            response.raise_for_status()
            print("✅ Slide gerado com sucesso!")
            print(json.dumps(response.json(), indent=2, ensure_ascii=False))
        except Exception as e:
            print(f"❌ Erro ao enviar para Apps Script: {e}")


if __name__ == "__main__":
    processar_historias()
