#!/usr/bin/env python3
"""
Bangla Text Normalization Service  (Port 8006)
────────────────────────────────────────────────
Fixes phonetic variants, common typos, mixed-script digits, and Unicode noise
before text reaches the RAG retrieval pipeline.

Why this matters:
  "ব্যথা" vs "বেথা" vs "বেদনা" — same concept, different spellings.
  Normalizing before embedding → better cosine similarity → more relevant chunks.

Endpoints:
  POST /normalize          { "text": "…" }  → { "normalized": "…", "changes": n }
  POST /normalize-batch    { "texts": […] } → { "results": […] }
  GET  /rules              → list of active normalization rules
  GET  /health
"""

import re
import logging
from typing import Any, Dict, List, Tuple

from fastapi import FastAPI
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("bangla-normalizer")

# ── Normalization rules ────────────────────────────────────────────────────────
# Each rule: (pattern, replacement, description)
# Patterns are compiled once at startup.

_RAW_RULES: List[Tuple[str, str, str]] = [

    # ── 1. Unicode normalization: visually identical but different code points ──
    (r"\u09DC", "ড়",  "Normalize ড় (0x09DC → canonical)"),
    (r"\u09DD", "ঢ়",  "Normalize ঢ় (0x09DD → canonical)"),
    (r"\u09DF", "য়",  "Normalize য় (0x09DF → canonical)"),

    # ── 2. Arabic-Indic / ASCII digits → Bengali digits ──────────────────────
    (r"[\u0660-\u0669]",   lambda m: chr(0x09E6 + ord(m.group()) - 0x0660), "Arabic-Indic → Bengali digits"),
    (r"0", "০", "ASCII 0 → Bengali"),
    (r"1", "১", "ASCII 1 → Bengali"),
    (r"2", "২", "ASCII 2 → Bengali"),
    (r"3", "৩", "ASCII 3 → Bengali"),
    (r"4", "৪", "ASCII 4 → Bengali"),
    (r"5", "৫", "ASCII 5 → Bengali"),
    (r"6", "৬", "ASCII 6 → Bengali"),
    (r"7", "৭", "ASCII 7 → Bengali"),
    (r"8", "৮", "ASCII 8 → Bengali"),
    (r"9", "৯", "ASCII 9 → Bengali"),

    # ── 3. Common phonetic typo variants → canonical spellings ───────────────
    # Pain / ache
    (r"বেথা",    "ব্যথা",  "বেথা → ব্যথা"),
    (r"ব্যাথা",  "ব্যথা",  "ব্যাথা → ব্যথা"),
    (r"বেদনা",   "ব্যথা",  "বেদনা → ব্যথা"),

    # Fever
    (r"জ্বর",   "জ্বর",   "জ্বর (already canonical — no-op placeholder)"),
    (r"জর",     "জ্বর",   "জর → জ্বর"),
    (r"জোর",    "জ্বর",   "জোর → জ্বর (fever context)"),

    # Cough
    (r"কাশি",   "কাশি",   "canonical"),
    (r"কাশী",   "কাশি",   "কাশী → কাশি"),
    (r"খকখক",   "কাশি",   "খকখক → কাশি"),

    # Headache
    (r"মাথা\s*ব্যথা",  "মাথাব্যথা",  "Merge spaced মাথা ব্যথা"),
    (r"মাথা\s*বেদনা",  "মাথাব্যথা",  "মাথা বেদনা → মাথাব্যথা"),

    # Stomach
    (r"পেট\s*ব্যথা",   "পেটব্যথা",   "Merge পেট ব্যথা"),
    (r"পেটে\s*ব্যথা",  "পেটব্যথা",   "পেটে ব্যথা → পেটব্যথা"),
    (r"গ্যাস্ট্রিক",  "গ্যাস্ট্রিক", "canonical"),
    (r"গ্যাসট্রিক",   "গ্যাস্ট্রিক", "গ্যাসট্রিক → গ্যাস্ট্রিক"),

    # Diarrhea / dysentery
    (r"পাতলা\s*পায়খানা", "ডায়রিয়া", "পাতলা পায়খানা → ডায়রিয়া"),
    (r"ডাইরিয়া",         "ডায়রিয়া", "ডাইরিয়া → ডায়রিয়া"),
    (r"পেট\s*খারাপ",      "ডায়রিয়া", "পেট খারাপ → ডায়রিয়া"),

    # Diabetes
    (r"ডায়বেটিস",  "ডায়াবেটিস", "ডায়বেটিস → ডায়াবেটিস"),
    (r"সুগার",      "ডায়াবেটিস", "সুগার → ডায়াবেটিস"),

    # Asthma
    (r"হাঁপানি",    "হাঁপানি",   "canonical"),
    (r"শ্বাসকষ্ট", "শ্বাসকষ্ট", "canonical"),
    (r"শ্বাস\s*কষ্ট", "শ্বাসকষ্ট", "Merge শ্বাস কষ্ট"),

    # Blood pressure
    (r"ব্লাড\s*প্রেশার",   "রক্তচাপ",  "ব্লাড প্রেশার → রক্তচাপ"),
    (r"হাই\s*প্রেশার",     "উচ্চ রক্তচাপ", "হাই প্রেশার → উচ্চ রক্তচাপ"),
    (r"লো\s*প্রেশার",      "নিম্ন রক্তচাপ", "লো প্রেশার → নিম্ন রক্তচাপ"),

    # ── 4. Remove zero-width & control characters ─────────────────────────────
    (r"[\u200B-\u200D\uFEFF]", "", "Remove zero-width chars"),
    (r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", "Remove control chars"),

    # ── 5. Normalize whitespace ───────────────────────────────────────────────
    (r"\s{2,}", " ", "Collapse multiple spaces"),
]


class _Rule:
    """Compiled normalization rule."""
    __slots__ = ("pattern", "replacement", "description", "_re")

    def __init__(self, pattern: str, replacement, description: str):
        self.pattern = pattern
        self.replacement = replacement
        self.description = description
        self._re = re.compile(pattern)

    def apply(self, text: str) -> Tuple[str, int]:
        """Apply rule; return (new_text, n_substitutions)."""
        if callable(self.replacement):
            result, n = self._re.subn(self.replacement, text)
        else:
            result, n = self._re.subn(self.replacement, text)
        return result, n


_RULES: List[_Rule] = [_Rule(p, r, d) for p, r, d in _RAW_RULES]


# ── Normalization function ─────────────────────────────────────────────────────

def normalize(text: str) -> Dict[str, Any]:
    """
    Apply all rules in order. Returns normalized text and total change count.
    """
    if not text or not text.strip():
        return {"normalized": text, "changes": 0}

    result = text.strip()
    total_changes = 0
    applied: List[str] = []

    for rule in _RULES:
        new_text, n = rule.apply(result)
        if n > 0:
            total_changes += n
            applied.append(f"{rule.description} (×{n})")
            result = new_text

    return {
        "normalized": result,
        "changes": total_changes,
        "rules_applied": applied,
    }


# ── FastAPI ────────────────────────────────────────────────────────────────────
app = FastAPI(title="Bangla Text Normalizer", version="1.0.0")


class NormalizeRequest(BaseModel):
    text: str


class NormalizeBatchRequest(BaseModel):
    texts: List[str]


@app.post("/normalize")
async def normalize_text(req: NormalizeRequest):
    """Normalize a single Bangla text string."""
    return normalize(req.text)


@app.post("/normalize-batch")
async def normalize_batch(req: NormalizeBatchRequest):
    """Normalize a list of texts. Returns list in same order."""
    results = [normalize(t) for t in req.texts]
    return {
        "results": results,
        "total_texts": len(results),
        "total_changes": sum(r["changes"] for r in results),
    }


@app.get("/rules")
async def list_rules():
    """Return all active normalization rules."""
    return {
        "total_rules": len(_RULES),
        "rules": [
            {"pattern": r.pattern, "description": r.description}
            for r in _RULES
        ],
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "bangla-normalizer", "rules_loaded": len(_RULES)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8006)
