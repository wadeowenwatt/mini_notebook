import os
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings
from llama_index.llms.google_genai import GoogleGenAI
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

# 1. Set up API Key (Replace 'YOUR_API_KEY' with your actual key)
os.environ["GOOGLE_API_KEY"] = "AIzaSyA4OuUArwm7LySJjsgmEko9LfY0MqiGGKc"

# 2. Configure Gemini Model and Embedding Model
llm = GoogleGenAI(model="models/gemini-2.5-flash")
embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-m3")

# Assign default configurations for LlamaIndex
Settings.llm = llm
Settings.embed_model = embed_model
Settings.chunk_size = 512  # Size of each text chunk
Settings.chunk_overlap = 50 # Overlap between chunks to maintain context

# 3. Load data from a local directory
# Create a folder named 'data' and place your PDF/TXT files there
if not os.path.exists("data"):
    os.makedirs("data")
    print("Please add documents to the newly created 'data' directory.")
else:
    documents = SimpleDirectoryReader("data").load_data()

    # 4. Create Index (Convert text to vectors and store)
    index = VectorStoreIndex.from_documents(documents)

    # 5. Create Query Engine for querying
    query_engine = index.as_query_engine()

    # 6. Perform a question
    user_query = "Hãy cho tôi biết phạm vi điều chỉnh của luật đất đai"
    response = query_engine.query(user_query)

    print(f"Question: {user_query}")
    print(f"Answer: {response}")