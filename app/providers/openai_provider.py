import os, json
from typing import Any, Dict, List, Optional
from openai import OpenAI

MODEL = "gpt-4o-mini"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


def chat(messages: List[Dict[str, str]], response_format: Optional[Dict[str, Any]] = None) -> str:
    cli = OpenAI()
    params = {"model": MODEL, "messages": messages}
    if response_format:
        params["response_format"] = response_format
    resp = cli.chat.completions.create(**params)
    return resp.choices[0].message.content

def synthesize_signature(metrics, examples, brand, languages):
    sys = {"role":"system","content":(
        "You are a careful editorial scientist. "
        "Return STRICT JSON for ToneOfVoiceSignature with ALL required fields populated. "
        "tone[] and language_style[] must be non-empty arrays. "
        "emotional_appeal must include reassurance, confidence, excitement, empathy, restraint in [0,1]. "
        "address_forms must include the primary language with allowed/banned lists. "
        "Use enforceable, concise values. No extra keys."
    )}
    user = {"role":"user","content": json.dumps({
        "JSON_SCHEMA": metrics.get("json_schema", {}),
        "METRICS": metrics,
        "EXAMPLES": examples,
        "Brand": brand,
        "Languages": languages
    }, ensure_ascii=False)}
    out = chat([sys,user], response_format={"type":"json_object"})
    return json.loads(out)


def optimize_with_llm(signature: Dict[str, Any], draft: str, task: str, audience: str, channel: str, word_count_range: str) -> Dict[str, Any]:
    sys = {"role":"system","content":"You rewrite text to match a ToneOfVoiceSignature. Never invent facts. Keep within word_count_range. Return JSON with improved_text and self_check."}
    user = {"role":"user","content": json.dumps({
        "signature": signature,
        "task_description": task,
        "draft_text": draft,
        "audience": audience,
        "channel": channel,
        "word_count_range": word_count_range
    }, ensure_ascii=False)}
    out = chat([sys,user], response_format={"type":"json_object"})
    return json.loads(out)
