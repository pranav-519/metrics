import re
from dataclasses import dataclass
from typing import Dict, Any, Optional

@dataclass
class NormalizedTextResult:
    original_text: str
    normalized_text: str
    tokens: list

class TextNormalizer:
    """
    Normalizes packaging OCR text variations while strictly preserving original OCR text.
    Handles noisy punctuation, currency symbols, quantity units, entity prefixes,
    and packaging date indicators.
    """

    # Currency normalization patterns
    CURRENCY_MAP = {
        re.compile(r'(?:\b(?:Rs\.?|RS|INR)\b|₹|\bRs\b)', re.IGNORECASE): "₹",
        re.compile(r'₹\s*/?-?', re.IGNORECASE): "₹",
    }

    # Unit normalization patterns
    UNIT_CANONICAL = {
        "g": "g", "gm": "g", "gms": "g", "gram": "g", "grams": "g",
        "kg": "kg", "kgs": "kg", "kilogram": "kg", "kilograms": "kg",
        "mg": "mg", "mgs": "mg", "milligram": "mg",
        "ml": "ml", "m.l.": "ml", "millilitre": "ml", "millilitres": "ml",
        "l": "L", "ltr": "L", "litre": "L", "litres": "L",
        "cm": "cm", "m": "m", "mm": "mm", "n": "units", "u": "units", "pc": "units", "pcs": "units"
    }

    @classmethod
    def normalize_string(cls, text: str) -> NormalizedTextResult:
        """
        Takes raw OCR text, performs safe normalization without modifying original text,
        and returns both original and normalized representations.
        """
        if not text:
            return NormalizedTextResult(original_text="", normalized_text="", tokens=[])

        original = text
        normalized = original

        # Clean OCR artifacts: normalize smart quotes, odd dashes, repeated spaces, stray pipes
        normalized = re.sub(r'[\u2018\u2019\u201a\u201b]', "'", normalized)
        normalized = re.sub(r'[\u201c\u201d\u201e\u201f]', '"', normalized)
        normalized = re.sub(r'[\u2013\u2014]', '-', normalized)
        normalized = re.sub(r'\s*\|\s*', ' ', normalized)
        normalized = re.sub(r'[ \t]+', ' ', normalized).strip()

        # MRP normalization
        normalized = re.sub(
            r'\b(?:M\.?\s*R\.?\s*P\.?|MAX(?:IMUM)?\s+RETAIL\s+PRICE)\b',
            'MRP',
            normalized,
            flags=re.IGNORECASE
        )

        # Currency normalization (Rs, Rs., INR -> ₹)
        normalized = re.sub(r'\b(?:Rs\.?|RS|INR)\b\s*', '₹', normalized, flags=re.IGNORECASE)
        normalized = re.sub(r'₹\s+', '₹', normalized)

        # Net Quantity keyword normalization
        normalized = re.sub(
            r'\b(?:NET\s+(?:QTY|QUANTITY|WT\.?|WEIGHT|VOL\.?|VOLUME|CONTENTS?)|N\.?\s*W\.?)\b',
            'NET_QTY',
            normalized,
            flags=re.IGNORECASE
        )

        # Manufacturing / Packing date label normalization
        normalized = re.sub(
            r'\b(?:MFD\.?|MFG\.?\s*DATE|DATE\s+OF\s+MFG\.?|MANUFACTURED\s+ON)\b',
            'MFD_LABEL',
            normalized,
            flags=re.IGNORECASE
        )
        normalized = re.sub(
            r'\b(?:PKD\.?|PKG\.?\s*DATE|DATE\s+OF\s+P(?:AC)?K(?:IN)?G|PACKED\s+ON)\b',
            'PKD_LABEL',
            normalized,
            flags=re.IGNORECASE
        )
        normalized = re.sub(
            r'\b(?:EXP\.?\s*DATE|EXPIRY\s+DATE|EXPIRY|DATE\s+OF\s+EXPIRY|USE\s+BEFORE)\b',
            'EXP_LABEL',
            normalized,
            flags=re.IGNORECASE
        )
        normalized = re.sub(
            r'\b(?:BEST\s+BEFORE|BB)\b',
            'BEST_BEFORE_LABEL',
            normalized,
            flags=re.IGNORECASE
        )

        # Manufacturer / Packer / Importer normalization
        normalized = re.sub(
            r'\b(?:MANUFACTURED\s+&\s+MARKETED\s+BY|MANUFACTURED\s+(?:BY|AT)|MFD\.?\s+BY|MFG\.?\s+BY)\b',
            'MFG_BY',
            normalized,
            flags=re.IGNORECASE
        )
        normalized = re.sub(
            r'\b(?:PACKED\s+(?:BY|AT)|PKD\.?\s+BY)\b',
            'PKD_BY',
            normalized,
            flags=re.IGNORECASE
        )
        normalized = re.sub(
            r'\b(?:IMPORTED\s+(?:&\s+MARKETED\s+)?BY|IMPORTER\s*:?)\b',
            'IMP_BY',
            normalized,
            flags=re.IGNORECASE
        )

        # Consumer Care normalization
        normalized = re.sub(
            r'\b(?:CONSUMER\s+(?:CARE|CELL|HELPLINE)|CUSTOMER\s+(?:CARE|SUPPORT|SERVICE)|TOLL\s+FREE)\b',
            'CONSUMER_CARE_LABEL',
            normalized,
            flags=re.IGNORECASE
        )

        # Country of Origin normalization
        normalized = re.sub(
            r'\b(?:COUNTRY\s+OF\s+ORIGIN|MADE\s+IN|PRODUCT\s+OF)\b',
            'COUNTRY_ORIGIN_LABEL',
            normalized,
            flags=re.IGNORECASE
        )

        tokens = normalized.split()
        return NormalizedTextResult(
            original_text=original,
            normalized_text=normalized,
            tokens=tokens
        )

    @classmethod
    def canonicalize_unit(cls, raw_unit: str) -> str:
        """
        Safely standardizes common unit representations (e.g. 'gms' -> 'g', 'mL' -> 'ml').
        """
        if not raw_unit:
            return ""
        cleaned = raw_unit.lower().strip().rstrip(".")
        return cls.UNIT_CANONICAL.get(cleaned, raw_unit.strip())
