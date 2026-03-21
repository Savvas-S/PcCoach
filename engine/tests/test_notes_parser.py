"""Tests for user notes parsing."""

from engine.core.notes_parser import parse_notes


def test_empty_notes():
    prefs = parse_notes(None)
    assert prefs.brands == []
    assert prefs.resolution is None
    assert prefs.specific_models == []
    assert prefs.keywords == []


def test_empty_string():
    prefs = parse_notes("")
    assert prefs.brands == []


def test_brand_extraction_nvidia():
    prefs = parse_notes("I want an NVIDIA GPU")
    assert "NVIDIA" in prefs.brands


def test_brand_extraction_amd():
    prefs = parse_notes("prefer AMD for CPU")
    assert "AMD" in prefs.brands


def test_brand_extraction_multiple():
    prefs = parse_notes("I like NVIDIA GPUs and Corsair RAM with Samsung storage")
    assert "NVIDIA" in prefs.brands
    assert "Corsair" in prefs.brands
    assert "Samsung" in prefs.brands


def test_resolution_4k():
    prefs = parse_notes("I want to play at 4K")
    assert prefs.resolution == "4K"


def test_resolution_1440p():
    prefs = parse_notes("targeting 1440p gaming")
    assert prefs.resolution == "1440p"


def test_resolution_1080p():
    prefs = parse_notes("1080p is fine for me")
    assert prefs.resolution == "1080p"


def test_resolution_qhd():
    prefs = parse_notes("QHD monitor preferred")
    assert prefs.resolution == "1440p"


def test_specific_model_rtx():
    prefs = parse_notes("I want the RTX 5070 Ti")
    assert any("5070" in m.lower() for m in prefs.specific_models)


def test_specific_model_ryzen():
    prefs = parse_notes("Looking at the Ryzen 7 7800X3D")
    assert any("7800x3d" in m.lower() for m in prefs.specific_models)


def test_keywords_silent():
    prefs = parse_notes("I want a silent build")
    assert "silent" in prefs.keywords


def test_keywords_rgb():
    prefs = parse_notes("Love RGB everything")
    assert "rgb" in prefs.keywords


def test_keywords_compact():
    prefs = parse_notes("Need a small compact build")
    assert "compact" in prefs.keywords


def test_keywords_wifi():
    prefs = parse_notes("Must have wifi on the motherboard")
    assert "wifi" in prefs.keywords


def test_combined_notes():
    prefs = parse_notes("I want NVIDIA RTX 5070 for 1440p gaming, silent build with RGB")
    assert "NVIDIA" in prefs.brands
    assert prefs.resolution == "1440p"
    assert "silent" in prefs.keywords
    assert "rgb" in prefs.keywords
