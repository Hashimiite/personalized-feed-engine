from types import SimpleNamespace as NS

from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

from feed.assistant import build_assistant, default_llm

HITS = [
    (NS(id=1, topic="ai", content="Small language models match larger ones"), 0.82),
    (NS(id=2, topic="research", content="Neural networks predict protein folding"), 0.61),
    (NS(id=3, topic="sports", content="Hockey playoffs open"), 0.31),
]


def search(question):
    return HITS


class BrokenModel(GenericFakeChatModel):
    def _generate(self, *args, **kwargs):
        raise RuntimeError("provider down")


def test_generate_uses_llm_answer_with_only_close_posts():
    llm = GenericFakeChatModel(messages=iter([AIMessage("Smaller models are catching up [1]")]))
    result = build_assistant(search, llm, min_similarity=0.5).invoke({"question": "What is new in AI?"})
    assert result["answer"] == "Smaller models are catching up [1]"
    assert [p["id"] for p in result["posts"]] == [1, 2]


def test_no_match_branch_skips_the_llm():
    llm = GenericFakeChatModel(messages=iter([]))  # raises if called
    result = build_assistant(search, llm, min_similarity=0.9).invoke({"question": "Recipe for bread?"})
    assert result["posts"] == []
    assert result["answer"].startswith("No posts")


def test_without_llm_lists_relevant_posts():
    result = build_assistant(search, None, min_similarity=0.5).invoke({"question": "What is new in AI?"})
    assert "[1]" in result["answer"] and "[2]" in result["answer"] and "[3]" not in result["answer"]


def test_llm_failure_falls_back_to_listing_posts():
    llm = BrokenModel(messages=iter([]))
    result = build_assistant(search, llm, min_similarity=0.5).invoke({"question": "What is new in AI?"})
    assert result["answer"].startswith("The most relevant posts are [1]")


def test_llm_model_setting_loads_openai_chat_model(monkeypatch):
    monkeypatch.setenv("LLM_MODEL", "openai:gpt-4o-mini")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-not-a-real-key")
    default_llm.cache_clear()
    try:
        llm = default_llm()
        assert type(llm).__name__ == "ChatOpenAI"
        assert llm.model_name == "gpt-4o-mini"
    finally:
        default_llm.cache_clear()


def test_no_llm_model_means_no_chat_model(monkeypatch):
    monkeypatch.delenv("LLM_MODEL", raising=False)
    default_llm.cache_clear()
    try:
        assert default_llm() is None
    finally:
        default_llm.cache_clear()
