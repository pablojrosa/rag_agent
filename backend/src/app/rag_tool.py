"""Retrieve book passages from Pinecone using OpenAI embeddings."""
import os
from functools import lru_cache

from dotenv import load_dotenv
from openai import OpenAI
from pinecone import Pinecone

from .observability import observation

load_dotenv()


@lru_cache(maxsize=1)
def get_index():
    return Pinecone(api_key=os.environ["PINECONE_API_KEY"]).Index(
        os.environ["PINECONE_INDEX_NAME"]
    )


def get_embedding(text):
    model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    with observation("query-embedding", as_type="embedding", model=model, input=text) as span:
        response = OpenAI().embeddings.create(model=model, input=text)
        span.update(usage_details={"input": response.usage.prompt_tokens,
                                   "total": response.usage.total_tokens})
        return response.data[0].embedding


def semantic_search_raw(query, top_k=3):
    vector = get_embedding(query)
    with observation("book-retrieval", as_type="retriever", input=query,
                     metadata={"top_k": top_k}) as span:
        results = get_index().query(vector=vector, top_k=top_k, include_metadata=True)
        chunks = []
        for match in results.get("matches", []):
            metadata = match.get("metadata") or {}
            chunks.append({"id": match["id"], "text": metadata.get("text", ""),
                           "page": metadata.get("page"), "source": metadata.get("source"),
                           "score": match.get("score")})
        span.update(output=chunks)
        return {"context": "\n\n".join(chunk["text"] for chunk in chunks),
                "chunks": chunks,
                "scores": [chunk["score"] for chunk in chunks if chunk["score"] is not None]}


def semantic_search(query, top_k=3):
    return semantic_search_raw(query, top_k)["context"]
