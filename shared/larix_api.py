# -*- coding: utf-8 -*-
"""HTTP client for the current local Larix EST.WebApi contract.

The local API now requires POST /auth and a Bearer JWT for the endpoints used
by Manager.  This module centralises authentication so individual UI modules
never have to build auth payloads or manage tokens themselves.
"""
from __future__ import annotations

import base64
import getpass
import hashlib
import os
import socket
import threading
from typing import Any, Dict, Optional

import requests
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

DEFAULT_API_BASE_URL = "http://localhost:5000"
DEFAULT_API_LOGIN = "Test"
DEFAULT_API_PASSWORD = "Test"
APPLICATION_CODE = r"LarixLLC\Larix\Est\Manager"
DEFAULT_TIMEOUT = 30


def normalize_base_url(raw: str | None) -> str:
    """Return API host root, without a trailing /api or slash."""
    value = (raw or "").strip()
    if not value:
        value = DEFAULT_API_BASE_URL
    if value.isdigit():
        value = f"http://localhost:{value}"
    elif "://" not in value:
        value = "http://" + value
    value = value.rstrip("/")
    if value.lower().endswith("/api"):
        value = value[:-4].rstrip("/")
    return value


def _host_title() -> str:
    domain = os.environ.get("USERDOMAIN") or socket.gethostname()
    username = os.environ.get("USERNAME") or getpass.getuser()
    computer = os.environ.get("COMPUTERNAME") or socket.gethostname()
    return f"{domain}\\{username}@{computer}"


def _host_ident(host_title: str) -> str:
    digest = hashlib.sha512(host_title.encode("utf-8")).digest()
    return base64.b64encode(digest).decode("ascii")


def _encrypt_destination(destination: str, host_ident: str) -> str:
    """Reproduce Larix EncryptDecrypt.EncryptText for Destination."""
    digest = hashlib.sha512(host_ident.encode("utf-8")).digest()
    internal_key = base64.b64encode(digest).decode("ascii")[:24]

    iv = internal_key[1:9].encode("utf-16le")
    aes_key = internal_key[8:24].encode("utf-16le")

    padder = padding.PKCS7(128).padder()
    padded = padder.update(destination.encode("utf-8")) + padder.finalize()
    encryptor = Cipher(algorithms.AES(aes_key), modes.CBC(iv)).encryptor()
    encrypted = encryptor.update(padded) + encryptor.finalize()
    return base64.b64encode(encrypted).decode("ascii")


def build_auth_payload(
    base_url: str,
    login: str = DEFAULT_API_LOGIN,
    password: str = DEFAULT_API_PASSWORD,
) -> Dict[str, Any]:
    base = normalize_base_url(base_url)
    title = _host_title()
    ident = _host_ident(title)
    destination = _encrypt_destination(base + "/", ident)
    return {
        "userAuthDto": {
            "login": login,
            "password": password,
        },
        "terminalSessionRequest": {
            "hostTitle": title,
            "hostIdent": ident,
            "applicationCode": APPLICATION_CODE,
            "destination": destination,
        },
    }


