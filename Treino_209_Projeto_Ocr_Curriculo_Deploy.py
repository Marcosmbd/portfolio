import streamlit as st
import requests
from io import BytesIO
from google import genai
from google.genai import types
from google.auth import default
from google.auth.exceptions import DefaultCredentialsError
import json
import os

# Recupera a chave de serviço do secrets.toml
service_key_json = st.secrets["key"]["service_key"]

# Converte o JSON para um dicionário
service_key_dict = json.loads(service_key_json)

# Salva a chave de serviço em um arquivo temporário
service_key_path = "gcp_service_key.json"  # Caminho temporário no Streamlit Cloud

with open(service_key_path, "w") as f:
    json.dump(service_key_dict, f)

# Configura a variável de ambiente para o Google Cloud usar o arquivo
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = service_key_path

try:
    credentials, project = default()
except DefaultCredentialsError:
    st.error("Erro: Credenciais não encontradas. Verifique se configurou corretamente.")
    st.stop()

def generate(text):
    client = genai.Client(
        vertexai=True,
        project="marcos-estudos",
        location="global",
    )

    si_text1 = """Você deve atuar como um assistente inteligente especializado em análise de currículos e apresentação profissional. Seu objetivo é responder às perguntas com precisão, clareza e profissionalismo, 
            garantindo que a resposta gere uma impressão positiva sobre Marcos Bernardino.
            O documento de referência é o currículo de Marcos Bernardino, que contém informações detalhadas sobre sua trajetória profissional, habilidades técnicas e interpessoais, certificações, 
            formações acadêmicas, experiências relevantes e projetos desenvolvidos.
            Como estruturar suas respostas:
            Forneça respostas claras e objetivas, sempre destacando as competências, realizações e diferenciais de Marcos.
            Use uma abordagem persuasiva e profissional, ressaltando pontos fortes e experiências relevantes.
            Quando aplicável, mencione exemplos práticos ou resultados obtidos para reforçar a credibilidade das informações.
            Se uma informação específica não estiver disponível no documento, responda de forma diplomática e reforce as qualificações gerais de Marcos.
            Pontos-chave a serem valorizados:
            Experiência Profissional: Destacar cargos, responsabilidades e conquistas.
            Habilidades Técnicas: Evidenciar conhecimentos em ferramentas, linguagens e metodologias.
            Certificações e Formação Acadêmica: Mencionar diplomas e cursos que reforcem a credibilidade.
            Projetos e Iniciativas: Citar trabalhos notáveis ou contribuições relevantes.
            Soft Skills: Ressaltar habilidades interpessoais e diferenciais no ambiente de trabalho.
            Seu tom de resposta deve ser profissional, porém acessível e envolvente. Mantenha um equilíbrio entre objetividade e entusiasmo para tornar a comunicação clara e impactante.
            Ao informar links, mantenha os underlines que estão nos links"""
    
    model = "gemini-2.0-flash-001"
    
    # Construindo o contexto da conversa a partir do histórico
    contents = []
    for message in st.session_state.messages:
        role = "user" if message["role"] == "user" else "model"
        contents.append(types.Content(role=role, parts=[types.Part.from_text(text=message["content"])]))

    # Adiciona a pergunta atual
    contents.append(types.Content(role="user", parts=[types.Part.from_text(text=prompt)]))

    tools = [
        types.Tool(retrieval=types.Retrieval(vertex_ai_search=types.VertexAISearch(
            datastore=st.secrets["google_cloud"]["datastore"]
        )))]
    
    generate_content_config = types.GenerateContentConfig(
        temperature=0.2,
        top_p=0.95,
        max_output_tokens=8192,
        response_modalities=["TEXT"],
        tools=tools,
        system_instruction=[types.Part.from_text(text=instruction)],
    )

    response = client.models.generate_content(
        model=model,
        contents=contents,  # 🔹 Agora o Gemini recebe TODO o histórico
        config=generate_content_config,
    )

    if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
        return response.candidates[0].content.parts[0].text
    else:
        return "Resposta não encontrada."

# --- Sidebar ---
with st.sidebar:
    # Exibir imagem
    image_url = st.secrets["google_drive"]["image_url"]
    try:
        response = requests.get(image_url)
        image = BytesIO(response.content)
        st.image(image, width=1080)
    except Exception:
        st.error("Erro ao carregar a imagem.")

    # Nome e link para download do CV
    st.markdown("<h4 style='text-align: center; font-size: 24px;'><b>Marcos Bernardino</b></h4>", unsafe_allow_html=True)
    cv_url = st.secrets["google_drive"]["cv_url"]
    st.markdown(f"<p style='text-align: center;'><a href='{cv_url}' download>Download CV</a></p>", unsafe_allow_html=True)
    
    st.markdown("""
    <style>
        #MainMenu {visibility: hidden;}
        header {visibility: hidden;}
        footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- Inicializar histórico do chat ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- Exibir título e descrição apenas na primeira interação ---
if len(st.session_state.messages) == 0:
    st.title("Marcos Bernardino")
    st.write("Faça perguntas sobre a vida profissional ou acadêmica de Marcos Bernardino")

# --- Exibir mensagens do histórico ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- Input do usuário ---
if prompt := st.chat_input("Digite sua pergunta"):
    # Adicionar mensagem do usuário ao histórico
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Gerar resposta da IA
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        try:
            ai_response = generate(prompt)
            full_response = ai_response
        except Exception as e:
            full_response = f"Ocorreu um erro ao gerar a resposta: {e}"
            st.error(full_response)

        # Exibir resposta e atualizar histórico
        message_placeholder.markdown(full_response)
        st.session_state.messages.append({"role": "assistant", "content": full_response})
