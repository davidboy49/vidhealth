# Architecture diagram

`architecture.html` is an interactive, self-contained system map of the Hermes
health tracker: Garmin sync → Postgres → dashboard/bot/AI coach, with a "VPS:
systemd services" boundary. Open it directly in a browser — pan/zoom, click a
node, switch dark mode, or step through the guided views at the top.

`architecture.json` is its typed source, authored with the [Archify](https://github.com/tt-a1i/archify)
agent skill. To update the diagram after a real architecture change, edit
`architecture.json` and regenerate:

```bash
npx skills add tt-a1i/archify -g   # once, if not already installed
cd ~/.agents/skills/archify
node bin/archify.mjs validate architecture path/to/docs/architecture.json --quality showcase --json
node bin/archify.mjs deliver architecture path/to/docs/architecture.json path/to/docs/architecture.html --quality showcase --json
```

Don't hand-edit `architecture.html` — it's a generated, checksummed artifact.
