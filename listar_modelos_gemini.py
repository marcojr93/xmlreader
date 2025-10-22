"""
Script para listar modelos disponíveis no Google Generative AI
e identificar o nome correto para usar no LangChain
"""
import os
import google.generativeai as genai

def listar_modelos_disponíveis():
    """Lista todos os modelos disponíveis no Google Generative AI"""
    print("🔍 Listando modelos disponíveis no Google Generative AI...")
    
    # Verificar se API key está configurada
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("❌ GOOGLE_API_KEY não configurada")
        print("Configure com: os.environ['GOOGLE_API_KEY'] = 'sua_api_key'")
        return
    
    try:
        # Configurar API key
        genai.configure(api_key=api_key)
        
        print("📋 Modelos disponíveis:")
        print("-" * 60)
        
        # Listar todos os modelos
        modelos_encontrados = []
        
        for modelo in genai.list_models():
            nome = modelo.name
            display_name = getattr(modelo, 'display_name', 'N/A')
            description = getattr(modelo, 'description', 'N/A')
            
            # Verificar se suporta generateContent
            supported_methods = getattr(modelo, 'supported_generation_methods', [])
            suporta_generate = 'generateContent' in supported_methods
            
            print(f"Nome: {nome}")
            print(f"Display Name: {display_name}")
            print(f"Descrição: {description}")
            print(f"Suporta generateContent: {suporta_generate}")
            print("-" * 60)
            
            if suporta_generate:
                modelos_encontrados.append(nome)
        
        print(f"\n✅ Modelos que suportam generateContent ({len(modelos_encontrados)}):")
        for modelo in modelos_encontrados:
            print(f"  • {modelo}")
        
        # Sugerir modelos para LangChain
        print(f"\n💡 Sugestões para LangChain:")
        modelos_recomendados = []
        for modelo in modelos_encontrados:
            if 'gemini' in modelo.lower():
                modelos_recomendados.append(modelo)
        
        for modelo in modelos_recomendados:
            # Extrair nome simples para LangChain
            nome_simples = modelo.replace('models/', '')
            print(f"  📌 Use: model=\"{nome_simples}\"")
        
        return modelos_recomendados
        
    except Exception as e:
        print(f"❌ Erro ao listar modelos: {e}")
        return []

def testar_modelo_especifico(nome_modelo):
    """Testa um modelo específico"""
    print(f"\n🧪 Testando modelo: {nome_modelo}")
    
    try:
        api_key = os.environ.get("GOOGLE_API_KEY")
        genai.configure(api_key=api_key)
        
        # Criar modelo
        model = genai.GenerativeModel(nome_modelo)
        
        # Teste simples
        response = model.generate_content("Olá! Você está funcionando?")
        print(f"✅ Modelo {nome_modelo} funcionando!")
        print(f"Resposta: {response.text[:100]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao testar {nome_modelo}: {e}")
        return False

if __name__ == "__main__":
    # Configurar API key temporária para teste
    # Em produção, use uma API key real
    if not os.environ.get("GOOGLE_API_KEY"):
        print("⚠️  Configure GOOGLE_API_KEY para testar")
        print("Exemplo: os.environ['GOOGLE_API_KEY'] = 'sua_api_key_aqui'")
    else:
        modelos = listar_modelos_disponíveis()
        
        # Testar os modelos encontrados
        if modelos:
            print(f"\n🔬 Testando modelos encontrados...")
            for modelo in modelos[:3]:  # Testar apenas os 3 primeiros
                nome_simples = modelo.replace('models/', '')
                testar_modelo_especifico(nome_simples)