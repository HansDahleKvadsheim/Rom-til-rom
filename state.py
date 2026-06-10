"""
state.py — Delt server-tilstand og autosave

Holder én enkelt global instans av timeplanen som HTTP-handleren
leser og skriver, beskyttet av en threading.Lock.
"""

import json
import threading
from pathlib import Path

from models import Participant

AUTOSAVE_FILE = Path("timeplan_autosave.json")

_lock = threading.Lock()
_participants: list[Participant] = []
_version: int = 0


# ── Lese ──────────────────────────────────────────

def get_participants() -> list[Participant]:
    """Returnerer en kopi av deltakerlisten (trådsikker)."""
    with _lock:
        return list(_participants)


def get_version() -> int:
    with _lock:
        return _version


# ── Skrive ────────────────────────────────────────

def set_participants(ps: list[Participant]) -> None:
    """Oppdater tilstand og autosave til disk (trådsikker)."""
    global _participants, _version
    with _lock:
        _participants = ps
        _version += 1
    _autosave(ps)


# ── Autosave ──────────────────────────────────────

def _autosave(ps: list[Participant]) -> None:
    try:
        data = json.dumps([p.to_dict() for p in ps], indent=2, ensure_ascii=False)
        AUTOSAVE_FILE.write_text(data, encoding="utf-8")
    except Exception as e:
        print(f"  [autosave feil] {e}")


def load_autosave() -> list[Participant] | None:
    """
    Prøv å laste siste autosave fra disk.
    Returnerer None hvis filen ikke finnes eller er korrupt.
    """
    if not AUTOSAVE_FILE.exists():
        return None
    try:
        data = json.loads(AUTOSAVE_FILE.read_text(encoding="utf-8"))
        return [Participant.from_dict(d) for d in data]
    except Exception as e:
        print(f"  [autosave les-feil] {e}")
        return None


# ── JSON-import ───────────────────────────────────

def participants_from_json(text: str) -> list[Participant]:
    """Parse JSON-tekst til deltakerliste."""
    data = json.loads(text)
    return [Participant.from_dict(d) for d in data]


def participants_to_json(ps: list[Participant], indent: int = 2) -> str:
    return json.dumps([p.to_dict() for p in ps], indent=indent, ensure_ascii=False)
