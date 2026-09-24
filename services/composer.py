"""Composer: the single source of user-facing sentences.

Sentences come from config/templates/responses.<locale>.yaml. Only verified
claims are placed into template slots; a claim whose slot has no template is
dropped. Every rendered line keeps the key of the source that backs it.
"""
from __future__ import annotations

from functools import lru_cache

import yaml

from core.protocol import Claim
from core.settings import DEFAULT_LOCALE, TEMPLATES_DIR


@lru_cache
def load_templates(locale: str) -> dict:
    path = TEMPLATES_DIR / f"responses.{locale}.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


class _Blank(dict):
    def __missing__(self, key):
        return ""


class Composer:
    def __init__(self, locale: str = DEFAULT_LOCALE):
        self.tpl = load_templates(locale)

    def question(self, key: str) -> str:
        return self.tpl["questions"][key]

    def abstain_text(self) -> str:
        return self.tpl["abstain"]

    def render(self, scenario: str, claims: list[Claim]) -> dict:
        spec = self.tpl["results"][scenario]
        by_slot: dict[str, list[Claim]] = {}
        for c in claims:
            by_slot.setdefault(c.slot, []).append(c)

        used: list[str] = []

        summary = []
        for field in spec["summary"]:
            for c in by_slot.get(field["slot"], [])[:1]:
                summary.append({"label": field["label"], "value": self._label(c.value),
                                "source": c.source.key})
                used.append(c.source.key)

        sections = []
        for section in spec["sections"]:
            items = []
            for c in by_slot.get(section["slot"], []):
                text = section["item"].format_map(_Blank(c.value)).strip()
                items.append({"text": " ".join(text.split()), "source": c.source.key})
                used.append(c.source.key)
            if items:
                sections.append({"heading": section["heading"], "items": items})

        return {
            "scenario": scenario,
            "title": spec["title"],
            "summary": summary,
            "sections": sections,
            "sources": list(dict.fromkeys(used)),
            "disclaimer": self.tpl["disclaimer"],
        }

    def _label(self, value) -> str:
        return self.tpl["labels"].get(value, value) if isinstance(value, str) else str(value)
