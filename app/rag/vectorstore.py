import os
from app.rag.knowledge_base import get_all_documents

CHROMA_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "chroma")

_collection = None


def _get_collection():
    global _collection
    if _collection is not None:
        return _collection
    try:
        import chromadb
        from chromadb.utils import embedding_functions
        client = chromadb.PersistentClient(path=CHROMA_PATH)
        ef = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        _collection = client.get_or_create_collection(
            name="cyberagent_kb",
            embedding_function=ef,
            metadata={"hnsw:space": "cosine"},
        )
        if _collection.count() == 0:
            _index_documents(_collection)
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
