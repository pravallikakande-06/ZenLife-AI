"""Optional LLM integration. Supports Anthropic, OpenAI-compatible APIs, and local Ollama.
If nothing is configured or a call fails, ask() returns (None, reason) and callers use rule-based fallbacks.
No AI responses are ever fabricated."""
import requests

from utils import config

SYSTEM_PROMPT = (
    "You are ZenLife AI, a friendly general-wellness assistant covering nutrition, exercise, hydration, sleep, "
    "stress and healthy habits. You are NOT a doctor: never diagnose, never suggest or change medication or doses, "
    "and never present estimates as exact. Keep advice general, cautious and practical, and concise (under 250 words). "
    "Use the user's context only when relevant. For symptoms, injuries, eating-disorder or self-harm concerns, or "
    "emergencies, encourage contacting a qualified professional or local emergency services."
)
DEFAULT_MODELS = {"anthropic": "claude-sonnet-5-5", "openai": "gpt-4o-mini", "ollama": "llama3.1"}


def _settings():
    provider = (config.get("AI_PROVIDER") or "").strip().lower()
    if not provider:
        if config.get("ANTHROPIC_API_KEY"):
            provider = "anthropic"
        elif config.get("OPENAI_API_KEY"):
            provider = "openai"
    if provider not in DEFAULT_MODELS:
        return None
    key = config.get("ANTHROPIC_API_KEY") if provider == "anthropic" else config.get("OPENAI_API_KEY")
    if provider != "ollama" and not key:
        return None
    model = config.get("AI_MODEL") or DEFAULT_MODELS[provider]
    base = config.get("OPENAI_BASE_URL") or ("http://localhost:11434/v1" if provider == "ollama" else "https://api.openai.com/v1")
    return {"provider": provider, "model": model, "key": key, "base": base.rstrip("/")}


def status():
    s = _settings()
    return {"configured": bool(s), "provider": s["provider"] if s else None, "model": s["model"] if s else None}


def ask(messages, context=""):
    """messages: [{'role': 'user'|'assistant', 'content': str}]. Returns (text|None, error_message|None)."""
    s = _settings()
    if not s:
        return None, "No AI provider configured."
    system = SYSTEM_PROMPT + (f"\n\nUser context (user-provided, general): {context}" if context else "")
    try:
        if s["provider"] == "anthropic":
            r = requests.post("https://api.anthropic.com/v1/messages", timeout=45,
                              headers={"x-api-key": s["key"], "anthropic-version": "2023-06-01", "content-type": "application/json"},
                              json={"model": s["model"], "max_tokens": 700, "system": system, "messages": messages})
            r.raise_for_status()
            text = "".join(b.get("text", "") for b in r.json().get("content", []) if b.get("type") == "text")
        else:
            headers = {"content-type": "application/json"}
            if s["key"]:
                headers["Authorization"] = f"Bearer {s['key']}"
            r = requests.post(f"{s['base']}/chat/completions", headers=headers, timeout=60,
                              json={"model": s["model"], "max_tokens": 700,
                                    "messages": [{"role": "system", "content": system}, *messages]})
            r.raise_for_status()
            text = r.json()["choices"][0]["message"]["content"]
    except requests.HTTPError as e:
        return None, f"AI service returned an error (HTTP {e.response.status_code}). Check your key and model name."
    except requests.RequestException as e:
        return None, f"Could not reach the AI service: {type(e).__name__}."
    except (KeyError, IndexError, ValueError):
        return None, "The AI service returned an unexpected response."
    text = (text or "").strip()
    return (text, None) if text else (None, "The AI service returned an empty response.")
