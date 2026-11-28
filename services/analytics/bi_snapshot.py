"""M86 immutable BI snapshot publication primitives."""
import hashlib
import json
import os
import tempfile
from pathlib import Path
import shutil

def publish_snapshot(root, tables):
    """Publish validated CSV bytes under a content-addressed snapshot.

    Caller must perform semantic quality checks before calling.
    """
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    if not tables or any(not isinstance(v, bytes) or not k.endswith(".csv")
                         or Path(k).name != k or "\\" in k for k,v in tables.items()):
        raise ValueError("Expected named CSV byte payloads")
    manifest = {"schema_version": 1, "files": {
        k: {"sha256": hashlib.sha256(v).hexdigest(), "bytes": len(v)}
        for k,v in sorted(tables.items())}}
    raw = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
    snapshot = hashlib.sha256(raw).hexdigest()
    dest = root / snapshot
    stage = Path(tempfile.mkdtemp(prefix=".snapshot-", dir=root))
    pointer = None
    try:
        for name, data in tables.items():
            (stage / name).write_bytes(data)
        (stage / "manifest.json").write_bytes(raw)
        try:
            stage.rename(dest)
        except OSError:
            if not dest.is_dir():
                raise
        if (dest / "manifest.json").read_bytes() != raw:
            raise ValueError("Snapshot manifest mismatch")
        for name, data in tables.items():
            if (dest / name).read_bytes() != data:
                raise ValueError("Snapshot content mismatch")
        with tempfile.NamedTemporaryFile(dir=root, prefix=".current-", delete=False) as f:
            pointer = Path(f.name)
            f.write(json.dumps({"snapshot": snapshot, "schema_version": 1}).encode())
            f.flush()
            os.fsync(f.fileno())
        os.replace(pointer, root / "current.json")
        return snapshot
    finally:
        shutil.rmtree(stage, ignore_errors=True)
        if pointer is not None:
            pointer.unlink(missing_ok=True)
