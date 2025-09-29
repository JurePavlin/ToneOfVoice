import re
from typing import Dict, Any
from .providers.openai_provider import optimize_with_llm

def _heuristic_optimize(signature: Dict[str, Any], draft: str) -> str:
    text = draft
    # emoji policy
    if signature.get("emoji_policy","none")=="none":
        text = re.sub(r"[\U0001F300-\U0001FAFF]", "", text)
    # exclamation cap
    pc = signature.get("punctuation_cadence",{})
    cap = pc.get("exclamation_max_per_1000w", 2) if pc else 2
    if text.count("!") > cap:
        text = text.replace("!", ".")
    # formality adjustments
    level = signature.get("formality_level","neutral")
    if level=="formal":
        text = re.sub(r"\bhey\b", "Hello", text, flags=re.I)
        text = re.sub(r"\bguys\b", "everyone", text, flags=re.I)
        text = re.sub(r"\bcan't\b", "cannot", text, flags=re.I)
    if level=="informal":
        text = re.sub(r"\bdo not\b", "don’t", text, flags=re.I)
    # address forms
    for lang, pol in (signature.get("address_forms") or {}).items():
        for b in pol.get("banned", []):
            text = re.sub(rf"\b{re.escape(b)}\b", pol.get("allowed",[ "you" ])[0], text, flags=re.I)
    # sentence length band
    slr = signature.get("sentence_length_range")
    if slr:
        # dumb split/join to avoid very long sentences
        sents = re.split(r'(?<=[.!?])\s+', text)
        sents = [s.strip() for s in sents if s.strip()]
        out = []
        for s in sents:
            words = s.split()
            if len(words) > slr[1]:
                out.append(" ".join(words[:slr[1]]))
            else:
                out.append(s)
        text = " ".join(out)
    return text.strip()

def optimize(signature: Dict[str, Any], draft: str, task: str, audience: str, channel: str, word_count_range: str) -> Dict[str, Any]:
    """Call OpenAI with the draft message and the ToneOfVoice signature to retrieve an improved text.
    Falls back to a local heuristic if the LLM response is missing.",
    """
    llm = optimize_with_llm(signature, draft, task, audience, channel, word_count_range)
    if llm.get("improved_text"):
        return llm
    # fallback heuristic
    improved = _heuristic_optimize(signature, draft)
    return {"improved_text": improved, "self_check": "heuristic_fallback"}
