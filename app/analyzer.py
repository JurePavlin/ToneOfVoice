# /app/analyzer.py
import os, re, statistics
from typing import Any, Dict, List, Tuple

# --- optional deps; fail-soft ---
try:
    from langdetect import detect
except Exception:
    detect = None

try:
    import spacy
except Exception:
    spacy = None

try:
    from sentence_transformers import SentenceTransformer
    import numpy as np  # noqa: F401
    from sklearn.cluster import KMeans
except Exception:
    SentenceTransformer = None

try:
    import textstat
except Exception:
    textstat = None

# use the same provider the rest of the app uses
from .providers.openai_provider import synthesize_signature
from .tov_signature import JSON_SCHEMA

USE_SPACY = os.getenv("TOV_USE_SPACY", "1") == "1"
_nlp = None

def _get_nlp():
    global _nlp
    if not USE_SPACY or spacy is None:
        return None
    if _nlp is None:
        try:
            _nlp = spacy.blank("xx")
            if "sentencizer" not in _nlp.pipe_names:
                _nlp.add_pipe("sentencizer")
        except Exception:
            _nlp = None
    return _nlp

def _sentences(text: str) -> List[str]:
    nlp = _get_nlp()
    if nlp is not None:
        try:
            return [s.text.strip() for s in nlp(text).sents if s.text.strip()]
        except Exception:
            pass
    return [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]

def _readability(text: str) -> float:
    if textstat:
        try:
            return float(textstat.flesch_reading_ease(text))
        except Exception:
            pass
    # simple heuristic fallback (higher ≈ easier)
    words = max(1, len(re.findall(r"\w+", text)))
    sents = max(1, len(_sentences(text)))
    avg = words / sents
    return max(0.0, 120 - avg * 8.0)

ADDRESS_FORMS = {
    "en": ["you","sir","madam","y'all","dear"],
    "de": ["Sie","Du"],
    "fr": ["vous","tu"],
    "es": ["usted","ustedes","tú"]
}

def _address_stats(texts: List[str], lang: str) -> Dict[str, int]:
    keys = ADDRESS_FORMS.get(lang, [])
    counts = {k: 0 for k in keys}
    for t in texts:
        for k in keys:
            counts[k] += len(re.findall(rf"\b{k}\b", t, flags=re.I))
    return counts

def _embedding_clusters(snippets: List[str], k: int = 3) -> Tuple[List[int], List[str]]:
    if SentenceTransformer:
        try:
            model = SentenceTransformer("all-MiniLM-L6-v2")
            X = model.encode(snippets)
            labels = KMeans(n_clusters=min(k, max(1, len(set(snippets)))))
            labels = labels.fit_predict(X)
            return labels.tolist(), [f"cluster_{i}" for i in sorted(set(labels))]
        except Exception:
            pass
    # fallback: length buckets
    labels = [0 if len(s) < 80 else (1 if len(s) < 160 else 2) for s in snippets]
    return labels, ["short","medium","long"]

def analyze_corpus(corpus, lang_hint: str | None = None, brand: str = "UnknownBrand") -> Dict[str, Any]:
    """
    LLM-driven analyzer:
      - Accepts either a raw string with several sentences or a list of snippets.
      - Computes light metrics (language, readability, punctuation, clusters).
      - Builds a JSON object conforming to JSON_SCHEMA by asking the OpenAI LLM
        to fill each required field.
    Returns: { metrics, examples, signature }
    """
    # normalize input: allow a raw string with several sentences or a list of snippets
    if isinstance(corpus, str):
        corpus = [s for s in _sentences(corpus) if s]
    elif isinstance(corpus, list):
        corpus = [c for c in corpus if isinstance(c, str) and c.strip()]
    else:
        corpus = []

    if not corpus:
        raise ValueError("Corpus is empty.")

    # --- language detection (fail-soft) ---
    langs = []
    for t in corpus:
        try:
            langs.append(lang_hint or (detect(t) if detect else "en"))
        except Exception:
            langs.append(lang_hint or "en")
    top_lang = max(set(langs), key=langs.count) if langs else (lang_hint or "en")

    # --- basic stats ---
    sents = [s for t in corpus for s in _sentences(t)]
    avg_len = statistics.mean([len(re.findall(r"\w+", s)) for s in sents]) if sents else 12
    exclam = sum(t.count("!") for t in corpus)
    emojis = sum(len(re.findall(r"[\U0001F300-\U0001FAFF]", t)) for t in corpus)
    read = _readability(" ".join(corpus))
    addr = _address_stats(corpus, top_lang)
    labels, names = _embedding_clusters(sents[:200])  # cap cost

    metrics: Dict[str, Any] = {
        "detected_languages": {l: langs.count(l) for l in set(langs)},
        "primary_language": top_lang,
        "avg_sentence_length": avg_len,
        "readability": read,
        "punctuation": {"exclamations": exclam, "emojis": emojis},
        "address_counts": addr,
        "clusters": {"names": names, "sample_size": len(sents)},
        # include the JSON schema so the LLM fills each required field explicitly
        "json_schema": JSON_SCHEMA,
    }

    # --- choose representative examples: shortest per cluster ---
    cluster_to_examples = []
    for i, s in enumerate(sents[:500]):
        cluster_to_examples.append((labels[i % len(labels)] if labels else 0, len(s), s))
    cluster_to_examples.sort(key=lambda x: (x[0], x[1]))
    examples = [e[2] for e in cluster_to_examples[:8]] if cluster_to_examples else corpus[:4]

    # --- LLM synthesis of the signature (no hard-coded values here) ---
    signature = synthesize_signature(metrics, examples, brand, [top_lang])

    return {"metrics": metrics, "examples": examples, "signature": signature}
