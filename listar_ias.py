import os
from dotenv import load_dotenv
from google import genai

# 1. Carrega as variáveis do arquivo .env
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("❌ ERRO: A chave 'GEMINI_API_KEY' não foi encontrada no arquivo .env!")
    exit()

# 2. Inicializa o cliente do Gemini
client = genai.Client(api_key=api_key)

def listar_modelos():
    print("🔍 Consultando a API do Google para listar as IAs disponíveis na sua chave...\n")
    
    try:
        # Consulta a API oficial para listar os modelos liberados
        modelos = client.models.list()
        
        print("=" * 70)
        print(f"{'NOME DO MODELO (ID)':<40} | {'GERAÇÃO DE TEXTO/JSON'}")
        print("=" * 70)
        
        modelos_disponiveis = []
        
        for m in modelos:
            # Trata o nome do modelo removendo o prefixo 'models/'
            nome_modelo = m.name.replace("models/", "") if hasattr(m, 'name') else str(m)
            
            # Checa se o modelo aceita a função generateContent
            metodos = getattr(m, 'supported_generation_methods', [])
            suporta_geracao = "generateContent" in metodos or True # Se veio na lista, suporta chamadas
            
            status = "✅ Sim" if suporta_geracao else "❌ Não"
            
            # Filtra e destaca modelos relevantes da família Gemini
            if "gemini" in nome_modelo.lower():
                modelos_disponiveis.append(nome_modelo)
                print(f"{nome_modelo:<40} | {status}")

        print("=" * 70)
        print(f"\n🎉 Total de modelos Gemini ativos encontrados: {len(modelos_disponiveis)}")
        
        print("\n💡 RECOMENDAÇÃO DE TRIO PRINCIPAL PARA O PROJETO:")
        
        # Filtra os melhores para sugestão
        flash_models = [m for m in modelos_disponiveis if "flash" in m]
        pro_models = [m for m in modelos_disponiveis if "pro" in m]
        
        if flash_models:
            print(f" 🔹 Principal (Rápido e Preciso):  '{flash_models[0]}'")
        if len(flash_models) > 1:
            print(f" 🔹 Secundário/Reserva:            '{flash_models[1]}'")
        if pro_models:
            print(f" 🔹 Alta Complexidade (Pro):       '{pro_models[0]}'")

    except Exception as e:
        print(f"❌ Erro ao consultar a lista de modelos: {e}")

if __name__ == "__main__":
    listar_modelos()