#!/usr/bin/env python3
"""Print a one-line summary of the markdown-rag Qdrant collection.

Respects QDRANT_URL and RAG_COLLECTION env vars so it works against
non-default deployments. Exits with a friendly message on a missing
collection or unreachable Qdrant rather than a traceback.
"""

import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333").rstrip("/")
COLLECTION = os.environ.get("RAG_COLLECTION", "markdown-rag")
URL = f"{QDRANT_URL}/collections/{COLLECTION}"

try:
    with urlopen(URL, timeout=5) as resp:
        data = json.load(resp)
except HTTPError as exc:
    if exc.code == 404:
        print(f"collection {COLLECTION!r} does not exist at {QDRANT_URL} — run `make ingest` first")
        sys.exit(1)
    print(f"Qdrant returned HTTP {exc.code}: {exc.reason}", file=sys.stderr)
    sys.exit(1)
except URLError as exc:
    print(
        f"cannot reach Qdrant at {QDRANT_URL}: {exc.reason}. Is `make up` running?",
        file=sys.stderr,
    )
    sys.exit(1)

r = data["result"]
v = r["config"]["params"]["vectors"]
print(f"points={r['points_count']} dim={v['size']} distance={v['distance']} status={r['status']}")

idx = r.get("payload_schema", {}).get("source_file")
if idx:
    points = idx.get("points")
    suffix = f" ({points} points)" if points is not None else ""
    print(f"payload_index source_file={idx.get('data_type', 'unknown')}{suffix}")

sys.exit(0)
