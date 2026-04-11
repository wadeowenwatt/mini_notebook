import os

from llama_index.core import (
    VectorStoreIndex,
    SimpleDirectoryReader,
    Settings,
    StorageContext,
)
from llama_index.llms.google_genai import GoogleGenAI
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from dotenv import load_dotenv
from llama_index.vector_stores.chroma import ChromaVectorStore
import chromadb

load_dotenv()

DATA_DIR = "./data"
CHROMA_HOST = os.getenv("CHROMA_HOST", "localhost")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8000"))
CHROMA_COLLECTION = os.getenv("CHROMA_COLLECTION", "rag_documents")

# ─── Configure Models ────────────────────────────────────────────────────────

llm = GoogleGenAI(model="models/gemini-2.5-flash")
embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-m3")

Settings.llm = llm
Settings.embed_model = embed_model
Settings.chunk_size = 512
Settings.chunk_overlap = 50

# ─── ChromaDB Client ─────────────────────────────────────────────────────────


def _get_chroma_collection():
    """Kết nối ChromaDB server và trả về collection."""
    client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
    """Tạo hoặc kết nối ChromaDB local và trả về collection."""
    # Dùng PersistentClient để lưu vector DB ngay trong thư mục project thay vì kết nối server ngoài
    # client = chromadb.PersistentClient(path="./chroma_db")
    collection = client.get_or_create_collection(CHROMA_COLLECTION)
    return client, collection


# ─── Build or Load Index ─────────────────────────────────────────────────────


def _build_index(collection) -> VectorStoreIndex:
    """Đọc PDF từ data/ và đánh index vào ChromaDB collection."""
    print("[RAG] Bắt đầu đọc PDF và tạo Vector vào ChromaDB...")
    if not os.path.exists(DATA_DIR) or not os.listdir(DATA_DIR):
        raise FileNotFoundError(
            f"Thư mục '{DATA_DIR}' không tồn tại hoặc rỗng. "
            "Hãy thêm file PDF vào thư mục này."
        )
    documents = SimpleDirectoryReader(DATA_DIR).load_data()
    vector_store = ChromaVectorStore(chroma_collection=collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    index = VectorStoreIndex.from_documents(documents, storage_context=storage_context)
    print("[RAG] Đã lưu embedding vào ChromaDB thành công!")
    return index


def _load_index(collection) -> VectorStoreIndex:
    """Load index từ ChromaDB collection đã có dữ liệu."""
    print("[RAG] Tải index từ ChromaDB...")
    vector_store = ChromaVectorStore(chroma_collection=collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    index = VectorStoreIndex.from_vector_store(
        vector_store, storage_context=storage_context
    )
    print("[RAG] Tải index thành công!")
    return index


def _init_index() -> VectorStoreIndex:
    """Khởi tạo index: build mới nếu collection rỗng, ngược lại load từ ChromaDB."""
    _client, collection = _get_chroma_collection()
    if collection.count() == 0:
        return _build_index(collection)
    return _load_index(collection)


# Khởi tạo index và query engine khi module được import
_index = _init_index()
_query_engine = _index.as_query_engine()

# ─── Public API ──────────────────────────────────────────────────────────────


def query(message: str) -> str:
    """
    Nhận câu hỏi của user, chạy qua RAG pipeline và trả về câu trả lời.

    Args:
        message: Câu hỏi từ user.

    Returns:
        Chuỗi câu trả lời từ LLM.
    """
    print(f"[RAG] Query: {message!r}")
    response = _query_engine.query(message)
    answer = str(response)
    print(f"[RAG] Answer: {answer[:120]}...")
    return answer
