from __future__ import annotations

import hashlib
import json


def compute_prompt_hash(messages: list[dict]) -> str:
    """Return SHA-256 hex digest of the canonical JSON representation of messages.

    The hash is deterministic: same messages always produce the same 64-char hex string.
    sort_keys=True and ensure_ascii=False ensure consistent serialization across runs.
    """
    serialized = json.dumps(messages, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(serialized.encode('utf-8')).hexdigest()
