import time
from types import SimpleNamespace as NS

from feed.core import diversify, parse_tags, recency, relevance


def test_parse_tags_handles_empty_and_lists():
    assert parse_tags("") == set()
    assert parse_tags("tech,ai") == {"tech", "ai"}


def test_relevance_counts_matching_topic():
    user = NS(interests="tech,ai")
    assert relevance(user, NS(topic="ai")) == 1
    assert relevance(user, NS(topic="sports")) == 0


def test_recency_prefers_newer_posts():
    now = time.time()
    assert recency(NS(timestamp=now)) > recency(NS(timestamp=now - 7200))
    assert 0 < recency(NS(timestamp=now - 7200)) < 1


def test_diversify_caps_length_and_mixes_topics():
    posts = [NS(topic="tech") for _ in range(30)] + [NS(topic="ai"), NS(topic="sports")]
    feed = diversify(posts, limit=20)
    assert len(feed) <= 20
    assert {"tech", "ai", "sports"} <= {p.topic for p in feed}
