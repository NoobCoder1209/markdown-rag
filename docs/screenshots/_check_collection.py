#!/usr/bin/env python3
"""Print a one-line summary of the markdown-rag Qdrant collection."""

import json
import sys
from urllib.request import urlopen

QDRANT_URL = "http://localhost:6333/collections/markdown-rag"

with urlopen(QDRANT_URL, timeout=5) as resp:
    data = json.load(resp)

r = data["result"]
v = r["config"]["params"]["vectors"]
print(f"points={r['points_count']} dim={v['size']} distance={v['distance']} status={r['status']}")

idx = r.get("payload_schema", {}).get("source_file", {})
if idx:
    print(f"payload_index source_file=keyword ({idx.get('points', '?')} points)")

sys.exit(0)
