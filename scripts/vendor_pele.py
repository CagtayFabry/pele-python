"""Maintainer-only vendoring; never invoked by installation or a build."""

from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import io
import json
import re
import tarfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def download(url: str) -> bytes:
    if not url.startswith("https://registry.npmjs.org/"):
        raise ValueError(f"Unexpected npm artifact URL: {url}")
    with urllib.request.urlopen(url, timeout=60) as response:
        return response.read()


def verify_integrity(archive: bytes, integrity: str) -> None:
    """Require npm's SHA-512 SRI before opening any archive member."""
    algorithm, digest = integrity.split("-", 1)
    if algorithm != "sha512":
        raise ValueError("Expected SHA-512 npm registry integrity")
    expected = base64.b64decode(digest, validate=True)
    if not hmac.compare_digest(hashlib.sha512(archive).digest(), expected):
        raise ValueError("npm archive integrity mismatch; no assets were written")


def vendor(version: str) -> None:
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError("Supply an exact published Pele version, e.g. 1.12.0")
    metadata_url = f"https://registry.npmjs.org/pele/{version}"
    metadata = json.loads(download(metadata_url))
    if metadata["name"] != "pele" or metadata["version"] != version:
        raise ValueError("Unexpected npm package identity")
    archive_url = metadata["dist"]["tarball"]
    archive = download(archive_url)
    integrity = metadata["dist"]["integrity"]
    verify_integrity(archive, integrity)

    # Read exact members, never extract archive paths to the filesystem.
    assets = {}
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as tar:
        for name in ("dist/pele.global.js", "LICENSE", "package.json"):
            member = tar.getmember(f"package/{name}")
            if not member.isfile():
                raise ValueError(f"Expected a regular archive member: {name}")
            stream = tar.extractfile(member)
            if stream is None:
                raise ValueError(f"Missing archive member: {name}")
            assets[name] = stream.read()
    package = json.loads(assets.pop("package.json"))
    if (package["name"], package["version"], package["license"]) != ("pele", version, "MIT"):
        raise ValueError("Unexpected archived package metadata or license")

    destination = ROOT / "src" / "pele_python" / "_vendor"
    destination.mkdir(parents=True, exist_ok=True)
    files = {}
    for name, content in assets.items():
        filename = Path(name).name
        (destination / filename).write_bytes(content)
        files[filename] = {
            "source_path": f"package/{name}",
            "sha256": hashlib.sha256(content).hexdigest(),
            "size_bytes": len(content),
        }
    manifest = {
        "name": "pele",
        "version": version,
        "license": "MIT",
        "source_url": archive_url,
        "metadata_url": metadata_url,
        "npm_integrity": integrity,
        "archive_sha256": hashlib.sha256(archive).hexdigest(),
        "files": files,
    }
    (destination / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Vendored unmodified Pele {version}: {files['pele.global.js']['size_bytes']:,} bytes")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True)
    vendor(parser.parse_args().version)
