"""Tests for pipelines.rank — segment scoring."""
import pytest
from pipelines.rank import score_segment


class TestScoreSegment:
    def test_keyword_scoring(self):
        seg = {"text": "Apple reported strong iPhone sales", "claims": []}
        prof = {"keywords": ["apple", "iphone"], "entities": [], "penalties": []}
        score = score_segment(seg, prof)
        assert score == 4.0  # 2 keywords * 2.0 each

    def test_entity_scoring(self):
        seg = {"text": "Tim Cook announced new products", "claims": []}
        prof = {"keywords": [], "entities": ["tim cook"], "penalties": []}
        score = score_segment(seg, prof)
        assert score == 3.0  # 1 entity * 3.0

    def test_penalty(self):
        seg = {"text": "This is sponsored content", "claims": []}
        prof = {"keywords": [], "entities": [], "penalties": ["sponsored"]}
        score = score_segment(seg, prof)
        assert score == -2.0  # 1 penalty * -2.0

    def test_claims_add_weight(self):
        seg = {"text": "Revenue hit $10B", "claims": ["Revenue hit $10B"]}
        prof = {"keywords": [], "entities": [], "penalties": []}
        score = score_segment(seg, prof)
        assert score == 1.0  # 1 claim * 1.0

    def test_require_claim_penalty(self):
        seg = {"text": "Just chatting", "claims": []}
        prof = {"keywords": [], "entities": [], "penalties": [], "require_claim_or_metric": True}
        score = score_segment(seg, prof)
        assert score == -3.0

    def test_combined(self):
        seg = {"text": "Apple will launch new iPhone in Q2", "claims": ["Apple will launch new iPhone in Q2"]}
        prof = {
            "keywords": ["iphone", "launch"],
            "entities": ["apple"],
            "penalties": [],
        }
        score = score_segment(seg, prof)
        # keywords: 2*2=4, entities: 1*3=3, claims: 1*1=1 → 8.0
        assert score == 8.0
