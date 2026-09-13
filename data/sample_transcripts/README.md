# Sample transcript dataset — READ BEFORE USING

**These files are synthetic, original content written for this project. They are NOT real
Lenny's Podcast transcripts.** Lenny's Podcast transcripts are copyrighted material owned by
Lenny Rachitsky and his guests; this project does not scrape, redistribute, or reproduce them.

Each file in this directory is clearly labeled `[DEMO]` in its title and uses a fictional
guest name, so the assistant's citations are never mistaken for real quotes from real people.
They exist purely so a fresh evaluator can run `scripts/ingest_transcripts.py` and immediately
see the full pipeline (chunk → embed → retrieve → cite → refuse-when-unsupported) working
end-to-end without needing real transcript access.

## Using real Lenny's Podcast transcripts

If you have legitimate access to real transcripts (e.g. your own notes, or transcripts you are
licensed to use), drop `.md` or `.txt` files into this directory (or point
`scripts/ingest_transcripts.py --source <dir>` at another directory) using the same frontmatter
format:

```markdown
---
title: Episode title
guest: Guest name
url: https://www.lennyspodcast.com/...
published_at: 2024-01-15
---

Transcript body text...
```

The ingestion pipeline is source-agnostic — it doesn't know or care whether a file is real or
synthetic, it only cares about the frontmatter + body shape above.
