from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
from urllib.request import Request, urlopen


DEFAULT_API_VERSION = "v26.0"
ALLOWED_GRAPH_HOSTS = {"graph.facebook.com", "graph.instagram.com"}
PROFILE_FIELDS = (
    "biography,followers_count,follows_count,id,media_count,name,"
    "profile_picture_url,username,website"
)
MEDIA_FIELDS = (
    "id,caption,comments_count,like_count,media_product_type,media_type,"
    "media_url,permalink,shortcode,thumbnail_url,timestamp,username,"
    "children{id,media_type,media_url,permalink,thumbnail_url,timestamp}"
)


class InstagramAPIError(RuntimeError):
    """A safe, human-readable Instagram Graph API failure."""


@dataclass(frozen=True)
class InstagramSnapshot:
    profile: dict[str, Any]
    media: list[dict[str, Any]]
    collected_at: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "collected_at": self.collected_at,
            "profile": self.profile,
            "media": self.media,
        }


class InstagramGraphAPI:
    """Read public professional-account data through Business Discovery."""

    def __init__(self, access_token: str, instagram_user_id: str,
                 api_version: str = DEFAULT_API_VERSION) -> None:
        if not access_token.strip() or not instagram_user_id.strip():
            raise ValueError("O token e o ID da conta profissional são obrigatórios.")
        if not api_version.startswith("v") or not api_version[1:].replace(".", "").isdigit():
            raise ValueError("Versão inválida da Graph API.")
        self.access_token = access_token.strip()
        self.instagram_user_id = instagram_user_id.strip()
        self.base_url = f"https://graph.facebook.com/{api_version}"

    def collect(self, username: str, max_media: int = 500) -> InstagramSnapshot:
        username = username.strip().lstrip("@").casefold()
        if not username or not username.replace(".", "").replace("_", "").isalnum():
            raise ValueError("Nome de usuário do Instagram inválido.")
        if not 1 <= max_media <= 10_000:
            raise ValueError("max_media deve estar entre 1 e 10000.")

        discovery_fields = (
            f"business_discovery.username({username})"
            f"{{{PROFILE_FIELDS},media.limit(100){{{MEDIA_FIELDS}}}}}"
        )
        payload = self._get(
            f"{self.base_url}/{self.instagram_user_id}",
            {"fields": discovery_fields},
        )
        profile = payload.get("business_discovery")
        if not isinstance(profile, dict):
            raise InstagramAPIError(
                "A API não retornou Business Discovery. Confirme o usuário, "
                "as permissões e se as contas são profissionais."
            )

        media_page = profile.pop("media", {})
        media: list[dict[str, Any]] = []
        while isinstance(media_page, dict):
            items = media_page.get("data", [])
            if isinstance(items, list):
                media.extend(item for item in items if isinstance(item, dict))
            if len(media) >= max_media:
                media = media[:max_media]
                break
            next_url = media_page.get("paging", {}).get("next")
            if not isinstance(next_url, str) or not next_url:
                break
            media_page = self._get_next(next_url)

        return InstagramSnapshot(
            profile=profile,
            media=media,
            collected_at=datetime.now(timezone.utc).isoformat(),
        )

    def _get_next(self, url: str) -> dict[str, Any]:
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.hostname not in ALLOWED_GRAPH_HOSTS:
            raise InstagramAPIError("A API retornou uma URL de paginação insegura.")
        # Never trust or persist a token embedded in a pagination URL.
        query = [(key, value) for key, value in parse_qsl(parsed.query) if key != "access_token"]
        clean = urlunparse(parsed._replace(query=urlencode(query)))
        return self._get(clean)

    def _get(self, url: str, params: dict[str, str] | None = None) -> dict[str, Any]:
        if params:
            url = f"{url}?{urlencode(params)}"
        request = Request(url, headers={
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json",
            "User-Agent": "instagram-export-search/1.1",
        })
        try:
            with urlopen(request, timeout=30) as response:
                payload = json.load(response)
        except HTTPError as exc:
            try:
                detail = json.load(exc).get("error", {}).get("message", "")
            except (AttributeError, json.JSONDecodeError, UnicodeError):
                detail = ""
            raise InstagramAPIError(
                f"Instagram Graph API respondeu HTTP {exc.code}"
                + (f": {detail}" if detail else ".")
            ) from exc
        except (URLError, TimeoutError) as exc:
            raise InstagramAPIError("Não foi possível conectar à Instagram Graph API.") from exc
        except (json.JSONDecodeError, UnicodeError) as exc:
            raise InstagramAPIError("A Instagram Graph API retornou JSON inválido.") from exc
        if not isinstance(payload, dict):
            raise InstagramAPIError("A Instagram Graph API retornou uma resposta inesperada.")
        return payload


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Coleta dados públicos de uma conta profissional via Instagram Graph API."
    )
    parser.add_argument("username", help="nome de usuário, por exemplo: maysanchess")
    parser.add_argument("--output", type=Path, default=Path("instagram_snapshot.json"))
    parser.add_argument("--max-media", type=int, default=500)
    args = parser.parse_args()
    token = os.environ.get("INSTAGRAM_ACCESS_TOKEN", "")
    account_id = os.environ.get("INSTAGRAM_USER_ID", "")
    version = os.environ.get("INSTAGRAM_GRAPH_API_VERSION", DEFAULT_API_VERSION)
    if not token or not account_id:
        parser.error("defina INSTAGRAM_ACCESS_TOKEN e INSTAGRAM_USER_ID no ambiente")
    try:
        snapshot = InstagramGraphAPI(token, account_id, version).collect(
            args.username, args.max_media
        )
    except (InstagramAPIError, ValueError) as exc:
        parser.error(str(exc))
    args.output.write_text(
        json.dumps(snapshot.as_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"{len(snapshot.media)} mídias salvas em {args.output}")


if __name__ == "__main__":
    main()
