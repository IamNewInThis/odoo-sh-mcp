"""XML-RPC client wrapper for Odoo."""

import xmlrpc.client
import os
from functools import cached_property
from typing import Any


class OdooClient:
    """Thin wrapper around Odoo's XML-RPC endpoints."""

    def __init__(
        self,
        url: str | None = None,
        db: str | None = None,
        api_key: str | None = None,
        username: str | None = None,
        password: str | None = None,
    ):
        self.url = (url or os.environ["ODOO_URL"]).rstrip("/")
        self.db = db or os.environ["ODOO_DB"]
        self.api_key = api_key or os.environ.get("ODOO_API_KEY")
        self.username = username or os.environ.get("ODOO_USERNAME", "admin")
        self.password = password or os.environ.get("ODOO_PASSWORD", "")
        self._uid: int | None = None

    @cached_property
    def _common(self) -> xmlrpc.client.ServerProxy:
        return xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/common")

    @cached_property
    def _object(self) -> xmlrpc.client.ServerProxy:
        return xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/object")

    def uid(self) -> int:
        if self._uid is None:
            if self.api_key:
                # API key auth: try authenticate first; if it fails (returns 0/False)
                # fall back to uid=1 because Odoo validates the API key in execute_kw
                # directly without requiring a prior authenticate() call.
                self._uid = self._common.authenticate(
                    self.db, self.username, self.api_key, {}
                )
                if not self._uid:
                    # Odoo SH / some versions don't accept API key via authenticate().
                    # The key is validated per-call in execute_kw, so any valid positive
                    # UID works here. Use 1 (admin) as the conventional fallback.
                    self._uid = 1
            else:
                self._uid = self._common.authenticate(
                    self.db, self.username, self.password, {}
                )
                if not self._uid:
                    raise RuntimeError(
                        "Authentication failed. Check ODOO_URL, ODOO_DB and credentials."
                    )
        return self._uid

    def _auth(self) -> str:
        """Return the credential used for execute_kw calls."""
        return self.api_key if self.api_key else self.password

    def execute(
        self,
        model: str,
        method: str,
        args: list[Any] | None = None,
        kwargs: dict[str, Any] | None = None,
    ) -> Any:
        return self._object.execute_kw(
            self.db,
            self.uid(),
            self._auth(),
            model,
            method,
            args or [],
            kwargs or {},
        )

    def search_read(
        self,
        model: str,
        domain: list[Any],
        fields: list[str],
        limit: int = 0,
        order: str = "",
    ) -> list[dict[str, Any]]:
        kwargs: dict[str, Any] = {"fields": fields}
        if limit:
            kwargs["limit"] = limit
        if order:
            kwargs["order"] = order
        return self.execute(model, "search_read", [domain], kwargs)

    def version(self) -> dict[str, Any]:
        return self._common.version()
