"""Tests for the candidate formatting function used in ClaudeService."""

from app.services.catalog import CandidateComponent, StoreOption
from app.services.claude import _format_candidates


def _make_candidate(category, brand, model, specs, price=100.0):
    return CandidateComponent(
        id=1,
        category=category,
        brand=brand,
        model=model,
        specs=specs,
        stores=[
            StoreOption(
                store="amazon",
                url="https://www.amazon.de/dp/TEST?tag=thepccoach-21",
                price_eur=price,
            )
        ],
    )


class TestFormatCandidates:
    def test_formats_category_header(self):
        candidates = {
            "cpu": [
                _make_candidate(
                    "cpu", "AMD", "Ryzen 5 7600", {"socket": "AM5", "cores": "6"}
                )
            ],
        }
        text = _format_candidates(candidates)
        assert "### CPU (1 options)" in text

    def test_includes_component_details(self):
        candidates = {
            "gpu": [
                _make_candidate(
                    "gpu", "NVIDIA", "RTX 4060", {"vram_gb": "8", "tdp": "115"}, 299
                )
            ],
        }
        text = _format_candidates(candidates)
        assert "NVIDIA RTX 4060" in text
        assert "€299" in text
        assert "amazon €299" in text

    def test_includes_specs(self):
        candidates = {
            "cpu": [
                _make_candidate(
                    "cpu",
                    "AMD",
                    "Ryzen 5 7600",
                    {"socket": "AM5", "cores": "6", "tdp": "65"},
                )
            ],
        }
        text = _format_candidates(candidates)
        assert "socket=AM5" in text
        assert "cores=6" in text

    def test_includes_affiliate_url(self):
        candidates = {
            "cpu": [_make_candidate("cpu", "AMD", "Ryzen 5 7600", {"socket": "AM5"})],
        }
        text = _format_candidates(candidates)
        assert "url: https://www.amazon.de/dp/TEST?tag=thepccoach-21" in text

    def test_multiple_categories(self):
        candidates = {
            "cpu": [_make_candidate("cpu", "AMD", "Ryzen 5", {})],
            "gpu": [_make_candidate("gpu", "NVIDIA", "RTX 4060", {})],
        }
        text = _format_candidates(candidates)
        assert "### CPU" in text
        assert "### GPU" in text

    def test_empty_candidates_produces_header_only(self):
        text = _format_candidates({})
        assert "Available Components" in text
