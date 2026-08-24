from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import date
from typing import Iterable

from .models import Conversation, Message


@dataclass(frozen=True)
class SearchResult:
    conversation: Conversation
    message: Message
    before: tuple[Message, ...] = ()
    after: tuple[Message, ...] = ()
    matched_in: tuple[str, ...] = ()


def _searchable(value: str) -> str:
    """Normalize handles and display names without changing the evidence shown."""
    value = unicodedata.normalize("NFKD", value.casefold())
    return "".join(character for character in value if character.isalnum())


def search(conversations: Iterable[Conversation], name: str = "", keyword: str = "",
           start: date | None = None, end: date | None = None,
           context: int = 0) -> list[SearchResult]:
    """Find matching messages and, optionally, their local conversation context.

    Context is selected from the same exported conversation only. It is deliberately
    capped so a malformed request cannot cause an unexpectedly large rendered page.
    """
    name, keyword = _searchable(name), keyword.casefold().strip()
    context = max(0, min(context, 5))
    results: list[SearchResult] = []
    for conversation in conversations:
        conversation_fields = {
            "título": conversation.title,
            "participantes": " ".join(conversation.participants),
            "arquivo de origem": conversation.source,
        }
        conversation_matches = tuple(
            label for label, value in conversation_fields.items()
            if name and name in _searchable(value)
        )
        ordered = sorted(conversation.messages, key=lambda message: message.sent_at)
        for index, message in enumerate(ordered):
            day = message.sent_at.date()
            if start and day < start or end and day > end:
                continue
            if keyword and keyword not in message.text.casefold():
                continue
            message_fields = {
                "remetente": message.sender,
                "texto": message.text,
                "caminho de anexo": " ".join(attachment.original_path for attachment in message.attachments),
            }
            message_matches = tuple(
                label for label, value in message_fields.items()
                if name and name in _searchable(value)
            )
            matched_in = tuple(dict.fromkeys((*conversation_matches, *message_matches)))
            if name and not matched_in:
                continue
            results.append(SearchResult(
                conversation,
                message,
                tuple(ordered[max(0, index - context):index]),
                tuple(ordered[index + 1:index + context + 1]),
                matched_in,
            ))
    return sorted(results, key=lambda result: result.message.sent_at, reverse=True)


def anonymize(text: str) -> str:
    patterns = [
        (r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b", "[CPF]"),
        (r"(?<!\d)(?:\+?55\s*)?(?:\(?\d{2}\)?\s*)?9?\d{4}[-\s]?\d{4}(?!\d)", "[TELEFONE]"),
        (r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", "[E-MAIL]"),
        (r"(?i)\b(?:rua|avenida|av\.|travessa|alameda)\s+[\wÀ-ÿ .'-]+(?:,\s*\d+)?", "[ENDEREÇO]"),
    ]
    for pattern, replacement in patterns:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE if "(?i)" not in pattern else 0)
    return text
