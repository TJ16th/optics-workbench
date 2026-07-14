from __future__ import annotations

import os
from pathlib import Path
import tempfile
import threading
import time
import uuid
from dataclasses import dataclass


@dataclass(frozen=True)
class Artifact:
    category: str
    id: str
    path: str
    content_type: str
    expires_at: float

    @property
    def content(self) -> bytes:
        return Path(self.path).read_bytes()


class ArtifactStore:
    def __init__(self, ttl_seconds: float | None = None, root_dir: str | os.PathLike[str] | None = None):
        if ttl_seconds is None:
            ttl_seconds = float(os.environ.get("OPTICS_ARTIFACT_TTL_SECONDS", "1800.0"))
        self.ttl_seconds = float(ttl_seconds)
        self.root_dir = Path(root_dir or tempfile.mkdtemp(prefix="optics-artifacts-"))
        self.root_dir.mkdir(parents=True, exist_ok=True)
        self._items: dict[tuple[str, str], Artifact] = {}
        self._lock = threading.RLock()

    def put(self, category: str, content: bytes, *, content_type: str = "application/octet-stream", id: str | None = None) -> Artifact:
        with self._lock:
            self.gc()
            category = str(category)
            artifact_id = id or uuid.uuid4().hex
            artifact_dir = self.root_dir / category
            artifact_dir.mkdir(parents=True, exist_ok=True)
            path = artifact_dir / str(artifact_id)
            temporary = artifact_dir / f".{artifact_id}.{uuid.uuid4().hex}.tmp"
            temporary.write_bytes(bytes(content))
            os.replace(temporary, path)
            artifact = Artifact(
                category=category,
                id=str(artifact_id),
                path=str(path),
                content_type=str(content_type),
                expires_at=time.time() + self.ttl_seconds,
            )
            self._items[(artifact.category, artifact.id)] = artifact
            return artifact

    def get(self, category: str, id: str) -> Artifact | None:
        artifact, status = self.get_with_status(category, id)
        return artifact if status == "ok" else None

    def get_with_status(self, category: str, id: str) -> tuple[Artifact | None, str]:
        with self._lock:
            key = (str(category), str(id))
            artifact = self._items.get(key)
            if artifact is None:
                return None, "not_found"
            if artifact.expires_at <= time.time():
                self._delete(key, artifact)
                return None, "expired"
            return artifact, "ok"

    def gc(self) -> None:
        with self._lock:
            now = time.time()
            expired = [key for key, artifact in self._items.items() if artifact.expires_at <= now]
            for key in expired:
                self._delete(key, self._items[key])

    def _delete(self, key: tuple[str, str], artifact: Artifact) -> None:
        self._items.pop(key, None)
        try:
            Path(artifact.path).unlink(missing_ok=True)
        except OSError:
            pass


ARTIFACT_STORE = ArtifactStore()


def artifact_uri(artifact: Artifact) -> str:
    return f"artifact://{artifact.category}/{artifact.id}"
