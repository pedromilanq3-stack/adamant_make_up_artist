from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import Annotated, Any, Literal

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, ConfigDict, Field, model_validator

from .config import Settings
from .meta import MetaAPIError, MetaClient, MetaClientProtocol

app = FastAPI(
    title="GPT → Meta Ads Gateway",
    description="Gateway com pré-visualização e confirmação para campanhas do Meta Ads.",
    version="1.0.0",
)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


class CampaignChanges(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=400)
    status: Literal["ACTIVE", "PAUSED"] | None = None
    daily_budget: int | None = Field(default=None, ge=100)
    lifetime_budget: int | None = Field(default=None, ge=100)

    @model_validator(mode="after")
    def validate_changes(self) -> "CampaignChanges":
        selected = self.model_dump(exclude_none=True)
        if not selected:
            raise ValueError("Informe ao menos uma alteração")
        if self.daily_budget is not None and self.lifetime_budget is not None:
            raise ValueError("Altere somente um tipo de orçamento por vez")
        return self


class ApplyRequest(CampaignChanges):
    confirmation_token: str = Field(min_length=20)


def get_settings() -> Settings:
    try:
        return Settings.from_env()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def get_client(settings: Annotated[Settings, Depends(get_settings)]) -> MetaClientProtocol:
    return MetaClient(settings.access_token, settings.api_version, settings.ad_account_id)


def require_api_key(
    supplied: Annotated[str | None, Depends(api_key_header)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> None:
    if supplied is None or not hmac.compare_digest(supplied, settings.gateway_api_key):
        raise HTTPException(status_code=401, detail="Chave da API inválida")


def _changes(payload: CampaignChanges) -> dict[str, Any]:
    return payload.model_dump(exclude_none=True, exclude={"confirmation_token"})


def _signature(secret: str, campaign_id: str, changes: dict[str, Any], expires: int) -> str:
    message = json.dumps(
        {"campaign_id": campaign_id, "changes": changes, "expires": expires},
        sort_keys=True,
        separators=(",", ":"),
    )
    digest = hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()
    return f"{expires}.{digest}"


def _assert_account(campaign: dict[str, Any], expected_account: str) -> None:
    if str(campaign.get("account_id")) != expected_account:
        raise HTTPException(status_code=403, detail="Campanha fora da conta autorizada")


@app.exception_handler(MetaAPIError)
async def meta_error_handler(_request: Any, exc: MetaAPIError):
    from fastapi.responses import JSONResponse

    return JSONResponse(status_code=502, content={"detail": str(exc)})


@app.get("/health", operation_id="health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/campaigns", operation_id="listCampaigns")
def list_campaigns(
    _authorized: Annotated[None, Depends(require_api_key)],
    client: Annotated[MetaClientProtocol, Depends(get_client)],
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
) -> dict[str, Any]:
    return client.list_campaigns(limit)


@app.get("/campaigns/{campaign_id}", operation_id="getCampaign")
def get_campaign(
    campaign_id: str,
    _authorized: Annotated[None, Depends(require_api_key)],
    settings: Annotated[Settings, Depends(get_settings)],
    client: Annotated[MetaClientProtocol, Depends(get_client)],
) -> dict[str, Any]:
    campaign = client.get_campaign(campaign_id)
    _assert_account(campaign, settings.ad_account_id)
    return campaign


@app.post("/campaigns/{campaign_id}/preview", operation_id="previewCampaignChanges")
def preview_campaign_changes(
    campaign_id: str,
    payload: CampaignChanges,
    _authorized: Annotated[None, Depends(require_api_key)],
    settings: Annotated[Settings, Depends(get_settings)],
    client: Annotated[MetaClientProtocol, Depends(get_client)],
) -> dict[str, Any]:
    campaign = client.get_campaign(campaign_id)
    _assert_account(campaign, settings.ad_account_id)
    changes = _changes(payload)
    expires = int(time.time()) + 300
    return {
        "current": campaign,
        "changes": changes,
        "confirmation_token": _signature(settings.confirmation_secret, campaign_id, changes, expires),
        "expires_in_seconds": 300,
        "instruction": "Mostre a prévia ao usuário e só aplique após confirmação explícita.",
    }


@app.post("/campaigns/{campaign_id}/apply", operation_id="applyCampaignChanges")
def apply_campaign_changes(
    campaign_id: str,
    payload: ApplyRequest,
    _authorized: Annotated[None, Depends(require_api_key)],
    settings: Annotated[Settings, Depends(get_settings)],
    client: Annotated[MetaClientProtocol, Depends(get_client)],
) -> dict[str, Any]:
    changes = _changes(payload)
    try:
        expires = int(payload.confirmation_token.split(".", 1)[0])
    except (ValueError, IndexError):
        raise HTTPException(status_code=400, detail="Token de confirmação inválido") from None
    expected = _signature(settings.confirmation_secret, campaign_id, changes, expires)
    if expires < int(time.time()) or not hmac.compare_digest(payload.confirmation_token, expected):
        raise HTTPException(status_code=400, detail="Token de confirmação inválido ou expirado")
    campaign = client.get_campaign(campaign_id)
    _assert_account(campaign, settings.ad_account_id)
    result = client.update_campaign(campaign_id, changes)
    return {"applied": True, "campaign_id": campaign_id, "changes": changes, "meta": result}
