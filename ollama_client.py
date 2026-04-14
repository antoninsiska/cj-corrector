"""
Grammar correction using the local ufal/byt5-small-geccc-mate model.
Drop-in replacement for the original Ollama client —
exposes the same correct_czech(text, model=None) → dict interface.
"""
import os
import re
import difflib
import warnings

os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"
warnings.filterwarnings("ignore")

MODEL_NAME = "ufal/byt5-small-geccc-mate"

# Module-level cache — valid only within one process lifetime.
# grammar_correct.py is called as a subprocess, so each call reloads,
# but model loading happens once per process in the background thread.
_tokenizer = None
_model = None
_device = None


def _ensure_loaded():
    global _tokenizer, _model, _device
    if _model is not None:
        return

    import torch
    from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
    from transformers import logging as tlog
    tlog.set_verbosity_error()

    _device = "mps" if torch.backends.mps.is_available() else "cpu"
    _tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    _model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_NAME).to(_device)


def _space_tokenize(text: str) -> str:
    """Separate words and punctuation with spaces (model requirement)."""
    tokens = re.findall(r"\w+|[^\w\s]", text, re.UNICODE)
    return " ".join(tokens)


def _compute_mistakes(original: str, corrected: str) -> list:
    """Word-level diff → list of {original, correction} dicts."""
    orig_words = original.split()
    corr_words = corrected.split()
    mistakes = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(
        None, orig_words, corr_words
    ).get_opcodes():
        if tag == "replace":
            mistakes.append(
                {
                    "original": " ".join(orig_words[i1:i2]),
                    "correction": " ".join(corr_words[j1:j2]),
                }
            )
        elif tag == "delete":
            mistakes.append(
                {"original": " ".join(orig_words[i1:i2]), "correction": "∅"}
            )
        elif tag == "insert":
            mistakes.append(
                {"original": "∅", "correction": " ".join(corr_words[j1:j2])}
            )
    return mistakes


def correct_czech(text: str, model=None) -> dict:
    """Correct Czech grammar. model param is ignored (fixed local model)."""
    import torch

    _ensure_loaded()

    prepared = _space_tokenize(text)
    inputs = _tokenizer(prepared, return_tensors="pt").to(_device)

    with torch.no_grad():
        outputs = _model.generate(**inputs, max_new_tokens=256, num_beams=4)

    corrected = _tokenizer.decode(outputs[0], skip_special_tokens=True)
    mistakes = _compute_mistakes(text, corrected)
    return {"corrected": corrected, "mistakes": mistakes}


def get_models() -> list:
    """Kept for API compatibility."""
    return [MODEL_NAME]


# ── download helper (called by setup.sh) ──────────────────────────────────────

def download_model():
    """Download model if not already cached. Ignores OFFLINE flag."""
    os.environ.pop("TRANSFORMERS_OFFLINE", None)
    import torch
    from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
    from transformers import logging as tlog
    tlog.set_verbosity_error()
    print(f"Downloading {MODEL_NAME} …")
    AutoTokenizer.from_pretrained(MODEL_NAME)
    AutoModelForSeq2SeqLM.from_pretrained(MODEL_NAME)
    print("Model ready.")


if __name__ == "__main__":
    download_model()
