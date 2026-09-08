"""One retrieval and generation pipeline for chat and experiments."""
import os

from .main_agent import generate_answer
from .observability import observation


def answer_question(question, history=None, *, mode="online", expected_output=None):
    from .rag_tool import semantic_search_raw

    with observation("rag-answer", as_type="chain", input={"question": question},
                     metadata={"mode": mode, "prompt_version": os.getenv("PROMPT_VERSION", "1")}) as span:
        retrieved = semantic_search_raw(question)
        # Evaluators read this observation directly, including its retrieved context.
        span.update(input={"question": question, "context": retrieved["context"],
                           "expected_output": expected_output},
                    metadata={"mode": mode, "chunks": retrieved["chunks"],
                              "prompt_version": os.getenv("PROMPT_VERSION", "1")})
        answer = generate_answer(question, retrieved["context"], history)
        span.update(output=answer)
        return answer
