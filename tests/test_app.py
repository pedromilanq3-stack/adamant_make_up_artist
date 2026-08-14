from fastapi.testclient import TestClient

from app.config import Settings
from app.main import app, get_client, get_settings


SETTINGS = Settings("934861699094739", "test-token", "v99.0", "s" * 32, "k" * 32)


class FakeMetaClient:
    def __init__(self):
        self.updated = None

    def get_campaign(self, campaign_id):
        return {
            "id": campaign_id,
            "account_id": SETTINGS.ad_account_id,
            "name": "Campanha atual",
            "status": "PAUSED",
        }

    def list_campaigns(self, limit):
        return {"data": [self.get_campaign("52564925569669")], "limit": limit}

    def update_campaign(self, campaign_id, changes):
        self.updated = (campaign_id, changes)
        return {"success": True}


fake = FakeMetaClient()
app.dependency_overrides[get_settings] = lambda: SETTINGS
app.dependency_overrides[get_client] = lambda: fake
client = TestClient(app, headers={"X-API-Key": "k" * 32})


def test_preview_then_apply():
    preview = client.post(
        "/campaigns/52564925569669/preview", json={"status": "ACTIVE"}
    )
    assert preview.status_code == 200
    token = preview.json()["confirmation_token"]

    applied = client.post(
        "/campaigns/52564925569669/apply",
        json={"status": "ACTIVE", "confirmation_token": token},
    )
    assert applied.status_code == 200
    assert fake.updated == ("52564925569669", {"status": "ACTIVE"})


def test_modified_change_rejects_confirmation_token():
    token = client.post(
        "/campaigns/52564925569669/preview", json={"status": "ACTIVE"}
    ).json()["confirmation_token"]
    response = client.post(
        "/campaigns/52564925569669/apply",
        json={"status": "PAUSED", "confirmation_token": token},
    )
    assert response.status_code == 400


def test_rejects_unsupported_fields_and_conflicting_budgets():
    unsupported = client.post(
        "/campaigns/52564925569669/preview", json={"objective": "OUTCOME_SALES"}
    )
    conflicting = client.post(
        "/campaigns/52564925569669/preview",
        json={"daily_budget": 1000, "lifetime_budget": 5000},
    )
    assert unsupported.status_code == 422
    assert conflicting.status_code == 422


def test_requires_gateway_api_key():
    response = TestClient(app).get("/campaigns")
    assert response.status_code == 401
