import os, threading
from app.rag.knowledge_base import get_all_documents

CHROMA_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "chroma")

_collection = None
_lock = threading.Lock()


def _get_collection():
    global _collection
    if _collection is not None:
        return _collection
    with _lock:
        if _collection is not None:  # double-check after acquiring lock
            return _collection
        try:
            import chromadb
            from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
            client = chromadb.PersistentClient(path=CHROMA_PATH)
            ef = DefaultEmbeddingFunction()  # all-MiniLM-L6-v2 via onnxruntime, sin scipy
            col = client.get_or_create_collection(
                name="cyberagent_kb",
                embedding_function=ef,
                metadata={"hnsw:space": "cosine"},
            )
            _collection = col  # assign before indexing so a failed index doesn't null it
            if col.count() == 0:
                try:
                    _index_documents(col)
                except Exception as ie:
                    print(f"[RAG] Index error (non-fatal): {ie}")
        except Exception as e:
            print(f"[RAG] ChromaDB init error: {e}")
            _collection = None
    return _collection


def _index_documents(col):
    docs = get_all_documents()
    ids, documents, metadatas = [], [], []
    for doc in docs:
        ids.append(doc["id"])
        documents.append(f"{doc['title']}\n\n{doc['content']}")
        metadatas.append({
            "title": doc["title"],
            "platform": doc.get("platform", "all"),
            "tags": ",".join(doc.get("tags", [])),
        })
    if ids:
        col.add(ids=ids, documents=documents, metadatas=metadatas)
        print(f"[RAG] Indexed {len(ids)} documents")


def search(query: str, n_results: int = 3) -> list[dict]:
    col = _get_collection()
    if col is None:
        return []
    with _lock:
        try:
            n = min(n_results, col.count())
            if n == 0:
                return []
            results = col.query(query_texts=[query], n_results=n)
            out = []
            for i, doc in enumerate(results["documents"][0]):
                meta = results["metadatas"][0][i]
                out.append({
                    "title": meta["title"],
                    "content": doc,
                    "platform": meta["platform"],
                })
            return out
        except Exception as e:
            print(f"[RAG] Search error: {e}")
            return []


def add_document(doc_id: str, title: str, content: str,
                 platform: str = "all", tags: list = None):
    col = _get_collection()
    if col is None:
        return
    with _lock:
        try:
            col.upsert(
                ids=[doc_id],
                documents=[f"{title}\n\n{content}"],
                metadatas=[{
                    "title": title,
                    "platform": platform,
                    "tags": ",".join(tags or []),
                }],
            )
        except Exception as e:
            print(f"[RAG] Add error: {e}")


def reset_index():
    global _collection
    try:
        import chromadb
        client = chromadb.PersistentClient(path=CHROMA_PATH)
        client.delete_collection("cyberagent_kb")
        _collection = None
        _get_collection()
    except Exception as e:
        print(f"[RAG] Reset error: {e}")
