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

### Claude.ai / ChatGPT

1. Download [`biomapi-skill.zip`](biomapi-skill.zip) from this repo
2. Follow your platform's skill upload instructions to add the skill
3. The skill activates automatically once installed

Requires network access enabled and `biomapi.com` whitelisted in your AI assistant settings.

### Claude Code (CLI)

```bash
/plugin marketplace add mglraimundo/biomapi-skill
/plugin install biomapi-skill@mglraimundo-biomapi-skill
```

Updates are fetched automatically when the plugin version is bumped.

### Codex CLI

Download and extract the zip, then copy to your Codex skills folder:

```bash
cp -r skills/biomapi ~/.codex/skills/
```

## Usage

Just upload a biometry PDF or image to the conversation. The skill activates automatically and returns a compact summary:

```
Patient: JD (ID: 12345)
BiomPIN: lunar-rocket-731904
BiomAPI: https://biomapi.com/pin/lunar-rocket-731904
ESCRS IOL Calculator: https://appiolcalculator-ts.azurewebsites.net/?biompin=lunar-rocket-731904
```

Ask for the **biometry table** if you want the full measurements view. Multiple files are processed simultaneously.

### Extracted Data

**Core measurements** (per eye): Axial Length, ACD, K1/K2 with axes, WTW, Lens Thickness, CCT, lens status, post-refractive history, keratometric index.

**Posterior keratometry** (when available): PK1/PK2 with axes from supported devices — used for toric IOL formulas like Barrett Toric and EVO.

**Patient data**: Name (as privacy acronym), patient ID, date of birth, gender.

### BiomPIN sharing

A BiomPIN is generated **by default** with every extraction — no need to ask for it. The output includes a direct URL to view results and an ESCRS IOL Calculator link pre-loaded with the biometry data.

To skip BiomPIN generation, explicitly ask:

> "Process this biometry report without a PIN"

Retrieve shared data later:

> "Retrieve biometry data for lunar-rocket-731904"

### ESCRS IOL Calculator

The ESCRS link is included in every default output. To go straight to the calculator:

> "Calculate the IOL for this biometry"

> "Run this through the ESCRS calculator"

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

## Standalone CLI

No AI assistant? Use `biomapi.py` directly from the terminal — zero dependencies, pure Python stdlib.

```bash
# Download biomapi-cli.zip, unzip, then:
python biomapi.py process patient_report.pdf --pin
python biomapi.py retrieve lunar-rocket-731904
python biomapi.py csv *.json --output ./exports
python biomapi.py status
```

Results are saved as JSON files next to the source file. See [`cli/README.md`](cli/README.md) for the full reference including CSV columns, batch scripting examples, and error handling.

[**Download biomapi-cli.zip**](biomapi-cli.zip)

## How it works

The skill includes a zero-dependency Python script (`scripts/biomapi.py`) that sends files to the BiomAPI `/api/v1/biom/process` endpoint for extraction, then returns structured JSON that the AI assistant formats into a clinical summary. The same script powers the standalone CLI.

## License

MIT
