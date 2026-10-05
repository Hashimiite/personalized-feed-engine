"""Feed assistant: a LangGraph pipeline that answers questions using only the posts in the feed.

retrieve (semantic search) -> no_match when nothing is close enough, otherwise generate.
generate uses any LangChain chat model set through LLM_MODEL (for example
"anthropic:claude-haiku-4-5-20251001"). Without one, or if the model call fails, it lists the
most relevant posts instead so the endpoint always answers.
"""

import logging
import os
from functools import lru_cache
from typing import Literal, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph

log = logging.getLogger(__name__)

MIN_SIMILARITY = float(os.getenv("ASK_MIN_SIMILARITY", "0.5"))
TOP_K = 5
SYSTEM_PROMPT = (
    "Answer the question directly using only the numbered posts provided. Only start with yes or no "
    "when the posts clearly support it. If the posts point in different directions, say so and give "
    "each side briefly. Cite posts by their number in square brackets, like [3]. If the posts do not "
    "answer the question, say so in one sentence."
)


class AskState(TypedDict, total=False):
    question: str
    posts: list[dict]
    answer: str


def list_posts(posts):
    return "The most relevant posts are " + "; ".join(f"[{p['id']}] {p['content']}" for p in posts)


def build_assistant(search, llm=None, min_similarity: float = MIN_SIMILARITY):
    """search(question) returns (post, similarity) pairs, best first."""

    def retrieve(state: AskState):
        posts = [
            {"id": post.id, "topic": post.topic, "content": post.content, "similarity": round(sim, 3)}
            for post, sim in search(state["question"])
            if sim >= min_similarity
        ]
        return {"posts": posts}

    def route(state: AskState) -> Literal["generate", "no_match"]:
        return "generate" if state["posts"] else "no_match"

    def no_match(state: AskState):
        return {"answer": "No posts in the feed match that question yet."}

    def generate(state: AskState):
        posts = state["posts"]
        if llm is None:
            return {"answer": list_posts(posts)}
        context = "\n".join(f"[{p['id']}] ({p['topic']}) {p['content']}" for p in posts)
        messages = [
            SystemMessage(SYSTEM_PROMPT),
            HumanMessage(f"Posts:\n{context}\n\nQuestion: {state['question']}"),
        ]
        try:
            return {"answer": str(llm.invoke(messages).text)}
        except Exception:
            log.exception("LLM call failed; answering with the retrieved posts instead")
            return {"answer": list_posts(posts)}

    graph = StateGraph(AskState)
    graph.add_node("retrieve", retrieve)
    graph.add_node("generate", generate)
    graph.add_node("no_match", no_match)
    graph.add_edge(START, "retrieve")
    graph.add_conditional_edges("retrieve", route)
    graph.add_edge("generate", END)
    graph.add_edge("no_match", END)
    return graph.compile()


@lru_cache
def default_llm():
    model = os.getenv("LLM_MODEL")
    if not model:
        return None
    from langchain.chat_models import init_chat_model

    return init_chat_model(model)
