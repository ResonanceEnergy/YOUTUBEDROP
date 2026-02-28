"""Tests for utils.text — text utilities."""
import pytest
from utils.text import (
    normalize_text,
    split_sentences,
    has_numbers,
    keyword_hits,
    extract_simple_claims,
)


class TestNormalize:
    def test_whitespace_collapse(self):
        assert normalize_text("  hello   world  ") == "hello world"

    def test_newlines(self):
        assert normalize_text("hello\n\nworld") == "hello world"


class TestSplitSentences:
    def test_basic(self):
        sents = split_sentences("Hello world. This is a test. Done!")
        assert sents == ["Hello world.", "This is a test.", "Done!"]

    def test_single(self):
        sents = split_sentences("No punctuation here")
        assert sents == ["No punctuation here"]

    def test_empty(self):
        assert split_sentences("") == []


class TestHasNumbers:
    def test_with_number(self):
        assert has_numbers("Revenue was $2.5 billion")

    def test_without(self):
        assert not has_numbers("no numbers here")


class TestKeywordHits:
    def test_hits(self):
        assert keyword_hits("Apple reported strong iPhone sales", ["apple", "iphone"]) == 2

    def test_no_hits(self):
        assert keyword_hits("Nothing relevant", ["apple", "iphone"]) == 0

    def test_case_insensitive(self):
        assert keyword_hits("APPLE earnings", ["apple"]) == 1


class TestExtractClaims:
    def test_claims_with_numbers(self):
        sents = ["Revenue was $10 billion.", "The sky is blue.", "They will launch in Q2."]
        claims = extract_simple_claims(sents)
        assert "Revenue was $10 billion." in claims
        assert "They will launch in Q2." in claims
        assert "The sky is blue." not in claims

    def test_max_claims(self):
        sents = [f"They will launch product {i}." for i in range(20)]
        claims = extract_simple_claims(sents)
        assert len(claims) <= 8
