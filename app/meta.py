from __future__ import annotations

import json
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class MetaAPIError(RuntimeError):
    """Erro devolvido pela Graph API sem expor o token de acesso."""


class MetaClientProtocol(Protocol):
    def get_campaign(self, campaign_id: str) -> dict[str, Any]: ...
    def list_campaigns(self, limit: int) -> dict[str, Any]: ...
    def update_campaign(self, campaign_id: str, changes: dict[str, Any]) -> dict[str, Any]: ...


class MetaClient:
    FIELDS = "id,account_id,name,status,effective_status,daily_budget,lifetime_budget"

    def __init__(self, access_token: str, api_version: str, ad_account_id: str):
        self._token = access_token
        self._base_url = f"https://graph.facebook.com/{api_version}"
        self._account_id = ad_account_id

    def _request(self, method: str, path: str, params: dict[str, Any]) -> dict[str, Any]:
        payload = {**params, "access_token": self._token}
        data = urlencode(payload).encode() if method == "POST" else None
        url = f"{self._base_url}/{path}"
        if method == "GET":
            url = f"{url}?{urlencode(payload)}"
        request = Request(url, data=data, method=method)
        try:
            with urlopen(request, timeout=20) as response:  # noqa: S310 - domínio fixo
                return json.loads(response.read())
        except HTTPError as exc:
            body = exc.read().decode(errors="replace")
            try:
                detail = json.loads(body).get("error", {}).get("message", body)
            except json.JSONDecodeError:
                detail = body
            raise MetaAPIError(f"Meta API respondeu {exc.code}: {detail}") from exc
        except URLError as exc:
            raise MetaAPIError("Não foi possível acessar a Meta API") from exc

    def get_campaign(self, campaign_id: str) -> dict[str, Any]:
        return self._request("GET", campaign_id, {"fields": self.FIELDS})

    def list_campaigns(self, limit: int = 25) -> dict[str, Any]:
        return self._request(
            "GET", f"act_{self._account_id}/campaigns", {"fields": self.FIELDS, "limit": limit}
        )

    def update_campaign(self, campaign_id: str, changes: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", campaign_id, changes)

