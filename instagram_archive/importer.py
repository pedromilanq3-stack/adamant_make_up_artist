from __future__ import annotations

import json
import shutil
import tempfile
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from zipfile import BadZipFile, ZipFile, is_zipfile

from .models import Attachment, Conversation, Message
from .security import MAX_ARCHIVE_BYTES, MAX_EXTRACTED_BYTES, MAX_FILES, validate_member


class ArchiveError(ValueError):
    """A exportação não pôde ser validada ou interpretada."""


def _decode_meta(value: object) -> str:
    if not isinstance(value, str):
        return "" if value is None else str(value)
    # Some Meta JSON exports represent UTF-8 bytes as mis-decoded Latin-1.
    try:
        repaired = value.encode("latin-1").decode("utf-8")
        if repaired != value and any(ord(c) > 127 for c in repaired):
            return repaired
    except (UnicodeEncodeError, UnicodeDecodeError):
        pass
    return value


def _date(value: object) -> datetime:
    if isinstance(value, (int, float)):
        # Meta uses milliseconds in JSON.
        seconds = value / 1000 if value > 10_000_000_000 else value
        return datetime.fromtimestamp(seconds, tz=timezone.utc)
    text = str(value or "").strip()
    if not text:
        return datetime.fromtimestamp(0, tz=timezone.utc)
    text = text.replace("Z", "+00:00")
    for parser in (datetime.fromisoformat,):
        try:
            parsed = parser(text)
            return parsed.replace(tzinfo=parsed.tzinfo or timezone.utc)
        except ValueError:
            pass
    for fmt in ("%b %d, %Y %I:%M %p", "%d/%m/%Y %H:%M"):
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return datetime.fromtimestamp(0, tz=timezone.utc)


def _attachments(item: dict, root: Path) -> tuple[Attachment, ...]:
    found: list[Attachment] = []
    for kind in ("photos", "videos", "audio_files", "files", "gifs"):
        for entry in item.get(kind, []) or []:
            uri = entry.get("uri", "") if isinstance(entry, dict) else ""
            candidate = (root / uri).resolve() if uri else None
            if candidate is not None and root.resolve() not in candidate.parents:
                candidate = None
            found.append(Attachment(kind, uri, candidate if candidate and candidate.is_file() else None))
    if item.get("share") and isinstance(item["share"], dict):
        uri = item["share"].get("link", "")
        found.append(Attachment("share", uri, None))
    return tuple(found)


class _MessageHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.rows: list[list[str]] = []
        self._row: list[str] | None = None
        self._depth = 0
        self.title = "Conversa"

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        classes = dict(attrs).get("class", "") or ""
        if tag == "div" and ("pam" in classes.split() or "message" in classes.split()):
            if self._row is None:
                self._row, self._depth = [], 1
            else:
                self._depth += 1
        elif self._row is not None and tag == "div":
            self._depth += 1

    def handle_data(self, data: str) -> None:
        clean = data.strip()
        if self._row is not None and clean:
            self._row.append(clean)

    def handle_endtag(self, tag: str) -> None:
        if self._row is not None and tag == "div":
            self._depth -= 1
            if self._depth == 0:
                if len(self._row) >= 2:
                    self.rows.append(self._row)
                self._row = None


class InstagramArchive:
    """Context manager holding a temporary, local-only archive extraction."""

    def __init__(self, zip_path: str | Path):
        self.zip_path = Path(zip_path)
        self._temporary: tempfile.TemporaryDirectory[str] | None = None
        self.root: Path | None = None
        self.conversations: list[Conversation] = []

    def __enter__(self) -> "InstagramArchive":
        self.load()
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def load(self) -> list[Conversation]:
        if self.zip_path.suffix.lower() != ".zip" or not is_zipfile(self.zip_path):
            raise ArchiveError("Envie exclusivamente o ZIP da exportação oficial do Instagram.")
        if self.zip_path.stat().st_size > MAX_ARCHIVE_BYTES:
            raise ArchiveError("O ZIP excede o limite de 250 MB.")
        self.close()
        self._temporary = tempfile.TemporaryDirectory(prefix="instagram-export-")
        self.root = Path(self._temporary.name)
        try:
            self._extract()
            self.conversations = self._parse()
            if not self.conversations:
                raise ArchiveError("Nenhuma conversa JSON ou HTML reconhecida foi encontrada.")
            return self.conversations
        except Exception:
            self.close()
            raise

    def _extract(self) -> None:
        assert self.root is not None
        try:
            with ZipFile(self.zip_path) as archive:
                members = archive.infolist()
                if len(members) > MAX_FILES:
                    raise ArchiveError("O ZIP contém arquivos demais.")
                if sum(i.file_size for i in members) > MAX_EXTRACTED_BYTES:
                    raise ArchiveError("O conteúdo descompactado excede 750 MB.")
                for info in members:
                    try:
                        target = validate_member(info, self.root)
                    except ValueError as exc:
                        raise ArchiveError(str(exc)) from exc
                    if info.is_dir():
                        target.mkdir(parents=True, exist_ok=True)
                        continue
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with archive.open(info) as source, target.open("wb") as output:
                        shutil.copyfileobj(source, output, length=1024 * 1024)
        except BadZipFile as exc:
            raise ArchiveError("ZIP inválido ou corrompido.") from exc

    def _parse(self) -> list[Conversation]:
        assert self.root is not None
        paths = list(self.root.rglob("message_*.json")) + list(self.root.rglob("message_*.html"))
        paths += [p for p in self.root.rglob("messages.html") if p not in paths]
        return [conversation for path in sorted(paths) if (conversation := self._parse_file(path))]

    def _parse_file(self, path: Path) -> Conversation | None:
        assert self.root is not None
        if path.suffix.lower() == ".json":
            try:
                data = json.loads(path.read_text(encoding="utf-8-sig"))
            except (UnicodeError, json.JSONDecodeError) as exc:
                raise ArchiveError(f"JSON de mensagens inválido: {path.name}") from exc
            if not isinstance(data, dict) or not isinstance(data.get("messages"), list):
                return None
            participants = tuple(_decode_meta(x.get("name")) for x in data.get("participants", []) if isinstance(x, dict))
            messages = [Message(
                sender=_decode_meta(item.get("sender_name")),
                sent_at=_date(item.get("timestamp_ms") or item.get("timestamp")),
                text=_decode_meta(item.get("content")),
                attachments=_attachments(item, self.root),
            ) for item in data["messages"] if isinstance(item, dict)]
            return Conversation(_decode_meta(data.get("title")) or ", ".join(participants), participants, messages, str(path.relative_to(self.root)))
        parser = _MessageHTMLParser()
        try:
            parser.feed(path.read_text(encoding="utf-8-sig"))
        except UnicodeError as exc:
            raise ArchiveError(f"HTML de mensagens inválido: {path.name}") from exc
        messages = [Message(row[0], _date(row[-1]), " ".join(row[1:-1])) for row in parser.rows]
        participants = tuple(dict.fromkeys(message.sender for message in messages))
        return Conversation(path.parent.name, participants, messages, str(path.relative_to(self.root))) if messages else None

    def close(self) -> None:
        self.conversations = []
        self.root = None
        if self._temporary is not None:
            self._temporary.cleanup()
            self._temporary = None

