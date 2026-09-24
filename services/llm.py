"""Optional LLM fallback for signal extraction.

The model is asked to pick values from fixed vocabularies only. Any value
outside those vocabularies is discarded, so the model can never introduce a
new fact — it can only help map unusual phrasing onto known codes.
"""
from __future__ import annotations

import json
import logging

log = logging.getLogger(__name__)

PROMPT = """You map a UAE business description onto fixed vocabularies.
Return ONLY a JSON object with these keys; use null when the text does not say:
{fields}
Never invent values outside the lists."""


class LLMExtractor:
    def __init__(self, api_key: str, model: str):
        from openai import OpenAI  # optional dependency

        self.client = OpenAI(api_key=api_key)
        self.model = model

    def extract(self, text: str, vocab: dict[str, list[str]]) -> dict:
        fields = "\n".join(f'"{k}": one of {v} or null' for k, v in vocab.items())
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                temperature=0.0,
                response_format={"type": "json_object"},
                messages=[{"role": "system", "content": PROMPT.format(fields=fields)},
                          {"role": "user", "content": text}],
            )
            data = json.loads(resp.choices[0].message.content or "{}")
        except Exception as exc:  # network, auth or parse errors → no signal
            log.warning("LLM extraction failed: %s", exc)
            return {}
        return {k: data.get(k) for k, allowed in vocab.items() if data.get(k) in allowed}


def build_llm(api_key: str, model: str) -> LLMExtractor | None:
    if not api_key:
        return None
    try:
        return LLMExtractor(api_key, model)
    except ImportError:
        log.warning("OPENAI_API_KEY is set but the 'openai' package is not installed")
        return None
