import os

from llama_index.core import (
    VectorStoreIndex,
    SimpleDirectoryReader,
    Settings,
    StorageContext,
    load_index_from_storage,
)
from llama_index.llms.google_genai import GoogleGenAI  # noqa: E402
from llama_index.embeddings.huggingface import HuggingFaceEmbedding  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

load_dotenv()

PERSIST_DIR = "./storage"
DATA_DIR = "./data"

# ─── Configure Models ────────────────────────────────────────────────────────

llm = GoogleGenAI(model="models/gemini-2.5-flash")
embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-m3")

Settings.llm = llm
Settings.embed_model = embed_model
Settings.chunk_size = 512
Settings.chunk_overlap = 50

# ─── Build or Load Index ─────────────────────────────────────────────────────


def _build_index() -> VectorStoreIndex:
    """Tạo index mới từ thư mục data/ và lưu vào storage/."""
    print("[RAG] Chưa có dữ liệu embedding. Bắt đầu đọc PDF và tạo Vector...")
    if not os.path.exists(DATA_DIR) or not os.listdir(DATA_DIR):
        raise FileNotFoundError(
            f"Thư mục '{DATA_DIR}' không tồn tại hoặc rỗng. "
            "Hãy thêm file PDF vào thư mục này."
        )
    documents = SimpleDirectoryReader(DATA_DIR).load_data()
    index = VectorStoreIndex.from_documents(documents)
    index.storage_context.persist(persist_dir=PERSIST_DIR)
    print("[RAG] Đã lưu embedding thành công!")
    return index


def _load_index() -> VectorStoreIndex:
    """Load index đã tồn tại từ storage/."""
    print("[RAG] Phát hiện dữ liệu đã embedding, đang tải lên từ ổ cứng...")
    storage_context = StorageContext.from_defaults(persist_dir=PERSIST_DIR)
    index = load_index_from_storage(storage_context)
    print("[RAG] Tải embedding thành công!")
    return index


# Khởi tạo index và query engine khi module được import
_index = _load_index() if os.path.exists(PERSIST_DIR) else _build_index()
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
