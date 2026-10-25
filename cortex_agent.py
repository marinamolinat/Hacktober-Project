"""Public-query Cortex Agent adapter with structured citation extraction.

The caller must intersect cited_event_ids with freshly eligible stored events and
compose its public answer from those stored facts, rather than forwarding prose.
References: Snowflake Cortex Agents Run API and SQL API key-pair authentication.
"""

import base64
import hashlib
import json
import os
import re
import time
from pathlib import Path

import requests

from snowflake_client import identifier


def _base64url(value):
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _token():
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding

    key_path = os.getenv("SNOWFLAKE_PRIVATE_KEY_PATH")
    account = os.getenv("SNOWFLAKE_ACCOUNT", "")
    user = os.getenv("SNOWFLAKE_USER", "")
    if not key_path or not account or not user:
        raise ValueError("Agent key-pair authentication is not configured.")
    passphrase = os.getenv("SNOWFLAKE_PRIVATE_KEY_PASSPHRASE")
    private_key = serialization.load_pem_private_key(
        Path(key_path).expanduser().read_bytes(),
        password=passphrase.encode() if passphrase else None,
    )
    public_der = private_key.public_key().public_bytes(
        serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
    fingerprint = "SHA256:" + base64.b64encode(hashlib.sha256(public_der).digest()).decode("ascii")
    # Locator authentication excludes its region suffix. Organization-account
    # identifiers retain their hyphen. An explicit JWT identifier is optional.
    jwt_account = os.getenv("SNOWFLAKE_JWT_ACCOUNT") or account.split(".", 1)[0]
    qualified_user = jwt_account.upper().replace(".", "-") + "." + user.upper()
    issued_at = int(time.time())
    payload = {"iss": qualified_user + "." + fingerprint, "sub": qualified_user,
               "iat": issued_at, "exp": issued_at + 300}
    header = _base64url(json.dumps({"alg": "RS256", "typ": "JWT"}, separators=(",", ":")).encode())
    body = _base64url(json.dumps(payload, separators=(",", ":")).encode())
    unsigned = (header + "." + body).encode("ascii")
    signature = private_key.sign(unsigned, padding.PKCS1v15(), hashes.SHA256())
    return header + "." + body + "." + _base64url(signature)


def _normalize(response):
    answer, citations, warnings = [], [], []
    if not isinstance(response, dict):
        raise ValueError("Agent response was not an object.")
    if response.get("status") in {"error", "cancelled", "timed_out"}:
        raise ValueError("Agent did not complete.")

    def add_id(value):
        if isinstance(value, str) and value and value not in citations:
            citations.append(value)

    def search_documents(value):
        # Search document identifiers are structured data; prose and snippets
        # are never scanned for IDs or treated as instructions.
        if isinstance(value, dict):
            for key, item in value.items():
                if key in {"doc_id", "event_id", "EVENT_ID"}:
                    add_id(item)
                elif isinstance(item, (dict, list)):
                    search_documents(item)
        elif isinstance(value, list):
            for item in value:
                search_documents(item)

    for content in response.get("content", []):
        if not isinstance(content, dict):
            continue
        if content.get("type") == "text":
            text = content.get("text")
            if isinstance(text, str):
                answer.append(text)
            for annotation in content.get("annotations") or []:
                if isinstance(annotation, dict) and annotation.get("type") == "cortex_search_citation":
                    add_id(annotation.get("doc_id"))
        elif content.get("type") == "tool_result":
            result = content.get("tool_result") or {}
            if result.get("type") == "cortex_search" and result.get("status") in {None, "success"}:
                for item in result.get("content") or []:
                    if isinstance(item, dict) and item.get("type") == "json":
                        search_documents(item.get("json"))
    for warning in response.get("warnings") or []:
        code = warning.get("code") if isinstance(warning, dict) else None
        warnings.append("Cortex Agent reported a tool warning" + (f" ({code})." if code else "."))
    if not citations:
        warnings.append("Cortex Agent returned no structured event citations; using current event records.")
    return {"answer": "\n\n".join(answer), "cited_event_ids": citations, "warnings": warnings}


def ask_agent(question):
    """Call the configured stored Agent; degrade without exposing credentials."""
    fallback = {"answer": None, "cited_event_ids": [],
                "warnings": ["Cortex Agent is unavailable; using current event records."]}
    if not isinstance(question, str) or not question.strip() or len(question) > 500:
        return fallback
    try:
        database = identifier(os.getenv("SNOWFLAKE_DATABASE", "HACKATHON_DB"))
        schema = identifier(os.getenv("SNOWFLAKE_SCHEMA", "APP"))
        configured_agent = os.getenv("SNOWFLAKE_AGENT", "EVENT_ASSISTANT").split(".")
        if len(configured_agent) == 3:
            database, schema, name = map(identifier, configured_agent)
        elif len(configured_agent) == 1:
            name = identifier(configured_agent[0])
        else:
            return fallback
        host = os.getenv("SNOWFLAKE_HOST") or os.getenv("SNOWFLAKE_ACCOUNT", "").lower() + ".snowflakecomputing.com"
        if not re.fullmatch(r"[a-zA-Z0-9_.-]+\.snowflakecomputing\.com", host):
            return fallback
        headers = {"Authorization": "Bearer " + _token(), "Content-Type": "application/json",
                   "Accept": "application/json", "X-Snowflake-Authorization-Token-Type": "KEYPAIR_JWT",
                   "X-Snowflake-Role": identifier(os.getenv("SNOWFLAKE_ROLE", "HACKATHON_API"))}
        payload = {"stream": False, "messages": [{"role": "user", "content": [
            {"type": "text", "text": question.strip()}]}]}
        with requests.post(f"https://{host}/api/v2/databases/{database}/schemas/{schema}/agents/{name}:run",
                           headers=headers, json=payload, timeout=20) as response:
            response.raise_for_status()
            return _normalize(response.json())
    except Exception:
        return fallback