class LarixApiClient:
    """Authenticated client for the local EST.WebApi instance."""

    def __init__(
        self,
        base_url: str = DEFAULT_API_BASE_URL,
        *,
        login: Optional[str] = None,
        password: Optional[str] = None,
    ) -> None:
        self.base_url = normalize_base_url(base_url)
        self.login = login or os.environ.get("LARIX_API_LOGIN") or DEFAULT_API_LOGIN
        self.password = password or os.environ.get("LARIX_API_PASSWORD") or DEFAULT_API_PASSWORD
        self.session = requests.Session()
        self.session.headers.update({"accept": "application/json"})
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.terminal_session_response: Any = None
        self.acs_authorization_response: Any = None
        self.api_version: Any = None
        self._lock = threading.RLock()

    def _url(self, path_or_url: str) -> str:
        value = str(path_or_url or "").strip()
        if value.startswith("http://") or value.startswith("https://"):
            return value
        if not value.startswith("/"):
            value = "/" + value
        return self.base_url + value

    def get_api_version(self, timeout: float = 5.0) -> Any:
        response = self.session.get(self._url("/getApiVersion"), timeout=timeout)
        response.raise_for_status()
        try:
            self.api_version = response.json()
        except ValueError:
            self.api_version = response.text
        return self.api_version

    def authenticate(self, *, force: bool = False, timeout: float = DEFAULT_TIMEOUT) -> str:
        with self._lock:
            if self.access_token and not force:
                return self.access_token

            # /auth is anonymous; do not leak a stale Bearer token into re-authentication.
            self.session.headers.pop("Authorization", None)
            response = self.session.post(
                self._url("/auth"),
                json=build_auth_payload(self.base_url, self.login, self.password),
                timeout=timeout,
            )
            response.raise_for_status()
            data = response.json()
            tokens = data.get("tokens") if isinstance(data, dict) else None
            if not isinstance(tokens, dict):
                raise RuntimeError("POST /auth: в ответе отсутствует объект tokens")
            access = tokens.get("accessToken")
            if not access:
                raise RuntimeError("POST /auth: в ответе отсутствует accessToken")

            self.access_token = str(access)
            refresh = tokens.get("refreshToken")
            self.refresh_token = str(refresh) if refresh else None
            self.terminal_session_response = data.get("terminalSessionResponse")
            self.acs_authorization_response = data.get("acsAuthorizationResponse")
            self.session.headers["Authorization"] = f"Bearer {self.access_token}"
            return self.access_token

    def refresh(self, timeout: float = DEFAULT_TIMEOUT) -> bool:
        with self._lock:
            if not self.access_token or not self.refresh_token:
                return False
            response = self.session.post(
                self._url("/refresh"),
                json={
                    "accessToken": self.access_token,
                    "refreshToken": self.refresh_token,
                },
                timeout=timeout,
            )
            if response.status_code >= 400:
                return False
            data = response.json()
            access = data.get("accessToken") if isinstance(data, dict) else None
            if not access:
                return False
            self.access_token = str(access)
            refresh = data.get("refreshToken") if isinstance(data, dict) else None
            if refresh:
                self.refresh_token = str(refresh)
            self.session.headers["Authorization"] = f"Bearer {self.access_token}"
            return True

    def request(
        self,
        method: str,
        path_or_url: str,
        *,
        auth: bool = True,
        timeout: float = DEFAULT_TIMEOUT,
        retry_auth: bool = True,
        **kwargs: Any,
    ) -> requests.Response:
        with self._lock:
            if auth:
                self.authenticate(timeout=timeout)

            response = self.session.request(
                method.upper(),
                self._url(path_or_url),
                timeout=timeout,
                **kwargs,
            )

            if auth and retry_auth and response.status_code == 401:
                if not self.refresh(timeout=timeout):
                    self.authenticate(force=True, timeout=timeout)
                response = self.session.request(
                    method.upper(),
                    self._url(path_or_url),
                    timeout=timeout,
                    **kwargs,
                )
            return response

    def get_json(
        self,
        path_or_url: str,
        *,
        params: Any = None,
        timeout: float = DEFAULT_TIMEOUT,
        auth: bool = True,
    ) -> Any:
        response = self.request(
            "GET",
            path_or_url,
            params=params,
            timeout=timeout,
            auth=auth,
        )
        response.raise_for_status()
        return response.json()

    def post_json(
        self,
        path_or_url: str,
        payload: Any,
        *,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> requests.Response:
        return self.request("POST", path_or_url, json=payload, timeout=timeout)


_CLIENTS: Dict[str, LarixApiClient] = {}
_CLIENTS_LOCK = threading.RLock()


def get_api_client(base_url: str | None = None) -> LarixApiClient:
    base = normalize_base_url(base_url or os.environ.get("LARIX_API_BASE_URL"))
    with _CLIENTS_LOCK:
        client = _CLIENTS.get(base)
        if client is None:
            client = LarixApiClient(base)
            _CLIENTS[base] = client
        return client


def api_request(method: str, base_url: str, path: str, **kwargs: Any) -> requests.Response:
    return get_api_client(base_url).request(method, path, **kwargs)


def api_get_json(base_url: str, path: str, *, params: Any = None, timeout: float = DEFAULT_TIMEOUT) -> Any:
    return get_api_client(base_url).get_json(path, params=params, timeout=timeout)


def check_connection(base_url: str, timeout: float = 5.0, *, require_auth: bool = True) -> bool:
    """Check API version and, by default, verify that the new auth flow works."""
    try:
        client = get_api_client(base_url)
        client.get_api_version(timeout=timeout)
        if require_auth:
            client.authenticate(force=True, timeout=max(timeout, 10.0))
        return True
    except Exception:
        return False
