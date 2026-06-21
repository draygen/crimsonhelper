"""
Classifies raw OCR text into categories and extracts structured data.
Uses keyword/regex heuristics tuned for Crimson Desert UI text.
Patterns are compiled once at module load for efficiency.
"""
import re
from dataclasses import dataclass, field

# ── Pre-compiled pattern sets ──────────────────────────────────────────────────

_QUEST_RE = [re.compile(p, re.IGNORECASE) for p in [
    r"\bquest\b", r"\bobjective\b", r"\baccept\b", r"\bcomplete\b",
    r"\breward\b", r"\bmain quest\b", r"\bside quest\b", r"\bdaily quest\b",
    r"\bfailed\b.*quest", r"\bquest\b.*\bfailed\b",
    r"•\s+\w", r"-\s+\w",
]]

_LOOT_RE = [re.compile(p, re.IGNORECASE) for p in [
    r"\bobtained\b", r"\bacquired\b", r"\breceived\b",
    r"\bitem\b.{0,30}\bx\d+", r"\bx\d+\b.{0,30}\bitem\b",
    r"\bdrop\b", r"\bloot\b", r"\bpicked up\b",
    r"(?:[\w\s]+)\s+x\d+",
]]

_NPC_RE = [re.compile(p, re.IGNORECASE) for p in [
    r"\bgreetings\b", r"\btraveler\b", r"\badventurer\b",
    r"\bmerchant\b", r"\bblacksmith\b", r"\bguard\b",
    r"^\w[\w\s]+:[\s\n]",
    r"\[talk\]", r"\[interact\]",
]]

_LOCATION_RE = [re.compile(p, re.IGNORECASE) for p in [
    r"\bzone\b", r"\bregion\b", r"\bcastle\b", r"\bvillage\b",
    r"\bforest\b", r"\bdesert\b", r"\bport\b", r"\btavern\b",
    r"\barea\b", r"\bmap\b",
]]

_ZONE_ENTRY_RE = re.compile(
    r"(?:entering|entered|welcome\s+to|you\s+(?:are\s+)?(?:now\s+)?in)\s+"
    r"([A-Z][A-Za-z'\-\s]{2,30}?)(?:\s*[\|\n\r.,]|$)",
    re.IGNORECASE | re.MULTILINE,
)
_ZONE_LABEL_RE = re.compile(
    r"(?:zone|region|area|district|province|territory)\s*[:\-]\s*"
    r"([A-Z][A-Za-z'\-\s]{2,25}?)(?:\s*[\|\n\r.,]|$)",
    re.IGNORECASE | re.MULTILINE,
)

_QUEST_COMPLETE_RE = re.compile(
    r"quest\s+(?:complete|finished|cleared)|(?:^|\s)completed\s+quest", re.IGNORECASE
)
_QUEST_FAILED_RE = re.compile(
    r"quest\s+failed|mission\s+failed|(?:^|\s)failed\s+quest", re.IGNORECASE
)

_ITEM_RE = re.compile(r"([\w\s\-\']+?)\s+x(\d+)", re.IGNORECASE)
_ITEM_NOUN_RE = re.compile(
    r"\b[A-Z][a-z]{2,}\s?(?:[A-Z][a-z]+)?(?:\s(?:Fragment|Ore|Stone|Crystal|Shard|Dust|Piece))?\b"
)
_NPC_NAME_RE = re.compile(r"^([\w\s]+):\s", re.MULTILINE)


# ── Scoring ────────────────────────────────────────────────────────────────────

def _score(text: str, patterns: list[re.Pattern]) -> int:
    return sum(1 for p in patterns if p.search(text))


def _extract_zone(text: str) -> str:
    for pat in (_ZONE_ENTRY_RE, _ZONE_LABEL_RE):
        m = pat.search(text)
        if m:
            return m.group(1).strip()
    return ""


# ── Data class ─────────────────────────────────────────────────────────────────

@dataclass
class Classification:
    category: str          # quest | loot | npc | general
    confidence: float      # 0–1
    title: str = ""
    description: str = ""
    items: list[str] = field(default_factory=list)
    npc_name: str = ""
    zone: str = ""
    quest_status: str = "active"   # active | completed | failed


# ── Public entry point ─────────────────────────────────────────────────────────

def classify(text: str) -> Classification:
    if not text or text.startswith("[OCR"):
        return Classification(category="general", confidence=0.0)

    zone = _extract_zone(text)

    scores = {
        "quest":    _score(text, _QUEST_RE),
        "loot":     _score(text, _LOOT_RE),
        "npc":      _score(text, _NPC_RE),
        "location": _score(text, _LOCATION_RE),
    }
    best_cat, best_score = max(scores.items(), key=lambda x: x[1])

    if best_score == 0:
        return Classification(category="general", confidence=0.1, zone=zone)

    total = sum(scores.values()) or 1
    confidence = min(best_score / total, 1.0)

    if best_cat == "quest":
        result = _parse_quest(text, confidence)
    elif best_cat == "loot":
        result = _parse_loot(text, confidence)
    elif best_cat == "npc":
        result = _parse_npc(text, confidence)
    else:
        result = Classification(category="general", confidence=confidence)

    if not result.zone and zone:
        result.zone = zone
    return result


# ── Category-specific parsers ──────────────────────────────────────────────────

def _parse_quest(text: str, conf: float) -> Classification:
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    title = lines[0] if lines else "Unknown Quest"
    if len(title) > 80 or title.lower().startswith(("objective", "reward")):
        title = "Unknown Quest"

    description = " ".join(lines[1:5]) if len(lines) > 1 else ""

    quest_status = "active"
    if _QUEST_COMPLETE_RE.search(text):
        quest_status = "completed"
    elif _QUEST_FAILED_RE.search(text):
        quest_status = "failed"

    return Classification(
        category="quest",
        confidence=conf,
        title=title,
        description=description,
        quest_status=quest_status,
    )


def _parse_loot(text: str, conf: float) -> Classification:
    items = [f"{m.group(1).strip()} x{m.group(2)}" for m in _ITEM_RE.finditer(text)
             if m.group(1).strip()]

    if not items:
        items = list(dict.fromkeys(_ITEM_NOUN_RE.findall(text)))[:6]

    return Classification(category="loot", confidence=conf, items=items)


def _parse_npc(text: str, conf: float) -> Classification:
    npc_name = ""
    m = _NPC_NAME_RE.search(text)
    if m:
        npc_name = m.group(1).strip()

    lines = [l.strip() for l in text.splitlines() if l.strip()]
    dialogue = " ".join(lines[:6])
    return Classification(category="npc", confidence=conf, npc_name=npc_name, description=dialogue)
