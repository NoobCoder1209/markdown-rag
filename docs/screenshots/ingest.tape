# vhs tape: ingest-only demo (no API key required)
# Run with: vhs docs/screenshots/ingest.tape
# Output:    docs/screenshots/ingest.gif

Output docs/screenshots/ingest.gif

Set Shell zsh
Set FontSize 14
Set Width 1200
Set Height 720
Set TypingSpeed 40ms
Set Theme "Catppuccin Mocha"

Type "cd ~/git/portfolio/markdown-rag"
Enter
Sleep 400ms

Type "source .venv/bin/activate"
Enter
Sleep 400ms

Type "# 1. Bring up Qdrant in Docker"
Enter
Sleep 600ms
Type "make up"
Enter
Sleep 5s

Type "# 2. Wait until Qdrant answers"
Enter
Sleep 400ms
Type "make wait"
Enter
Sleep 2s

Type "# 3. Chunk + embed + upsert all 12 markdown files"
Enter
Sleep 600ms
Type "make ingest"
Enter
Sleep 16s

Type "# 4. Verify the collection in Qdrant"
Enter
Sleep 600ms
Type "python docs/screenshots/_check_collection.py"
Enter
Sleep 3s

Type "# 68 chunks, 384-dim cosine, payload index on source_file ✓"
Enter
Sleep 3s
