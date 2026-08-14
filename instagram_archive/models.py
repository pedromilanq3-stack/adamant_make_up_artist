from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class Attachment:
    kind: str
    original_path: str
    local_path: Path | None

    @property
    def exists(self) -> bool:
        return self.local_path is not None and self.local_path.is_file()


@dataclass(frozen=True)
class Message:
    sender: str
    sent_at: datetime
    text: str
    attachments: tuple[Attachment, ...] = ()


@dataclass
class Conversation:
    title: str
    participants: tuple[str, ...]
    messages: list[Message] = field(default_factory=list)
    source: str = ""

