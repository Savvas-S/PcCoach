"""Compatibility family computation.

Groups products into families defined by (socket, ddr_type) where all
family-bound components (CPU, motherboard, RAM, cooling) are guaranteed
cross-compatible. Family-independent categories (GPU, storage, PSU, case)
are shared across all families.

This eliminates the need for post-selection socket/DDR validation — if you
pick one product from each pool within a family, they work together.
"""

from __future__ import annotations

from collections import defaultdict

from engine.models.types import CompatibilityFamily, ProductRecord

# Categories that vary per family (must match socket/DDR)
_FAMILY_BOUND = {"cpu", "motherboard", "ram", "cooling"}

# Categories shared across all families
FAMILY_INDEPENDENT = {"gpu", "storage", "psu", "case"}

# Known AMD sockets
_AMD_SOCKETS = frozenset({"AM4", "AM5"})

# Known Intel sockets
_INTEL_SOCKETS = frozenset({"LGA1700", "LGA1851"})


def compute_families(
    products: list[ProductRecord],
    form_factor: str = "atx",
    cpu_brand: str = "no_preference",
    cooling_preference: str = "no_preference",
) -> list[CompatibilityFamily]:
    """Group products into compatibility families.

    Args:
        products: Deduplicated product list.
        form_factor: Case form factor filter (applied to motherboards).
        cpu_brand: CPU brand preference ("intel", "amd", "no_preference").
        cooling_preference: Cooling type ("liquid", "air", "no_preference").

    Returns:
        List of CompatibilityFamily, excluding empty families. Sorted by
        number of products descending (most populated first). Caller can
        reorder based on profile preference.
    """
    # Step 1: Categorize products
    cpus: list[ProductRecord] = []
    motherboards: list[ProductRecord] = []
    ram_sticks: list[ProductRecord] = []
    coolers: list[ProductRecord] = []

    for p in products:
        if p.category == "cpu":
            # Apply brand filter
            if cpu_brand == "amd" and p.brand.lower() != "amd":
                continue
            if cpu_brand == "intel" and p.brand.lower() != "intel":
                continue
            cpus.append(p)
        elif p.category == "motherboard":
            # Apply form factor filter
            if not _form_factor_compatible(
                p.specs.get("form_factor", ""), form_factor
            ):
                continue
            motherboards.append(p)
        elif p.category == "ram":
            ram_sticks.append(p)
        elif p.category == "cooling":
            # Apply cooling preference filter
            if cooling_preference == "liquid" and p.specs.get("type") != "liquid":
                continue
            if cooling_preference == "air" and p.specs.get("type") != "air":
                continue
            coolers.append(p)

    # Step 2: Discover all (socket, ddr_type) combos from motherboards
    family_keys: set[tuple[str, str]] = set()
    mobo_by_family: dict[tuple[str, str], list[ProductRecord]] = defaultdict(list)

    for mobo in motherboards:
        socket = mobo.specs.get("socket", "")
        ddr_type = mobo.specs.get("ddr_type", "")
        if not socket or not ddr_type:
            continue
        key = (socket, ddr_type)
        family_keys.add(key)
        mobo_by_family[key].append(mobo)

    # Step 3: Build families
    families: list[CompatibilityFamily] = []

    for socket, ddr_type in sorted(family_keys):
        # Filter CPUs by socket
        family_cpus = [c for c in cpus if c.specs.get("socket") == socket]
        if not family_cpus:
            continue

        # Filter RAM by DDR type
        family_ram = [r for r in ram_sticks if r.specs.get("ddr_type") == ddr_type]
        if not family_ram:
            continue

        family_mobos = mobo_by_family[(socket, ddr_type)]
        if not family_mobos:
            continue

        # Coolers: filter by socket_support if available, otherwise all coolers
        family_coolers = _filter_coolers(coolers, socket)

        families.append(
            CompatibilityFamily(
                socket=socket,
                ddr_type=ddr_type,
                cpus=family_cpus,
                motherboards=family_mobos,
                ram=family_ram,
                coolers=family_coolers,
            )
        )

    # Sort: most populated families first (total products across all pools)
    families.sort(
        key=lambda f: len(f.cpus) + len(f.motherboards) + len(f.ram) + len(f.coolers),
        reverse=True,
    )

    return families


def _filter_coolers(
    coolers: list[ProductRecord], socket: str
) -> list[ProductRecord]:
    """Filter coolers compatible with the given socket.

    If coolers have `socket_support` spec, filter by it. Otherwise,
    return all coolers (current catalog has no socket_support data).
    """
    has_socket_data = any(c.specs.get("socket_support") for c in coolers)
    if not has_socket_data:
        return coolers

    compatible = []
    for c in coolers:
        support = c.specs.get("socket_support", "")
        # socket_support is a comma-separated string
        supported_sockets = [s.strip() for s in support.split(",")]
        if socket in supported_sockets:
            compatible.append(c)

    return compatible if compatible else coolers


def _form_factor_compatible(mobo_ff: str, request_ff: str) -> bool:
    """Check if a motherboard form factor fits the requested case size.

    Form factor hierarchy: ATX (largest) > Micro-ATX > Mini-ITX (smallest).
    A smaller motherboard fits in a larger case, but not vice versa.
    """
    ranks = {
        "atx": 3,
        "micro_atx": 2,
        "micro-atx": 2,
        "microatx": 2,
        "mini_itx": 1,
        "mini-itx": 1,
        "miniitx": 1,
    }
    mobo_rank = ranks.get(mobo_ff.lower().strip(), 3)
    request_rank = ranks.get(request_ff.lower().strip(), 3)
    # Motherboard must be same size or smaller than case
    return mobo_rank <= request_rank


def get_family_independent_products(
    products: list[ProductRecord],
) -> dict[str, list[ProductRecord]]:
    """Get products for family-independent categories (GPU, storage, PSU, case).

    These products are shared across all families — no socket/DDR filtering.
    """
    result: dict[str, list[ProductRecord]] = defaultdict(list)
    for p in products:
        if p.category in FAMILY_INDEPENDENT:
            result[p.category].append(p)
    return result
