"""API keys live in the operating system's keychain (the macOS Keychain in the desktop app) and nowhere else: not SQLite, not preferences, not JSON, not .env, not logs.

The store has four operations and `get` is used only by the backend when it is about to call the provider. No API response returns a stored key; the UI gets `mask_key`.
"""

import sys
from typing import Protocol

SERVICE = "com.roamingwizards.poltracker.ai"
MAX_KEY_LENGTH = 400


class SecretStoreError(RuntimeError):
    """The keychain could not be used. The message is safe to show: it never contains a key."""


class SecretStore(Protocol):
    def get(self, account: str) -> str | None: ...
    def set(self, account: str, secret: str) -> None: ...
    def delete(self, account: str) -> bool: ...


def clean_key(raw: object) -> str:
    """Trim and sanity-check a pasted key. The error text never includes the value."""
    if not isinstance(raw, str):
        raise ValueError("The API key must be text.")
    key = raw.strip()
    if not key:
        raise ValueError("Enter an API key.")
    if len(key) > MAX_KEY_LENGTH:
        raise ValueError("That does not look like an API key (too long).")
    if any(c.isspace() or ord(c) < 33 or ord(c) > 126 for c in key):
        raise ValueError("An API key contains no spaces or special characters. Check that you copied only the key.")
    return key


def mask_key(key: str) -> str:
    """'sk-••••••••1234': enough to recognise which key is stored, never enough to use it."""
    if len(key) < 12:
        return "••••••••"
    prefix = "sk-" if key.startswith("sk-") else ""
    return f"{prefix}••••••••{key[-4:]}"


class KeyringSecretStore:
    """The macOS Keychain through the `keyring` package, one generic-password item per provider under SERVICE. On macOS the Keychain backend is used directly (no
    plugin discovery, so it also works inside the packaged app); elsewhere the platform's own backend is used. If no secure backend exists the store refuses to save:
    it never falls back to a file."""

    def __init__(self, service: str = SERVICE, backend=None):
        self._service, self._backend = service, backend

    def _kr(self):
        try:
            if self._backend is None:
                if sys.platform == "darwin":
                    from keyring.backends.macOS import Keyring as MacKeychain

                    self._backend = MacKeychain()
                else:
                    import keyring

                    self._backend = keyring.get_keyring()
            if getattr(self._backend, "priority", 1) <= 0:  # keyring's "fail" backend and the like: refuse rather than fall back to anything weaker
                raise SecretStoreError("No secure key storage is available on this system, so API keys cannot be saved.")
        except SecretStoreError:
            raise
        except Exception as exc:  # missing package, no backend
            raise SecretStoreError("Secure key storage (the system keychain) is unavailable.") from exc
        return self._backend

    def get(self, account: str) -> str | None:
        try:
            return self._kr().get_password(self._service, account)
        except SecretStoreError:
            raise
        except Exception as exc:
            raise SecretStoreError("Could not read the key from the system keychain.") from exc

    def set(self, account: str, secret: str) -> None:
        try:
            self._kr().set_password(self._service, account, secret)
        except SecretStoreError:
            raise
        except Exception as exc:
            raise SecretStoreError("Could not save the key to the system keychain.") from exc

    def delete(self, account: str) -> bool:
        try:
            kr = self._kr()
            if kr.get_password(self._service, account) is None:
                return False
            kr.delete_password(self._service, account)
            return True
        except SecretStoreError:
            raise
        except Exception as exc:
            raise SecretStoreError("Could not remove the key from the system keychain.") from exc


class MemorySecretStore:
    """For tests and for running without a keychain. Nothing is persisted."""

    def __init__(self):
        self._d: dict[str, str] = {}

    def get(self, account: str) -> str | None:
        return self._d.get(account)

    def set(self, account: str, secret: str) -> None:
        self._d[account] = secret

    def delete(self, account: str) -> bool:
        return self._d.pop(account, None) is not None
