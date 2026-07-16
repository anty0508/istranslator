import threading

import httpx
from openai import OpenAI

from .logging_setup import log


class TranslationError(Exception):
    pass


_clients = {}
_lock = threading.Lock()
_no_extras = set()

EXTRA_PARAMS = {"reasoning_effort": "minimal", "verbosity": "low"}


def _looks_like_param_error(exc):
    msg = str(exc).lower()
    return any(
        k in msg
        for k in (
            "reasoning_effort",
            "reasoning",
            "verbosity",
            "unsupported",
            "unrecognized",
            "does not support",
        )
    )


def _get_client(config):
    api_key = config.effective("api_key").strip()
    if not api_key:
        raise TranslationError(
            "No API key configured. Add one in Settings or set OPENAI_API_KEY in .env."
        )
    base_url = config.effective("base_url").strip()
    key = (api_key, base_url)

    with _lock:
        client = _clients.get(key)
        if client is None:
            http_client = httpx.Client(
                limits=httpx.Limits(
                    max_keepalive_connections=4,
                    max_connections=8,
                    keepalive_expiry=300.0,
                ),
                timeout=15.0,
            )
            client = OpenAI(
                api_key=api_key,
                base_url=base_url or None,
                http_client=http_client,
                max_retries=1,
            )
            _clients[key] = client
    return client


def warmup(config):
    try:
        client = _get_client(config)
        client.models.list()
    except Exception:
        pass


HISTORY_ITEM_MAX = 400


def _build_messages(text, target_language, history=None):
    system_prompt = (
        f"Translate the user's message into {target_language}. "
        "Make it read exactly like a real, experienced senior software engineer wrote it — "
        "the way they'd casually message their boss in a work chat: friendly, easygoing and "
        "human, while staying professional and respectful. Natural, idiomatic and "
        "native-sounding, with a relaxed conversational chat tone; never stiff, overly formal, "
        "stilted or robotic. Keep the original meaning and any technical terms intact. "
        "Reply with only the translated message — no quotes, labels, notes or explanations."
    )
    messages = [{"role": "system", "content": system_prompt}]

    if history:
        lines = []
        for item in history:
            item = " ".join(item.split())
            if len(item) > HISTORY_ITEM_MAX:
                item = item[:HISTORY_ITEM_MAX] + "…"
            if item:
                lines.append(f"- {item}")
        if lines:
            messages.append({
                "role": "system",
                "content": (
                    "Recent messages in this ongoing conversation, for CONTEXT ONLY — do NOT "
                    "translate or repeat them. Use them to resolve references and pronouns, keep "
                    "terminology and names consistent, and match the flow:\n" + "\n".join(lines)
                ),
            })

    messages.append({"role": "user", "content": text})
    return messages


def translate(text, target_language, config, history=None):
    client = _get_client(config)
    model = config.effective("model").strip()
    messages = _build_messages(text, target_language, history)

    use_extras = model not in _no_extras
    try:
        kwargs = dict(EXTRA_PARAMS) if use_extras else {}
        resp = client.chat.completions.create(model=model, messages=messages, **kwargs)
    except Exception as exc:
        if use_extras and _looks_like_param_error(exc):
            log.info("model %r rejected reasoning_effort/verbosity; retrying without them", model)
            _no_extras.add(model)
            try:
                resp = client.chat.completions.create(model=model, messages=messages)
            except Exception as exc2:
                raise TranslationError(str(exc2)) from exc2
        else:
            raise TranslationError(str(exc)) from exc

    content = resp.choices[0].message.content
    if not content:
        raise TranslationError("Empty response from the model.")
    return content.strip()
