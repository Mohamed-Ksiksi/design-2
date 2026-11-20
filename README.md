# EcoCode

EcoCode is a Flask prototype for a code performance and environmental sustainability platform. It presents time complexity, execution time, energy consumption and carbon emissions in one engineering report, then offers an illustrative optimization comparison.

**Everything measured-looking in this application is demonstration data.** Submitted source code is treated as plain text. It is never compiled, interpreted, benchmarked or executed.

## Technology

Only Python, Flask, HTML5, CSS3 and Jinja2 are used.

- No JavaScript, no frontend framework, no charting library.
- No database, accounts or external services.
- Charts are plain HTML elements sized with CSS; no client-side rendering.
- Fonts are local system font stacks, so the app works offline.

## Install and run locally

```bash
cd ecocode
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
python app.py
```

Open <http://127.0.0.1:5000>.

If you prefer the Flask CLI:

```bash
flask --app app run --debug
```

A virtual environment already exists in the project folder on this machine; activate it with `venv\Scripts\activate` before running the commands above.

## Project structure

```
ecocode/
├── app.py                  Routes, validation, demonstration model and data
├── templates/
│   ├── base.html           Shared navigation, header, footer, flash messages
│   ├── index.html          Landing / overview
│   ├── workspace.html      Code submission workspace
│   ├── dashboard.html      Analysis dashboard with CSS charts
│   ├── comparison.html     Optimization and code comparison
│   ├── history.html        Analysis history and reports (two routes)
│   └── settings.html       Prototype preferences
├── static/css/
│   ├── style.css           Design tokens, navigation, landing, history, settings
│   ├── workspace.css       Editor-style textarea and settings panel
│   ├── dashboard.css       Metrics, CSS charts, technical analysis
│   └── comparison.css      Code panels, comparison table, before/after bars
├── static/images/          Reserved for future branding assets
├── requirements.txt
└── README.md
```

## Routes and workflow

| Route | Purpose |
|---|---|
| `GET /` | Overview / landing page |
| `GET, POST /analyze` | Workspace; accepts pasted code, uploaded `.py`/`.txt` files, language, input size and presets |
| `GET /dashboard` | Latest demonstration report |
| `GET /comparison` | Original vs illustrative optimized code and metrics |
| `GET /download-optimized` | Downloads the example optimized Python file |
| `GET /history` | Analysis history with server-side filters |
| `GET /reports` | The same archive presented as reports |
| `POST /history/view` | Loads a demonstration report from a history row |
| `GET /history/export.csv` | Downloads the visible history rows as CSV |
| `GET, POST /settings` | Prototype preferences |

Main path: **Overview → New analysis → Analyze code → Dashboard → OPTIMIZE MY CODE → Comparison.**

The latest report is kept in Flask's signed session cookie. Uploaded files are limited to 1 MB; submitted code is limited to 3,000 characters so it fits comfortably in that cookie.

## What works today

- Navigation throughout the application, with the active page marked.
- Ordinary HTML forms and Flask POST routes for all actions.
- Code entry, file upload, clear/load-sample actions, input-size presets and validation messages.
- Four metrics with formatted values and units, scaled to the chosen input size.
- Four CSS-only visualisations: time, energy, carbon and scalability.
- Technical notes, loop inventory, submitted source viewer and recommendations.
- Fixed example optimized implementation with highlighted changed lines.
- Metric comparison table, relative improvement bars and an explanation.
- Download of the example optimized code (no clipboard script; select the code to copy it).
- History/reports with server-side search and filters, CSV export and working “View results” buttons.

## What needs a real backend later

The current figures come from a simple formula in `app.py` (`demo_point`). A production version would replace it with real services:

1. **Analysis** — parse the source (AST for Python), detect loops and inefficient patterns, and derive complexity from the structure rather than the fixed findings in `FINDINGS`.
2. **Execution time** — run code in an isolated sandbox with a timeout, limits and repeated trials. Never execute untrusted submissions in the Flask process.
3. **Energy** — collect CPU/power telemetry or apply a calibrated hardware model.
4. **Carbon** — use a real grid-region emission factor and timestamped data instead of the fixed `GRID_G_PER_WH`.
5. **Optimization** — generate a genuine rewrite, verify equivalence with tests, and highlight actual changed lines.
6. **Persistence** — move history from illustrative `HISTORY` rows and the session cookie to a database.
7. **Additional languages** — extend the language selector once analysers exist.

Keep the template variables and routes as they are and the presentation layer can remain largely unchanged while those services are added.

## Design notes

The interface uses a light paper-like background, hairline rules, a deep forest green accent and a warm clay colour for “original” values. Display typography is a serif stack, data and labels use a monospace stack, and body copy uses a system sans stack. No shadows, glowing effects, animations or decorative icon libraries are used.
