"""Authentication helpers for Lottery POS.

Two kinds of accounts exist, both separate from Home Assistant users:

* ``owner``    - the lottery company. Back office only.
* ``retailer`` - a shop. Sell screen only, and only for its own shop.

Passwords are stored as salted PBKDF2-SHA256 hashes. Sessions are random tokens
kept in memory (a Home Assistant restart signs everybody out).
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
import time

ITERATIONS = 200_000
MIN_PASSWORD_LEN = 6

# Sliding session lifetime (seconds of inactivity before the token expires)
SESSION_TTL = {"owner": 30 * 60, "retailer": 12 * 3600}

# Brute force protection
MAX_FAILURES = 5
LOCK_SECONDS = 300


def hash_password(password: str, iterations: int = ITERATIONS) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"pbkdf2_sha256${iterations}${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str | None) -> bool:
    """Constant-time check. Always does the hashing work, even for bad input."""
    try:
        algo, iters, salt_hex, hash_hex = (stored or "").split("$")
        if algo != "pbkdf2_sha256":
            raise ValueError
        salt, expected, n = bytes.fromhex(salt_hex), bytes.fromhex(hash_hex), int(iters)
    except (ValueError, TypeError):
        # burn comparable time so unknown users are not distinguishable by speed
        hashlib.pbkdf2_hmac("sha256", b"x", b"0" * 16, ITERATIONS)
        return False
    dk = hashlib.pbkdf2_hmac("sha256", (password or "").encode("utf-8"), salt, n)
    return hmac.compare_digest(dk, expected)


def generate_password(length: int = 10) -> str:
    """Readable random password (no 0/O/1/l/I)."""
    alphabet = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def check_strength(password: str) -> str | None:
    if len(password or "") < MIN_PASSWORD_LEN:
        return f"Password must be at least {MIN_PASSWORD_LEN} characters"
    return None


class Session:
    __slots__ = ("token", "role", "subject", "username", "name", "expires", "mode")

    def __init__(self, token, role, subject, username, name, mode):
        self.token, self.role, self.subject = token, role, subject
        self.username, self.name, self.mode = username, name, mode
        self.expires = time.time() + SESSION_TTL[role]


class SessionManager:
    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}
        self._fail: dict[str, tuple[int, float]] = {}

    # ----- lockout -----
    def locked_for(self, username: str) -> int:
        n, until = self._fail.get(username.lower(), (0, 0.0))
        left = int(until - time.time())
        return left if n >= MAX_FAILURES and left > 0 else 0

    def record_failure(self, username: str) -> None:
        key = username.lower()
        n, until = self._fail.get(key, (0, 0.0))
        if until and until < time.time():
            n = 0  # lock expired, start over
        n += 1
        self._fail[key] = (n, time.time() + LOCK_SECONDS)
        if len(self._fail) > 500:  # keep memory bounded
            now = time.time()
            self._fail = {k: v for k, v in self._fail.items() if v[1] > now}

    def clear_failures(self, username: str) -> None:
        self._fail.pop(username.lower(), None)

    # ----- sessions -----
    def create(self, role: str, subject: str, username: str, name: str, mode: str) -> Session:
        # one live session per account per mode: a new login replaces the old one
        for tok, s in list(self._sessions.items()):
            if s.role == role and s.subject == subject and s.mode == mode:
                del self._sessions[tok]
        tok = secrets.token_urlsafe(32)
        sess = Session(tok, role, subject, username, name, mode)
        self._sessions[tok] = sess
        return sess

    def get(self, token: str | None) -> Session | None:
        if not token:
            return None
        sess = self._sessions.get(token)
        if not sess:
            return None
        now = time.time()
        if sess.expires < now:
            del self._sessions[token]
            return None
        sess.expires = now + SESSION_TTL[sess.role]  # sliding
        return sess

    def revoke(self, token: str | None) -> None:
        if token:
            self._sessions.pop(token, None)

    def revoke_subject(self, role: str, subject: str) -> None:
        for tok, s in list(self._sessions.items()):
            if s.role == role and s.subject == subject:
                del self._sessions[tok]
