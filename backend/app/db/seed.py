"""Seed the component catalog with real products and Amazon.de affiliate links.

Run via:  uv run python -m app.db.seed
Or:       make seed
"""

from __future__ import annotations

import asyncio
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import init_db
from app.db.models import AffiliateLink, Component

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Amazon.de affiliate tag — appended to all URLs
# ---------------------------------------------------------------------------
_AMAZON_TAG = "thepccoach-21"


def _amazon_url(asin: str) -> str:
    """Build an Amazon.de affiliate product URL from an ASIN."""
    return f"https://www.amazon.de/dp/{asin}?tag={_AMAZON_TAG}"


# ---------------------------------------------------------------------------
# Seed data — manually curated, real products, real ASINs, real prices
#
# Prices are approximate EUR prices as of March 2026.
# Update periodically by checking Amazon.de.
# ---------------------------------------------------------------------------

SEED_COMPONENTS: list[dict] = [
    # ===== CPUs =====
    {
        "category": "cpu",
        "brand": "AMD",
        "model": "Ryzen 5 7600",
        "specs": {
            "socket": "AM5",
            "cores": "6",
            "threads": "12",
            "tdp": "65",
            "boost_ghz": "5.1",
        },
        "links": [{"store": "amazon", "asin": "B0BMQJWBDM", "price_eur": 199.00}],
    },
    {
        "category": "cpu",
        "brand": "AMD",
        "model": "Ryzen 5 7600X",
        "specs": {
            "socket": "AM5",
            "cores": "6",
            "threads": "12",
            "tdp": "105",
            "boost_ghz": "5.3",
        },
        "links": [{"store": "amazon", "asin": "B0BBJDS62N", "price_eur": 219.00}],
    },
    {
        "category": "cpu",
        "brand": "AMD",
        "model": "Ryzen 7 7700X",
        "specs": {
            "socket": "AM5",
            "cores": "8",
            "threads": "16",
            "tdp": "105",
            "boost_ghz": "5.4",
        },
        "links": [{"store": "amazon", "asin": "B0BBHHT8LY", "price_eur": 289.00}],
    },
    {
        "category": "cpu",
        "brand": "AMD",
        "model": "Ryzen 7 7800X3D",
        "specs": {
            "socket": "AM5",
            "cores": "8",
            "threads": "16",
            "tdp": "120",
            "boost_ghz": "5.0",
        },
        "links": [{"store": "amazon", "asin": "B0BTZB7F88", "price_eur": 389.00}],
    },
    {
        "category": "cpu",
        "brand": "AMD",
        "model": "Ryzen 9 7900X",
        "specs": {
            "socket": "AM5",
            "cores": "12",
            "threads": "24",
            "tdp": "170",
            "boost_ghz": "5.6",
        },
        "links": [{"store": "amazon", "asin": "B0BBJ59WJ4", "price_eur": 399.00}],
    },
    {
        "category": "cpu",
        "brand": "AMD",
        "model": "Ryzen 9 7950X",
        "specs": {
            "socket": "AM5",
            "cores": "16",
            "threads": "32",
            "tdp": "170",
            "boost_ghz": "5.7",
        },
        "links": [{"store": "amazon", "asin": "B0BBHD5D8Y", "price_eur": 549.00}],
    },
    {
        "category": "cpu",
        "brand": "Intel",
        "model": "Core i5-14400F",
        "specs": {
            "socket": "LGA1700",
            "cores": "10",
            "threads": "16",
            "tdp": "65",
            "boost_ghz": "4.7",
        },
        "links": [{"store": "amazon", "asin": "B0CQ3142LB", "price_eur": 179.00}],
    },
    {
        "category": "cpu",
        "brand": "Intel",
        "model": "Core i5-14600K",
        "specs": {
            "socket": "LGA1700",
            "cores": "14",
            "threads": "20",
            "tdp": "125",
            "boost_ghz": "5.3",
        },
        "links": [{"store": "amazon", "asin": "B0CHBGVFHP", "price_eur": 269.00}],
    },
    {
        "category": "cpu",
        "brand": "Intel",
        "model": "Core i7-14700K",
        "specs": {
            "socket": "LGA1700",
            "cores": "20",
            "threads": "28",
            "tdp": "125",
            "boost_ghz": "5.6",
        },
        "links": [{"store": "amazon", "asin": "B0CGJ41C9W", "price_eur": 369.00}],
    },
    {
        "category": "cpu",
        "brand": "Intel",
        "model": "Core i9-14900K",
        "specs": {
            "socket": "LGA1700",
            "cores": "24",
            "threads": "32",
            "tdp": "125",
            "boost_ghz": "6.0",
        },
        "links": [{"store": "amazon", "asin": "B0CGJDKLB8", "price_eur": 519.00}],
    },
    # ===== GPUs =====
    {
        "category": "gpu",
        "brand": "NVIDIA",
        "model": "GeForce RTX 4060 (Gigabyte Windforce OC)",
        "specs": {
            "vram_gb": "8",
            "tdp": "115",
            "length_mm": "240",
            "interface": "PCIe 4.0 x8",
        },
        "links": [{"store": "amazon", "asin": "B0C8ZQTRD7", "price_eur": 299.00}],
    },
    {
        "category": "gpu",
        "brand": "NVIDIA",
        "model": "GeForce RTX 4060 Ti (MSI Ventus 2X Black OC)",
        "specs": {
            "vram_gb": "8",
            "tdp": "160",
            "length_mm": "251",
            "interface": "PCIe 4.0 x8",
        },
        "links": [{"store": "amazon", "asin": "B0C4F7KX1B", "price_eur": 399.00}],
    },
    {
        "category": "gpu",
        "brand": "NVIDIA",
        "model": "GeForce RTX 4070 (MSI Ventus 2X OC)",
        "specs": {
            "vram_gb": "12",
            "tdp": "200",
            "length_mm": "242",
            "interface": "PCIe 4.0 x16",
        },
        "links": [{"store": "amazon", "asin": "B0BYZJWDNC", "price_eur": 549.00}],
    },
    {
        "category": "gpu",
        "brand": "NVIDIA",
        "model": "GeForce RTX 4070 Super (Gigabyte Windforce OC)",
        "specs": {
            "vram_gb": "12",
            "tdp": "220",
            "length_mm": "282",
            "interface": "PCIe 4.0 x16",
        },
        "links": [{"store": "amazon", "asin": "B0CQTNRTWR", "price_eur": 599.00}],
    },
    {
        "category": "gpu",
        "brand": "NVIDIA",
        "model": "GeForce RTX 4070 Ti Super (ASUS TUF Gaming OC)",
        "specs": {
            "vram_gb": "16",
            "tdp": "285",
            "length_mm": "305",
            "interface": "PCIe 4.0 x16",
        },
        "links": [{"store": "amazon", "asin": "B0CS3X3DTG", "price_eur": 799.00}],
    },
    {
        "category": "gpu",
        "brand": "NVIDIA",
        "model": "GeForce RTX 4080 Super (Gigabyte Windforce V2)",
        "specs": {
            "vram_gb": "16",
            "tdp": "320",
            "length_mm": "329",
            "interface": "PCIe 4.0 x16",
        },
        "links": [{"store": "amazon", "asin": "B0CSK2GHR8", "price_eur": 999.00}],
    },
    {
        "category": "gpu",
        "brand": "NVIDIA",
        "model": "GeForce RTX 4090 (Gigabyte Windforce V2)",
        "specs": {
            "vram_gb": "24",
            "tdp": "450",
            "length_mm": "336",
            "interface": "PCIe 4.0 x16",
        },
        "links": [{"store": "amazon", "asin": "B0C82C1PWN", "price_eur": 1899.00}],
    },
    {
        "category": "gpu",
        "brand": "AMD",
        "model": "Radeon RX 7600 (Sapphire Pulse)",
        "specs": {
            "vram_gb": "8",
            "tdp": "165",
            "length_mm": "260",
            "interface": "PCIe 4.0 x8",
        },
        "links": [{"store": "amazon", "asin": "B0C49S5R55", "price_eur": 259.00}],
    },
    {
        "category": "gpu",
        "brand": "AMD",
        "model": "Radeon RX 7800 XT (Sapphire Pulse)",
        "specs": {
            "vram_gb": "16",
            "tdp": "263",
            "length_mm": "267",
            "interface": "PCIe 4.0 x16",
        },
        "links": [{"store": "amazon", "asin": "B0CGM19NMS", "price_eur": 479.00}],
    },
    {
        "category": "gpu",
        "brand": "AMD",
        "model": "Radeon RX 7900 XT (Sapphire Pulse)",
        "specs": {
            "vram_gb": "20",
            "tdp": "315",
            "length_mm": "280",
            "interface": "PCIe 4.0 x16",
        },
        "links": [{"store": "amazon", "asin": "B0BQNDB95D", "price_eur": 749.00}],
    },
    # ===== Motherboards — AM5 =====
    {
        "category": "motherboard",
        "brand": "Gigabyte",
        "model": "B650 Gaming X AX V2",
        "specs": {
            "socket": "AM5",
            "chipset": "B650",
            "ddr_type": "DDR5",
            "form_factor": "ATX",
            "max_ram_gb": "192",
        },
        "links": [{"store": "amazon", "asin": "B0CSKH56WN", "price_eur": 169.00}],
    },
    {
        "category": "motherboard",
        "brand": "MSI",
        "model": "MAG B650 TOMAHAWK WIFI",
        "specs": {
            "socket": "AM5",
            "chipset": "B650",
            "ddr_type": "DDR5",
            "form_factor": "ATX",
            "max_ram_gb": "192",
        },
        "links": [{"store": "amazon", "asin": "B0BDS873GF", "price_eur": 209.00}],
    },
    {
        "category": "motherboard",
        "brand": "ASUS",
        "model": "ROG STRIX B650-A GAMING WIFI",
        "specs": {
            "socket": "AM5",
            "chipset": "B650",
            "ddr_type": "DDR5",
            "form_factor": "ATX",
            "max_ram_gb": "192",
        },
        "links": [{"store": "amazon", "asin": "B0BHHVHQXZ", "price_eur": 239.00}],
    },
    {
        "category": "motherboard",
        "brand": "MSI",
        "model": "MAG X670E TOMAHAWK WIFI",
        "specs": {
            "socket": "AM5",
            "chipset": "X670E",
            "ddr_type": "DDR5",
            "form_factor": "ATX",
            "max_ram_gb": "192",
        },
        "links": [{"store": "amazon", "asin": "B09YCV8XQG", "price_eur": 289.00}],
    },
    {
        "category": "motherboard",
        "brand": "Gigabyte",
        "model": "B650M DS3H",
        "specs": {
            "socket": "AM5",
            "chipset": "B650",
            "ddr_type": "DDR5",
            "form_factor": "micro_atx",
            "max_ram_gb": "192",
        },
        "links": [{"store": "amazon", "asin": "B0BKL4JJD8", "price_eur": 119.00}],
    },
    {
        "category": "motherboard",
        "brand": "MSI",
        "model": "MAG B650M MORTAR WIFI",
        "specs": {
            "socket": "AM5",
            "chipset": "B650",
            "ddr_type": "DDR5",
            "form_factor": "micro_atx",
            "max_ram_gb": "192",
        },
        "links": [{"store": "amazon", "asin": "B0BDSBNWMH", "price_eur": 189.00}],
    },
    # ===== Motherboards — LGA1700 =====
    {
        "category": "motherboard",
        "brand": "Gigabyte",
        "model": "B760 Gaming X AX",
        "specs": {
            "socket": "LGA1700",
            "chipset": "B760",
            "ddr_type": "DDR5",
            "form_factor": "ATX",
            "max_ram_gb": "192",
        },
        "links": [{"store": "amazon", "asin": "B0BSHC2ZD4", "price_eur": 159.00}],
    },
    {
        "category": "motherboard",
        "brand": "MSI",
        "model": "MAG B760 TOMAHAWK WIFI",
        "specs": {
            "socket": "LGA1700",
            "chipset": "B760",
            "ddr_type": "DDR5",
            "form_factor": "ATX",
            "max_ram_gb": "192",
        },
        "links": [{"store": "amazon", "asin": "B0BMM7NZDX", "price_eur": 189.00}],
    },
    {
        "category": "motherboard",
        "brand": "ASUS",
        "model": "ROG STRIX Z790-A GAMING WIFI",
        "specs": {
            "socket": "LGA1700",
            "chipset": "Z790",
            "ddr_type": "DDR5",
            "form_factor": "ATX",
            "max_ram_gb": "192",
        },
        "links": [{"store": "amazon", "asin": "B0BSVD47ZC", "price_eur": 339.00}],
    },
    {
        "category": "motherboard",
        "brand": "Gigabyte",
        "model": "B760M DS3H",
        "specs": {
            "socket": "LGA1700",
            "chipset": "B760",
            "ddr_type": "DDR5",
            "form_factor": "micro_atx",
            "max_ram_gb": "192",
        },
        "links": [{"store": "amazon", "asin": "B0C6HY2FZV", "price_eur": 109.00}],
    },
    # ===== RAM — DDR5 =====
    {
        "category": "ram",
        "brand": "G.Skill",
        "model": "Flare X5 32GB (2x16GB) DDR5-6000 CL30",
        "specs": {
            "ddr_type": "DDR5",
            "capacity_gb": "32",
            "speed_mhz": "6000",
            "modules": "2x16GB",
            "cas_latency": "30",
        },
        "links": [{"store": "amazon", "asin": "B0DD295CNY", "price_eur": 99.00}],
    },
    {
        "category": "ram",
        "brand": "Kingston",
        "model": "FURY Beast 32GB (2x16GB) DDR5-6000 CL36",
        "specs": {
            "ddr_type": "DDR5",
            "capacity_gb": "32",
            "speed_mhz": "6000",
            "modules": "2x16GB",
            "cas_latency": "36",
        },
        "links": [{"store": "amazon", "asin": "B0BD5TF3T3", "price_eur": 89.00}],
    },
    {
        "category": "ram",
        "brand": "Corsair",
        "model": "Vengeance 32GB (2x16GB) DDR5-6000 CL30",
        "specs": {
            "ddr_type": "DDR5",
            "capacity_gb": "32",
            "speed_mhz": "6000",
            "modules": "2x16GB",
            "cas_latency": "30",
        },
        "links": [{"store": "amazon", "asin": "B0CBRJ63RT", "price_eur": 109.00}],
    },
    {
        "category": "ram",
        "brand": "G.Skill",
        "model": "Trident Z5 Neo 64GB (2x32GB) DDR5-6000 CL30",
        "specs": {
            "ddr_type": "DDR5",
            "capacity_gb": "64",
            "speed_mhz": "6000",
            "modules": "2x32GB",
            "cas_latency": "30",
        },
        "links": [{"store": "amazon", "asin": "B0BJP3MRW1", "price_eur": 189.00}],
    },
    {
        "category": "ram",
        "brand": "Kingston",
        "model": "FURY Beast 16GB (2x8GB) DDR5-5600 CL36",
        "specs": {
            "ddr_type": "DDR5",
            "capacity_gb": "16",
            "speed_mhz": "5600",
            "modules": "2x8GB",
            "cas_latency": "36",
        },
        "links": [{"store": "amazon", "asin": "B0BRTJCLBJ", "price_eur": 49.00}],
    },
    # ===== Storage =====
    {
        "category": "storage",
        "brand": "Samsung",
        "model": "990 EVO 1TB NVMe M.2",
        "specs": {
            "type": "NVMe M.2",
            "capacity_gb": "1000",
            "read_mbps": "5000",
            "write_mbps": "4200",
        },
        "links": [{"store": "amazon", "asin": "B0CP43PS7B", "price_eur": 79.00}],
    },
    {
        "category": "storage",
        "brand": "Samsung",
        "model": "990 Pro 1TB NVMe M.2",
        "specs": {
            "type": "NVMe M.2",
            "capacity_gb": "1000",
            "read_mbps": "7450",
            "write_mbps": "6900",
        },
        "links": [{"store": "amazon", "asin": "B0B9C3ZVHR", "price_eur": 99.00}],
    },
    {
        "category": "storage",
        "brand": "Samsung",
        "model": "990 Pro 2TB NVMe M.2",
        "specs": {
            "type": "NVMe M.2",
            "capacity_gb": "2000",
            "read_mbps": "7450",
            "write_mbps": "6900",
        },
        "links": [{"store": "amazon", "asin": "B0B9C4DKKG", "price_eur": 169.00}],
    },
    {
        "category": "storage",
        "brand": "WD",
        "model": "Black SN770 1TB NVMe M.2",
        "specs": {
            "type": "NVMe M.2",
            "capacity_gb": "1000",
            "read_mbps": "5150",
            "write_mbps": "4900",
        },
        "links": [{"store": "amazon", "asin": "B09QV692XY", "price_eur": 69.00}],
    },
    {
        "category": "storage",
        "brand": "WD",
        "model": "Black SN770 2TB NVMe M.2",
        "specs": {
            "type": "NVMe M.2",
            "capacity_gb": "2000",
            "read_mbps": "5150",
            "write_mbps": "4850",
        },
        "links": [{"store": "amazon", "asin": "B09QV5KJHV", "price_eur": 129.00}],
    },
    {
        "category": "storage",
        "brand": "Kingston",
        "model": "NV2 500GB NVMe M.2",
        "specs": {
            "type": "NVMe M.2",
            "capacity_gb": "500",
            "read_mbps": "3500",
            "write_mbps": "2100",
        },
        "links": [{"store": "amazon", "asin": "B0BBWJH1P8", "price_eur": 35.00}],
    },
    {
        "category": "storage",
        "brand": "Crucial",
        "model": "T500 1TB NVMe M.2",
        "specs": {
            "type": "NVMe M.2",
            "capacity_gb": "1000",
            "read_mbps": "7300",
            "write_mbps": "6800",
        },
        "links": [{"store": "amazon", "asin": "B0CK39YR9V", "price_eur": 89.00}],
    },
    # ===== PSU =====
    {
        "category": "psu",
        "brand": "Corsair",
        "model": "RM550e (2023) 550W 80+ Gold",
        "specs": {"wattage": "550", "efficiency": "80+ Gold", "modular": "full"},
        "links": [{"store": "amazon", "asin": "B0BYDP3XL1", "price_eur": 69.00}],
    },
    {
        "category": "psu",
        "brand": "Corsair",
        "model": "RM650e (2023) 650W 80+ Gold",
        "specs": {"wattage": "650", "efficiency": "80+ Gold", "modular": "full"},
        "links": [{"store": "amazon", "asin": "B0BYDLP71P", "price_eur": 79.00}],
    },
    {
        "category": "psu",
        "brand": "Corsair",
        "model": "RM750e (2023) 750W 80+ Gold",
        "specs": {"wattage": "750", "efficiency": "80+ Gold", "modular": "full"},
        "links": [{"store": "amazon", "asin": "B0BVL2CTX4", "price_eur": 89.00}],
    },
    {
        "category": "psu",
        "brand": "Corsair",
        "model": "RM850e (2023) 850W 80+ Gold",
        "specs": {"wattage": "850", "efficiency": "80+ Gold", "modular": "full"},
        "links": [{"store": "amazon", "asin": "B0BVL17341", "price_eur": 109.00}],
    },
    {
        "category": "psu",
        "brand": "be quiet!",
        "model": "Pure Power 12 M 650W 80+ Gold",
        "specs": {"wattage": "650", "efficiency": "80+ Gold", "modular": "full"},
        "links": [{"store": "amazon", "asin": "B0BT33WJ38", "price_eur": 85.00}],
    },
    {
        "category": "psu",
        "brand": "be quiet!",
        "model": "Pure Power 12 M 750W 80+ Gold",
        "specs": {"wattage": "750", "efficiency": "80+ Gold", "modular": "full"},
        "links": [{"store": "amazon", "asin": "B0BT2YZGZK", "price_eur": 95.00}],
    },
    {
        "category": "psu",
        "brand": "Seasonic",
        "model": "Focus GX-850 850W 80+ Gold",
        "specs": {"wattage": "850", "efficiency": "80+ Gold", "modular": "full"},
        "links": [{"store": "amazon", "asin": "B07WVN2TXK", "price_eur": 119.00}],
    },
    {
        "category": "psu",
        "brand": "Corsair",
        "model": "RM1000e (2023) 1000W 80+ Gold",
        "specs": {"wattage": "1000", "efficiency": "80+ Gold", "modular": "full"},
        "links": [{"store": "amazon", "asin": "B0BYL3MPDC", "price_eur": 149.00}],
    },
    # ===== Cases =====
    {
        "category": "case",
        "brand": "Fractal Design",
        "model": "Pop XL Air RGB TG",
        "specs": {
            "form_factor": "ATX",
            "max_gpu_length_mm": "405",
            "max_cooler_height_mm": "170",
            "included_fans": "3",
        },
        "links": [{"store": "amazon", "asin": "B0B1NLFNC1", "price_eur": 99.00}],
    },
    {
        "category": "case",
        "brand": "NZXT",
        "model": "H5 Flow (2024)",
        "specs": {
            "form_factor": "ATX",
            "max_gpu_length_mm": "365",
            "max_cooler_height_mm": "165",
            "included_fans": "2",
        },
        "links": [{"store": "amazon", "asin": "B0D2N4SHY3", "price_eur": 89.00}],
    },
    {
        "category": "case",
        "brand": "Corsair",
        "model": "4000D Airflow",
        "specs": {
            "form_factor": "ATX",
            "max_gpu_length_mm": "360",
            "max_cooler_height_mm": "170",
            "included_fans": "2",
        },
        "links": [{"store": "amazon", "asin": "B08C7BGV3D", "price_eur": 99.00}],
    },
    {
        "category": "case",
        "brand": "Lian Li",
        "model": "LANCOOL II Mesh C RGB",
        "specs": {
            "form_factor": "ATX",
            "max_gpu_length_mm": "384",
            "max_cooler_height_mm": "176",
            "included_fans": "3",
        },
        "links": [{"store": "amazon", "asin": "B08DX68X3D", "price_eur": 109.00}],
    },
    {
        "category": "case",
        "brand": "be quiet!",
        "model": "Pure Base 500DX",
        "specs": {
            "form_factor": "ATX",
            "max_gpu_length_mm": "369",
            "max_cooler_height_mm": "190",
            "included_fans": "3",
        },
        "links": [{"store": "amazon", "asin": "B087D61YMP", "price_eur": 109.00}],
    },
    {
        "category": "case",
        "brand": "Fractal Design",
        "model": "North TG",
        "specs": {
            "form_factor": "ATX",
            "max_gpu_length_mm": "355",
            "max_cooler_height_mm": "170",
            "included_fans": "2",
        },
        "links": [{"store": "amazon", "asin": "B0BXPYCFH3", "price_eur": 129.00}],
    },
    {
        "category": "case",
        "brand": "Cooler Master",
        "model": "MasterBox Q300L V2",
        "specs": {
            "form_factor": "micro_atx",
            "max_gpu_length_mm": "360",
            "max_cooler_height_mm": "159",
            "included_fans": "1",
        },
        "links": [{"store": "amazon", "asin": "B0C3FYPCZX", "price_eur": 49.00}],
    },
    {
        "category": "case",
        "brand": "Fractal Design",
        "model": "Pop Mini Air RGB TG",
        "specs": {
            "form_factor": "micro_atx",
            "max_gpu_length_mm": "405",
            "max_cooler_height_mm": "170",
            "included_fans": "3",
        },
        "links": [{"store": "amazon", "asin": "B0B1NNB1DM", "price_eur": 89.00}],
    },
    # ===== Cases — Mini-ITX =====
    {
        "category": "case",
        "brand": "Cooler Master",
        "model": "NR200P",
        "specs": {
            "form_factor": "mini_itx",
            "max_gpu_length_mm": "330",
            "max_cooler_height_mm": "155",
            "included_fans": "2",
        },
        "links": [{"store": "amazon", "asin": "B08BFJX4SN", "price_eur": 89.00}],
    },
    {
        "category": "case",
        "brand": "Fractal Design",
        "model": "Terra",
        "specs": {
            "form_factor": "mini_itx",
            "max_gpu_length_mm": "322",
            "max_cooler_height_mm": "77",
            "included_fans": "1",
        },
        "links": [{"store": "amazon", "asin": "B0CB6CFLGS", "price_eur": 149.00}],
    },
    # ===== Motherboards — Mini-ITX =====
    {
        "category": "motherboard",
        "brand": "Gigabyte",
        "model": "B650I AORUS ULTRA",
        "specs": {
            "socket": "AM5",
            "chipset": "B650",
            "ddr_type": "DDR5",
            "form_factor": "mini_itx",
            "max_ram_gb": "96",
        },
        "links": [{"store": "amazon", "asin": "B083R826VW", "price_eur": 239.00}],
    },
    {
        "category": "motherboard",
        "brand": "ASUS",
        "model": "ROG STRIX B760-I GAMING WIFI",
        "specs": {
            "socket": "LGA1700",
            "chipset": "B760",
            "ddr_type": "DDR5",
            "form_factor": "mini_itx",
            "max_ram_gb": "96",
        },
        "links": [{"store": "amazon", "asin": "B0BNQFXLJR", "price_eur": 219.00}],
    },
    # ===== Cooling — Air =====
    {
        "category": "cooling",
        "brand": "be quiet!",
        "model": "Pure Rock 2",
        "specs": {
            "type": "air",
            "height_mm": "155",
            "tdp_rating": "150",
            "socket_support": "AM5,LGA1700",
        },
        "links": [{"store": "amazon", "asin": "B087VM79LV", "price_eur": 35.00}],
    },
    {
        "category": "cooling",
        "brand": "Noctua",
        "model": "NH-U12S redux",
        "specs": {
            "type": "air",
            "height_mm": "158",
            "tdp_rating": "180",
            "socket_support": "AM5,LGA1700",
        },
        "links": [{"store": "amazon", "asin": "B09K3MMZQL", "price_eur": 49.00}],
    },
    {
        "category": "cooling",
        "brand": "Thermalright",
        "model": "Peerless Assassin 120 SE",
        "specs": {
            "type": "air",
            "height_mm": "155",
            "tdp_rating": "260",
            "socket_support": "AM5,LGA1700",
        },
        "links": [{"store": "amazon", "asin": "B0BXJ5MMHP", "price_eur": 35.00}],
    },
    {
        "category": "cooling",
        "brand": "Noctua",
        "model": "NH-D15",
        "specs": {
            "type": "air",
            "height_mm": "165",
            "tdp_rating": "250",
            "socket_support": "AM5,LGA1700",
        },
        "links": [{"store": "amazon", "asin": "B00L7UZMAK", "price_eur": 99.00}],
    },
    {
        "category": "cooling",
        "brand": "DeepCool",
        "model": "AK400",
        "specs": {
            "type": "air",
            "height_mm": "155",
            "tdp_rating": "220",
            "socket_support": "AM5,LGA1700",
        },
        "links": [{"store": "amazon", "asin": "B0B4NXL2F2", "price_eur": 29.00}],
    },
    # ===== Cooling — Liquid =====
    {
        "category": "cooling",
        "brand": "Arctic",
        "model": "Liquid Freezer II 240",
        "specs": {
            "type": "liquid",
            "radiator_size_mm": "240",
            "tdp_rating": "300",
            "socket_support": "AM5,LGA1700",
        },
        "links": [{"store": "amazon", "asin": "B07WSDLRR3", "price_eur": 69.00}],
    },
    {
        "category": "cooling",
        "brand": "Arctic",
        "model": "Liquid Freezer II 360",
        "specs": {
            "type": "liquid",
            "radiator_size_mm": "360",
            "tdp_rating": "400",
            "socket_support": "AM5,LGA1700",
        },
        "links": [{"store": "amazon", "asin": "B07WPBSP5C", "price_eur": 89.00}],
    },
    {
        "category": "cooling",
        "brand": "Corsair",
        "model": "iCUE H150i Elite LCD XT 360mm",
        "specs": {
            "type": "liquid",
            "radiator_size_mm": "360",
            "tdp_rating": "400",
            "socket_support": "AM5,LGA1700",
        },
        "links": [{"store": "amazon", "asin": "B0D4TN418G", "price_eur": 199.00}],
    },
    # ===== Monitors =====
    {
        "category": "monitor",
        "brand": "LG",
        "model": '27GP850-B 27" 1440p 165Hz IPS',
        "specs": {
            "resolution": "2560x1440",
            "size_inches": "27",
            "panel": "IPS",
            "refresh_hz": "165",
            "response_ms": "1",
        },
        "links": [{"store": "amazon", "asin": "B09QG3SJG3", "price_eur": 279.00}],
    },
    {
        "category": "monitor",
        "brand": "Dell",
        "model": 'S2722DGM 27" 1440p 165Hz VA Curved',
        "specs": {
            "resolution": "2560x1440",
            "size_inches": "27",
            "panel": "VA",
            "refresh_hz": "165",
            "response_ms": "1",
        },
        "links": [{"store": "amazon", "asin": "B09PVZD74D", "price_eur": 249.00}],
    },
    {
        "category": "monitor",
        "brand": "ASUS",
        "model": 'VG27AQ1A 27" 1440p 170Hz IPS',
        "specs": {
            "resolution": "2560x1440",
            "size_inches": "27",
            "panel": "IPS",
            "refresh_hz": "170",
            "response_ms": "1",
        },
        "links": [{"store": "amazon", "asin": "B09GFL94HH", "price_eur": 269.00}],
    },
    {
        "category": "monitor",
        "brand": "LG",
        "model": '24GS60F 24" 1080p 180Hz IPS',
        "specs": {
            "resolution": "1920x1080",
            "size_inches": "24",
            "panel": "IPS",
            "refresh_hz": "180",
            "response_ms": "1",
        },
        "links": [{"store": "amazon", "asin": "B0D2C1FJPB", "price_eur": 139.00}],
    },
    {
        "category": "monitor",
        "brand": "Samsung",
        "model": 'Odyssey G7 S28BG702 28" 4K 144Hz IPS',
        "specs": {
            "resolution": "3840x2160",
            "size_inches": "28",
            "panel": "IPS",
            "refresh_hz": "144",
            "response_ms": "1",
        },
        "links": [{"store": "amazon", "asin": "B0B3H4SK6C", "price_eur": 449.00}],
    },
    # ===== Keyboards =====
    {
        "category": "keyboard",
        "brand": "Logitech",
        "model": "G413 SE Mechanical",
        "specs": {
            "type": "mechanical",
            "switch": "tactile",
            "layout": "full",
            "backlight": "white",
        },
        "links": [{"store": "amazon", "asin": "B09ZK3R3QN", "price_eur": 49.00}],
    },
    {
        "category": "keyboard",
        "brand": "Corsair",
        "model": "K60 PRO TKL RGB",
        "specs": {
            "type": "mechanical",
            "switch": "Corsair OPX",
            "layout": "TKL",
            "backlight": "RGB",
        },
        "links": [{"store": "amazon", "asin": "B0CJZRFWPN", "price_eur": 69.00}],
    },
    {
        "category": "keyboard",
        "brand": "HyperX",
        "model": "Alloy Origins Core TKL",
        "specs": {
            "type": "mechanical",
            "switch": "HyperX Red",
            "layout": "TKL",
            "backlight": "RGB",
        },
        "links": [{"store": "amazon", "asin": "B07YMN61NS", "price_eur": 59.00}],
    },
    # ===== Mice =====
    {
        "category": "mouse",
        "brand": "Logitech",
        "model": "G502 X LIGHTSPEED",
        "specs": {
            "sensor": "HERO 25K",
            "weight_g": "102",
            "wireless": "yes",
            "dpi_max": "25600",
        },
        "links": [{"store": "amazon", "asin": "B0B18GMV71", "price_eur": 89.00}],
    },
    {
        "category": "mouse",
        "brand": "Logitech",
        "model": "G305 LIGHTSPEED",
        "specs": {
            "sensor": "HERO 12K",
            "weight_g": "99",
            "wireless": "yes",
            "dpi_max": "12000",
        },
        "links": [{"store": "amazon", "asin": "B07CMS5Q6P", "price_eur": 39.00}],
    },
    {
        "category": "mouse",
        "brand": "Razer",
        "model": "DeathAdder V3",
        "specs": {
            "sensor": "Focus Pro 30K",
            "weight_g": "59",
            "wireless": "no",
            "dpi_max": "30000",
        },
        "links": [{"store": "amazon", "asin": "B0CY65WFVH", "price_eur": 69.00}],
    },
    {
        "category": "mouse",
        "brand": "SteelSeries",
        "model": "Rival 3",
        "specs": {
            "sensor": "TrueMove Core",
            "weight_g": "77",
            "wireless": "no",
            "dpi_max": "8500",
        },
        "links": [{"store": "amazon", "asin": "B07THJKG53", "price_eur": 29.00}],
    },
]


async def seed_catalog(db: AsyncSession) -> None:
    """Insert seed components and affiliate links. Skips if catalog already has data."""
    count = (await db.execute(text("SELECT count(*) FROM components"))).scalar()
    if count and count > 0:
        log.info("Catalog already has %d components — skipping seed.", count)
        return

    log.info("Seeding %d components...", len(SEED_COMPONENTS))

    for item in SEED_COMPONENTS:
        component = Component(
            category=item["category"],
            brand=item["brand"],
            model=item["model"],
            specs=item["specs"],
            in_stock=True,
        )
        db.add(component)
        await db.flush()  # get component.id

        for link in item["links"]:
            db.add(
                AffiliateLink(
                    component_id=component.id,
                    store=link["store"],
                    url=_amazon_url(link["asin"]),
                    price_eur=link["price_eur"],
                )
            )

    await db.commit()
    log.info("Seeded %d components with affiliate links.", len(SEED_COMPONENTS))


async def _main() -> None:
    """Entry point for `python -m app.db.seed`."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    init_db()

    from app.database import get_db

    async for db in get_db():
        await seed_catalog(db)


if __name__ == "__main__":
    asyncio.run(_main())
