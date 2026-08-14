from __future__ import annotations

import re
from pathlib import Path, PurePosixPath
from zipfile import ZipInfo

MAX_ARCHIVE_BYTES = 250 * 1024 * 1024
MAX_EXTRACTED_BYTES = 750 * 1024 * 1024
MAX_FILES = 20_000
MAX_FILE_BYTES = 100 * 1024 * 1024
MAX_COMPRESSION_RATIO = 200

ALLOWED_EXTENSIONS = {
    ".json", ".html", ".htm", ".txt", ".jpg", ".jpeg", ".png", ".gif",
    ".webp", ".heic", ".mp4", ".mov", ".m4a", ".mp3", ".wav", ".ogg",
    ".aac", ".pdf", ".vcf",
}
EXECUTABLE_EXTENSIONS = {
    ".exe", ".dll", ".com", ".bat", ".cmd", ".msi", ".scr", ".ps1",
    ".sh", ".app", ".apk", ".jar", ".py", ".js", ".php", ".rb",
}


def safe_member_path(info: ZipInfo, destination: Path) -> Path:
    raw = info.filename.replace("\\", "/")
    path = PurePosixPath(raw)
    if not raw or raw.startswith("/") or path.is_absolute() or ".." in path.parts:
        raise ValueError(f"caminho inseguro no ZIP: {info.filename!r}")
    if re.match(r"^[A-Za-z]:", raw) or "\x00" in raw:
        raise ValueError(f"caminho inválido no ZIP: {info.filename!r}")
    target = (destination / Path(*path.parts)).resolve()
    root = destination.resolve()
    if target != root and root not in target.parents:
        raise ValueError(f"Zip Slip bloqueado: {info.filename!r}")
    return target


def validate_member(info: ZipInfo, destination: Path) -> Path:
    target = safe_member_path(info, destination)
    if info.is_dir():
        return target
    extension = target.suffix.lower()
    if extension in EXECUTABLE_EXTENSIONS or extension not in ALLOWED_EXTENSIONS:
        raise ValueError(f"formato não permitido: {info.filename!r}")
    if info.file_size > MAX_FILE_BYTES:
        raise ValueError(f"arquivo interno excede o limite: {info.filename!r}")
    if info.compress_size == 0 and info.file_size > 0:
        raise ValueError(f"arquivo suspeito no ZIP: {info.filename!r}")
    if info.compress_size and info.file_size / info.compress_size > MAX_COMPRESSION_RATIO:
        raise ValueError(f"taxa de compressão suspeita: {info.filename!r}")
    # Unix symlinks can escape the extraction root.
    if (info.external_attr >> 16) & 0o170000 == 0o120000:
        raise ValueError(f"link simbólico não permitido: {info.filename!r}")
    return target

