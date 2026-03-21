"""Tests for compatibility family computation."""

from engine.core.families import (
    compute_families,
    get_family_independent_products,
)
from engine.tests.conftest import SAMPLE_PRODUCTS, make_product


def test_am5_ddr5_family_only_am5():
    """AM5_DDR5 family should only contain AM5 CPUs and DDR5 RAM."""
    families = compute_families(SAMPLE_PRODUCTS)
    am5 = next((f for f in families if f.socket == "AM5"), None)
    assert am5 is not None
    assert am5.ddr_type == "DDR5"
    for cpu in am5.cpus:
        assert cpu.specs["socket"] == "AM5"
    for mobo in am5.motherboards:
        assert mobo.specs["socket"] == "AM5"
        assert mobo.specs["ddr_type"] == "DDR5"
    for ram in am5.ram:
        assert ram.specs["ddr_type"] == "DDR5"


def test_am4_ddr4_family_only_am4():
    """AM4_DDR4 family should only contain AM4 CPUs and DDR4 RAM."""
    families = compute_families(SAMPLE_PRODUCTS)
    am4 = next((f for f in families if f.socket == "AM4"), None)
    assert am4 is not None
    assert am4.ddr_type == "DDR4"
    for cpu in am4.cpus:
        assert cpu.specs["socket"] == "AM4"
    for mobo in am4.motherboards:
        assert mobo.specs["socket"] == "AM4"
        assert mobo.specs["ddr_type"] == "DDR4"


def test_lga1700_ddr5_family():
    """LGA1700_DDR5 family should exist with Intel CPUs."""
    families = compute_families(SAMPLE_PRODUCTS)
    lga = next((f for f in families if f.socket == "LGA1700"), None)
    assert lga is not None
    assert lga.ddr_type == "DDR5"
    for cpu in lga.cpus:
        assert cpu.specs["socket"] == "LGA1700"


def test_cpu_brand_filter_amd():
    """cpu_brand='amd' should exclude Intel CPUs from all families."""
    families = compute_families(SAMPLE_PRODUCTS, cpu_brand="amd")
    for f in families:
        for cpu in f.cpus:
            assert cpu.brand.lower() == "amd"
    # LGA1700 family should be gone (no AMD CPUs for that socket)
    lga = next((f for f in families if f.socket == "LGA1700"), None)
    assert lga is None


def test_cpu_brand_filter_intel():
    """cpu_brand='intel' should exclude AMD CPUs."""
    families = compute_families(SAMPLE_PRODUCTS, cpu_brand="intel")
    for f in families:
        for cpu in f.cpus:
            assert cpu.brand.lower() == "intel"
    # AM4/AM5 families should be gone
    am_families = [f for f in families if f.socket.startswith("AM")]
    assert len(am_families) == 0


def test_cpu_brand_no_preference():
    """cpu_brand='no_preference' should include all CPUs."""
    families = compute_families(SAMPLE_PRODUCTS, cpu_brand="no_preference")
    all_cpus = []
    for f in families:
        all_cpus.extend(f.cpus)
    brands = {cpu.brand.lower() for cpu in all_cpus}
    assert "amd" in brands
    assert "intel" in brands


def test_cooling_preference_liquid():
    """cooling_preference='liquid' should only include liquid coolers."""
    families = compute_families(SAMPLE_PRODUCTS, cooling_preference="liquid")
    for f in families:
        for c in f.coolers:
            assert c.specs.get("type") == "liquid"


def test_cooling_preference_air():
    """cooling_preference='air' should only include air coolers."""
    families = compute_families(SAMPLE_PRODUCTS, cooling_preference="air")
    for f in families:
        for c in f.coolers:
            assert c.specs.get("type") == "air"


def test_empty_families_excluded():
    """Families without CPUs or motherboards should not appear."""
    # Only AM4 products, no LGA1700 or AM5
    products = [
        make_product(1, "cpu", "AMD", "Ryzen 5 5600X",
                     {"socket": "AM4", "cores": "6", "tdp": "65"}, 140),
        make_product(10, "motherboard", "MSI", "B550-A PRO",
                     {"socket": "AM4", "chipset": "AMD B550", "form_factor": "ATX",
                      "ddr_type": "DDR4"}, 100),
        make_product(20, "ram", "Corsair", "LPX 16GB",
                     {"ddr_type": "DDR4", "capacity_gb": "16"}, 145),
        make_product(70, "cooling", "Thermalright", "Assassin",
                     {"type": "air"}, 35),
    ]
    families = compute_families(products)
    assert len(families) == 1
    assert families[0].socket == "AM4"


