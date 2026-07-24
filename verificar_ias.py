import os
import time
from dotenv import load_dotenv
from google import genai

# 1. Carrega as variáveis de ambiente
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("❌ ERRO: A chave 'GEMINI_API_KEY' não foi encontrada no .env!")
    exit()

client = genai.Client(api_key=api_key)

def checar_status_modelos():
    print("======================================================================")
    print("🔍 CONSULTANDO MODELOS DISPONÍVEIS NA SUA CHAVE DA API...")
    print("======================================================================\n")

    try:
        # Busca a lista oficial de modelos diretamente do servidor do Google
        todos_modelos = list(client.models.list())
        
        # Filtra apenas modelos Gemini destinados a geração de texto
        modelos_gemini = []
        for m in todos_modelos:
            nome = m.name.replace("models/", "")
            if "gemini" in nome.lower() and "embed" not in nome.lower() and "imagen" not in nome.lower():
                modelos_gemini.append(nome)

        print(f"📋 Encontrados {len(modelos_gemini)} modelos Gemini ativos na sua conta.\n")
        print("⚡ TESTANDO DISPONIBILIDADE E COTA EM TEMPO REAL (PING)...\n")

        modelos_prontos = []

        for idx, modelo in enumerate(modelos_gemini, 1):
            try:
                # Faz uma requisição ultraleve de teste
                response = client.models.generate_content(
                    model=modelo,
                    contents="OK"
                )
                print(f"  [{idx:02d}] ✅ {modelo:<30} -> DISPONÍVEL E COM COTA LIBERADA!")
                modelos_prontos.append(modelo)

            except Exception as e:
                err_msg = str(e)
                if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
                    print(f"  [{idx:02d}] ⚠️ {modelo:<30} -> SEM COTA NO MOMENTO (429 / Limite atingido)")
                elif "404" in err_msg or "NOT_FOUND" in err_msg:
                    print(f"  [{idx:02d}] ❌ {modelo:<30} -> NÃO ENCONTRADO / MÉTODOS NÃO SUPORTADOS (404)")
                elif "503" in err_msg:
                    print(f"  [{idx:02d}] ⚠️ {modelo:<30} -> SERVIDOR OCUPADO NO MOMENTO (503)")
                else:
                    print(f"  [{idx:02d}] ⚠️ {modelo:<30} -> ERRO: {err_msg[:50]}...")

            # Pausa rápida de 0.5s para não estourar requisições por segundo durante a checagem
            time.sleep(0.5)

        print("\n======================================================================")
        print("📊 RESUMO DE DISPONIBILIDADE:")
        print(f"🟢 Modelos Prontos para Uso Agorinha: {len(modelos_prontos)} de {len(modelos_gemini)}")
        print("======================================================================")

        if modelos_prontos:
            print("\n💡 Cole esta lista no seu 'LISTA_MODELOS' do ingestao_lote.py:")
            print(f"LISTA_MODELOS = {modelos_prontos}")

    except Exception as e:
        print(f"❌ Erro ao conectar na API do Google: {e}")

if __name__ == "__main__":
    checar_status_modelos()