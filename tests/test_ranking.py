import time
from types import SimpleNamespace as NS

import numpy as np

from feed.core import diversify, parse_tags, recency, relevance, unit


def test_parse_tags_trims_and_skips_empty():
    assert parse_tags("") == set()
    assert parse_tags("machine learning, startups,") == {"machine learning", "startups"}


def test_relevance_is_cosine_similarity_clipped_to_zero():
    profile = unit([1.0, 0.0, 0.0])
    assert relevance(profile, [2.0, 0.0, 0.0]) == 1.0
    assert relevance(profile, [0.0, 3.0, 0.0]) == 0.0
    assert relevance(profile, [-1.0, 0.0, 0.0]) == 0.0
    assert 0.7 < relevance(profile, [1.0, 1.0, 0.0]) < 0.71


def test_relevance_without_profile_or_embedding_is_zero():
    assert relevance(None, [1.0]) == 0.0
    assert relevance(unit([1.0]), None) == 0.0


def test_unit_vector_has_length_one():
    assert np.isclose(np.linalg.norm(unit([3.0, 4.0])), 1.0)


def test_recency_prefers_newer_posts():
    now = time.time()
    assert recency(NS(timestamp=now)) > recency(NS(timestamp=now - 7200))


def test_diversify_caps_length_and_mixes_topics():
    posts = [NS(topic="tech") for _ in range(30)] + [NS(topic="ai"), NS(topic="sports")]
    feed = diversify(posts, limit=20)
    assert len(feed) <= 20
    assert {"tech", "ai", "sports"} <= {p.topic for p in feed}