def test_form_factor_filter_micro_atx():
    """micro_atx form factor should include micro_atx and mini_itx mobos."""
    products = [
        make_product(1, "cpu", "AMD", "Ryzen 5 5600X",
                     {"socket": "AM4", "cores": "6"}, 140),
        make_product(10, "motherboard", "MSI", "ATX Board",
                     {"socket": "AM4", "chipset": "B550", "form_factor": "ATX",
                      "ddr_type": "DDR4"}, 100),
        make_product(11, "motherboard", "MSI", "mATX Board",
                     {"socket": "AM4", "chipset": "B550", "form_factor": "Micro-ATX",
                      "ddr_type": "DDR4"}, 80),
        make_product(20, "ram", "Corsair", "DDR4 16GB",
                     {"ddr_type": "DDR4", "capacity_gb": "16"}, 100),
        make_product(70, "cooling", "Thermalright", "Cooler",
                     {"type": "air"}, 30),
    ]
    families = compute_families(products, form_factor="micro_atx")
    assert len(families) == 1
    # Only micro-ATX motherboard should be included (ATX too big)
    assert len(families[0].motherboards) == 1
    assert "mATX" in families[0].motherboards[0].model


def test_family_name():
    """Family name should be socket_ddr_type."""
    families = compute_families(SAMPLE_PRODUCTS)
    names = {f.name for f in families}
    assert "AM5_DDR5" in names
    assert "AM4_DDR4" in names


def test_family_pool_method():
    """pool() should return correct products for family-bound categories."""
    families = compute_families(SAMPLE_PRODUCTS)
    am5 = next(f for f in families if f.socket == "AM5")
    assert am5.pool("cpu") == am5.cpus
    assert am5.pool("motherboard") == am5.motherboards
    assert am5.pool("ram") == am5.ram
    assert am5.pool("cooling") == am5.coolers
    assert am5.pool("gpu") == []  # GPU is family-independent


def test_coolers_with_socket_support():
    """When coolers have socket_support data, filter by it."""
    products = [
        make_product(1, "cpu", "AMD", "Ryzen 5 5600X",
                     {"socket": "AM4"}, 140),
        make_product(10, "motherboard", "MSI", "B550",
                     {"socket": "AM4", "chipset": "B550", "form_factor": "ATX",
                      "ddr_type": "DDR4"}, 100),
        make_product(20, "ram", "Corsair", "DDR4",
                     {"ddr_type": "DDR4", "capacity_gb": "16"}, 100),
        make_product(70, "cooling", "CoolerA", "AM4 Only",
                     {"type": "air", "socket_support": "AM4,AM5"}, 30),
        make_product(71, "cooling", "CoolerB", "Intel Only",
                     {"type": "air", "socket_support": "LGA1700,LGA1851"}, 30),
    ]
    families = compute_families(products)
    assert len(families) == 1
    am4 = families[0]
    assert len(am4.coolers) == 1
    assert am4.coolers[0].model == "AM4 Only"


def test_family_independent_products():
    """get_family_independent_products returns GPU, storage, PSU, case."""
    independent = get_family_independent_products(SAMPLE_PRODUCTS)
    assert "gpu" in independent
    assert "storage" in independent
    assert "psu" in independent
    assert "case" in independent
    # Should NOT include family-bound categories
    assert "cpu" not in independent
    assert "motherboard" not in independent
    assert "ram" not in independent
    assert "cooling" not in independent


def test_coolers_all_included_when_no_socket_data():
    """When no cooler has socket_support data, all coolers go in every family."""
    families = compute_families(SAMPLE_PRODUCTS)
    for f in families:
        # All coolers from SAMPLE_PRODUCTS have no socket_support
        assert len(f.coolers) >= 1
