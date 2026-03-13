# BiomAPI Skill

AI-powered biometry data extraction from optical biometry reports (PDF/images) via [biomapi.com](https://biomapi.com).

Upload a biometry PDF or image and get structured measurements (AL, K1, K2, ACD, CCT, and more) returned as a clinical biometry table.

## Supported Devices

| Device | Manufacturer | PK Support |
|--------|-------------|------------|
| Aladdin | Topcon | — |
| Anterion | Heidelberg | Yes |
| Argos | Alcon | — |
| EyeStar ES900 | Haag-Streit | Yes |
| IOLMaster 700 | Zeiss | Yes |
| Lenstar LS 900 | Haag-Streit | — |
| MS-39 | CSO | Yes |
| OA-2000 | Tomey | — |
| Pentacam AXL | Oculus | Yes |
| Other | Other | — |

PK Support = posterior keratometry (PK1/PK2) extraction for toric IOL calculations.

## Installation

### Claude.ai / ChatGPT (web)

1. Download [`biomapi-skill.zip`](biomapi-skill.zip) from this repo
2. Go to **Customize > Skills** and click **+** > **Upload a skill**
3. Upload the zip — the skill appears in your list and activates automatically

### Claude Code (CLI)

```bash
/plugin marketplace add mglraimundo/biomapi-skill
/plugin install biomapi-skill@mglraimundo-biomapi-skill
```

Updates are fetched automatically when the plugin version is bumped.

### OpenAI Codex CLI

```bash
cp -r skills/biomapi ~/.codex/skills/
```

## Usage

Just upload a biometry PDF or image to the conversation. The skill activates automatically and returns a formatted clinical table:

| Measurement | Right Eye (OD) | Left Eye (OS) |
|-------------|----------------|---------------|
| AL (mm)     | 23.45          | 23.52         |
| ACD (mm)    | 3.12           | 3.08          |
| K1 (D) @ axis | 43.25 @ 5°  | 43.00 @ 175°  |
| K2 (D) @ axis | 44.50 @ 95° | 44.25 @ 85°   |
| WTW (mm)    | 11.8           | 11.9          |
| LT (mm)     | 4.52           | 4.48          |
| CCT (um)    | 545            | 542           |

### Extracted Data

**Core measurements** (per eye): Axial Length, ACD, K1/K2 with axes, WTW, Lens Thickness, CCT, lens status, post-refractive history, keratometric index.

**Posterior keratometry** (when available): PK1/PK2 with axes from supported devices — used for toric IOL formulas like Barrett Toric and EVO.

**Patient data**: Name (as privacy acronym), patient ID, date of birth, gender.

### BiomPIN sharing

A BiomPIN is generated **by default** with every extraction — no need to ask for it. The output includes:

- **BiomPIN code** for sharing (e.g., `lunar-rocket-731904`)
- **Direct URL** to view results: `https://biomapi.com/pin/lunar-rocket-731904`
- **ESCRS IOL Calculator link** pre-loaded with the biometry data

To skip BiomPIN generation, explicitly ask:

> "Process this biometry report without a PIN"

Retrieve shared data later:

> "Retrieve biometry data for lunar-rocket-731904"

### ESCRS IOL Calculator

Ask for an IOL calculation and the skill extracts the biometry and returns a direct link to the ESCRS IOL Calculator pre-loaded with the data:

> "Calculate the IOL for this biometry"

> "Run this through the ESCRS calculator"

Only the calculator link is returned — no table or raw JSON — so you can go straight to the formulas.

### Save results

Ask to save as JSON or CSV:

> "Save the results to patient_biometry.json"

The JSON output is compatible with BiomAPI's re-upload flow for validation and editing.

## Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `BIOMAPI_URL` | No | `https://biomapi.com` | API base URL |
| `BIOMAPI_KEY` | No | *(none)* | API key for higher rate limits |

Public access works out of the box with a daily limit of 30 extractions per IP. Set `BIOMAPI_KEY` for higher limits.

## How it works

The skill includes a zero-dependency Python script (`scripts/biomapi.py`) that sends files to the BiomAPI `/api/v1/biom/process` endpoint for extraction, then returns structured JSON that the AI assistant formats into a clinical summary.

## License

MIT
