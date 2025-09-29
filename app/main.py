from fastapi import FastAPI
from pydantic import BaseModel
from typing import Any, Dict, List, Union
from .analyzer import analyze_corpus
from .tov_signature import ToneOfVoiceSignature, JSON_SCHEMA
from .optimizer import optimize

app = FastAPI(title="ToV Module")

# ---- Request / Response Models ----

class AnalyzeIn(BaseModel):
    # Accept either a raw string with several sentences or a list of snippets
    corpus: Union[str, List[str]]
    lang: Union[str, None] = None
    brand: str = "UnknownBrand"

class AnalyzeOut(BaseModel):
    metrics: Dict[str, Any]
    examples: List[str]
    signature: Dict[str, Any]  # We return the dict so client isn't tightly coupled

class OptimizeIn(BaseModel):
    draft: str
    signature: Dict[str, Any]  # Accept plain dict; callers can send ToneOfVoiceSignature.model_dump()
    task: str = ""
    audience: str = ""
    channel: str = ""
    word_count_range: str = "60-120"

class OptimizeOut(BaseModel):
    improved_text: str
    self_check: Any

class ScoreIn(BaseModel):
    text: str
    signature: Dict[str, Any]

class ScoreOut(BaseModel):
    score: int
    feedback: Dict[str, Any]


# ---- Routes ----

@app.post("/analyze", response_model=AnalyzeOut)
def route_analyze(payload: AnalyzeIn) -> AnalyzeOut:
    out = analyze_corpus(payload.corpus, lang_hint=payload.lang, brand=payload.brand)
    return AnalyzeOut(metrics=out["metrics"], examples=out["examples"], signature=out["signature"])

@app.post("/optimize", response_model=OptimizeOut)
def route_optimize(payload: OptimizeIn) -> OptimizeOut:
    res = optimize(
        signature=payload.signature,
        draft=payload.draft,
        task=payload.task,
        audience=payload.audience,
        channel=payload.channel,
        word_count_range=payload.word_count_range,
    )
    return OptimizeOut(improved_text=res.get("improved_text",""), self_check=res.get("self_check"))

# A small heuristic scorer for debug/QA
import re

def _score(text: str, sig: Dict[str, Any]) -> Dict[str, Any]:
    pts, total = 0, 5

    # 1) exclamations
    exclam = text.count("!")
    cap = sig.get("punctuation_cadence",{}).get("exclamation_max_per_1000w", 2)
    if exclam <= cap:
        pts += 1

    # 2) emoji policy
    policy = sig.get("emoji_policy","none")
    has_emoji = bool(re.search(r"[\U0001F300-\U0001FAFF]", text))
    cond = (policy == "allow") or (policy == "none" and not has_emoji)
    if cond:
        pts += 1

    # 3) formality
    formal = sig.get("formality_level","neutral")
    informal_markers = len(re.findall(r"\b(hey|guys|lol|haha)\b", text, flags=re.I))
    if (formal != "formal") or (informal_markers == 0):
        pts += 1

    # 4) address forms (very light check)
    ok = True
    for lang, pol in (sig.get("address_forms") or {}).items():
        for b in pol.get("banned", []):
            if re.search(rf"\b{re.escape(b)}\b", text, flags=re.I):
                ok = False
                break
        if not ok:
            break
    if ok:
        pts += 1

    # 5) sentence length
    words = len(re.findall(r"\w+", text))
    sentences = max(1, len(re.split(r"[.!?]", text)))
    avg_sent_len = words / sentences
    slr = sig.get("sentence_length_range")
    if not slr or (slr[0] <= avg_sent_len <= slr[1]):
        pts += 1

    score = round((pts/total)*100)
    feedback = {
        "exclamation_ok": exclam <= cap,
        "emoji_policy_ok": cond,
        "formality_ok": (formal != "formal") or (informal_markers == 0),
        "address_forms_ok": ok,
        "sentence_length_ok": True if not slr else (slr[0] <= avg_sent_len <= slr[1]),
    }
    return {"score": score, "feedback": feedback}

@app.post("/score", response_model=ScoreOut)
def route_score(payload: ScoreIn) -> ScoreOut:
    s = _score(payload.text, payload.signature)
    return ScoreOut(score=s["score"], feedback=s["feedback"])

# Optional: healthcheck
@app.get("/health")
def route_health():
    return {"ok": True, "schema": JSON_SCHEMA}
