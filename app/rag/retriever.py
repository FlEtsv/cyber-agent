from app.rag.vectorstore import search

MAX_CONTENT_LEN = 600


def retrieve_context(query: str, n: int = 3) -> str:
    docs = search(query, n_results=n)
    if not docs:
        return ""
    parts = []
    for doc in docs:
        content = doc["content"]
        if len(content) > MAX_CONTENT_LEN:
            content = content[:MAX_CONTENT_LEN] + "..."
        parts.append(f"### {doc['title']}\n{content}")
    return "\n\n".join(parts)
