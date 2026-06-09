# vhs tape: full demo (ingest + ask). REQUIRES ANTHROPIC_API_KEY in .env.
# Run with: vhs docs/screenshots/demo.tape
# Output:    docs/screenshots/demo.gif
#
# Prereqs:
#   - Docker running
#   - .env file with ANTHROPIC_API_KEY=sk-ant-...
#   - .venv activated (or vhs will use system python)

Output docs/screenshots/demo.gif

Set Shell zsh
Set FontSize 14
Set Width 1200
Set Height 820
Set TypingSpeed 40ms
Set Theme "Catppuccin Mocha"

Type "cd ~/git/portfolio/markdown-rag"
Enter
Sleep 400ms

Type "source .venv/bin/activate"
Enter
Sleep 300ms

Type "set -a; source .env; set +a   # load ANTHROPIC_API_KEY"
Enter
Sleep 600ms

Type "# One command: bring up Qdrant, wait, ingest, ask"
Enter
Sleep 600ms

Type "make demo"
Enter
# `make demo` runs: docker compose up -d (~3s) → wait (~1s) → ingest (~10-15s)
# → ask (Claude streams ~5-10s). Generous sleep so the whole stream lands.
Sleep 35s

Type ""
Enter
Sleep 2s
