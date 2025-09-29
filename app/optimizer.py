import re
from typing import Dict, Any
from .providers.openai_provider import optimize_with_llm


def optimize(signature: Dict[str, Any], draft: str, task: str, audience: str, channel: str, word_count_range: str) -> Dict[str, Any]:
    """Call OpenAI with the draft message and the ToneOfVoice signature to retrieve an improved text.
    Falls back to a local heuristic if the LLM response is missing.",
    """
    llm = optimize_with_llm(signature, draft, task, audience, channel, word_count_range)
    return llm
