# Website

The project website is a single static page that presents the POC results to a general audience.

**Live at: <https://kshitijv97.github.io/ai-powered-data-governance/>**

## What it shows

| Section | Content | Source of truth |
|---|---|---|
| Hero | Headline figures: F1, defects caught, access checks, product limitations | `poc/results/summary.json` |
| The problem / Approach | Research question, why it matters, the seven POC stages | [README](../README.md#what-the-project-does) |
| Results | Classification chart and table, failing compliance tests, PIPEDA scorecard, access control, MCP answers | [Results](results.md), `poc/results/` |
| Product limitations | Six OpenMetadata 2.0.5 behaviours and their workarounds | [Results](results.md) |
| Takeaways | Supervised-control-system finding and study limits | [Results](results.md) |
| Responsible AI use | Tools, period, purposes, what AI did not do, checks, safeguards | [AI-use disclosure](ai-use.md) |
| Reproduce it | One-command run and links to the main docs pages | [Operations guide](operations.md) |

## How it is built

- One file, [`site/index.html`](../site/index.html): hand-written HTML, CSS and a small inline script. No build step, framework or external requests.
- The script does two things: the light/dark theme toggle (remembered in `localStorage` when the browser allows it) and the tooltips on the F1 chart.
- Colours are CSS custom properties on `:root`, redefined for dark mode. The layout works down to phone width without horizontal scrolling.

## How it is deployed

[`.github/workflows/pages.yml`](../.github/workflows/pages.yml) publishes the `site/` folder to GitHub Pages. It runs on every push to `master` that changes `site/**` or the workflow, and can be started by hand from the Actions tab (*pages → Run workflow*). GitHub Pages must be set to **Source: GitHub Actions** under *Settings → Pages*.

## Keeping it in sync

Every number on the page is copied by hand from `poc/results/`. After a new POC run:

1. Compare `poc/results/summary.json` with the hero figures, the F1 chart (bar widths, `data-tip` tooltips and the "Show as table" rows) and the compliance-test table.
2. Update [Results](results.md) and the README headline at the same time, so all three agree.
3. When the AI-use disclosure changes, update the *Responsible AI use* section together with [`docs/ai-use.md`](ai-use.md) and the README.

To preview locally:

```bash
python3 -m http.server 8791 --directory site
```

Then open <http://localhost:8791>. The same command is saved as the `site` configuration in `.claude/launch.json`.
