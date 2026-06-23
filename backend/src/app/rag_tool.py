import os
from pinecone import Pinecone
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
top_k = 3
PINECONE_API_KEY =os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME")
pc = Pinecone(api_key=PINECONE_API_KEY)
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL")
OPENAI_API_KEY=os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

if PINECONE_INDEX_NAME not in pc.list_indexes().names():
    raise ValueError(f"The index '{PINECONE_INDEX_NAME}' does not exist in Pinecone.")

index = pc.Index(PINECONE_INDEX_NAME)

def get_embedding(text: str):
    """Generate an embedding for a query."""
    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text
    )
    return response.data[0].embedding

def semantic_search(query: str, top_k: int = top_k) -> str:
    """
    Search for and retrieve passages directly from the book
    "An Introduction to Statistical Learning with Applications in Python".
    Use this tool EVERY TIME the user asks about concepts, definitions,
    algorithms, or examples from the book.

    Parameters:
      - query (str): The user's question or the key concepts to search for.
        For example: "explanation of k-means" or "difference between Lasso and Ridge".
    """
    query_vector = get_embedding(query)

    results = index.query(
        vector=query_vector,
        top_k=top_k,
        include_metadata=True
    )

    text_response = ""
    for match in results["matches"]:
        text = match["metadata"]["text"].replace("\n", " ")
        text_response += f"{text}\n\n"
    return text_response.strip()


def semantic_search_raw(query: str, top_k: int = 3) -> dict:
    """
    Functionally identical to semantic_search.
    The only difference is the output format.
    It is used to generate evaluation metrics.
    """
    query_vector = get_embedding(query)

    results = index.query(
        vector=query_vector,
        top_k=top_k,
        include_metadata=True
    )

    contexts = []
    scores = []

    if "matches" in results:
        for match in results["matches"]:
            text = match["metadata"]["text"].replace("\n", " ")
            contexts.append(text)

            if "score" in match:
                scores.append(match["score"])

    final_context = "\n\n".join(contexts)

    return {
        "context": final_context,
        "scores": scores
    }
