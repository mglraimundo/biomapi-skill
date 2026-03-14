---
name: biomapi
description: Process optical biometry reports (PDF/images) using BiomAPI AI extraction at biomapi.com. Use when the user uploads or references a biometry PDF or image and wants structured biometry data extracted, or when they mention a BiomPIN code (word-word-123456) to retrieve shared results. Returns patient info, a BiomPIN sharing link, and a preformed ESCRS IOL Calculator URL.
allowed-tools: Bash, Read, Glob
---

# BiomAPI - AI Biometry Extraction

Extract structured biometry data from optical biometry device reports (PDF/images) using the BiomAPI service at `https://biomapi.com`.

## When to Use This Skill

- User uploads or references a PDF/image that is an optical biometry report (from devices like IOLMaster, Lenstar, Anterion, Pentacam, etc.)
- User mentions a BiomPIN code (format: `word-word-123456`) to retrieve shared results
- User asks to check BiomAPI status
- User asks for an ESCRS IOL calculation given a biometry PDF/image (see **ESCRS IOL Calculation Shortcut** below)

## Data Reference

See [reference.md](reference.md) for the complete schema: all biometry fields with units and validation ranges, supported devices, enum values, posterior keratometry, and typical clinical ranges. Only load it when rendering a biometry table, checking validation ranges, or answering a clinical question — not on standard extractions.

## Client Script

The API client is at `scripts/biomapi.py` relative to this skill's directory. It requires only Python 3.10+ with zero external dependencies.

Run it via:

```bash
python3 scripts/biomapi.py <command> [args]
```

If the relative path doesn't resolve, try `${CLAUDE_SKILL_DIR}/scripts/biomapi.py`.

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `BIOMAPI_URL` | No | `https://biomapi.com` | API base URL |
| `BIOMAPI_KEY` | No | *(none)* | API key for higher rate limits |

Public access (no key) is rate-limited to 30 extractions/day per IP.

## Commands

### Process a biometry file

```bash
python3 scripts/biomapi.py process /path/to/report.pdf --pin
```

Multiple files in one call (processed concurrently inside the script):

```bash
python3 scripts/biomapi.py process file1.pdf file2.pdf file3.pdf --pin
```

- Accepts: `.pdf`, `.png`, `.jpg`, `.jpeg` (max 20MB)
- `--pin`: Generate a BiomPIN for secure sharing (**use by default**; omit only if user explicitly asks not to)

### Retrieve via BiomPIN

```bash
python3 scripts/biomapi.py retrieve word-word-123456
```

### Generate CSV export

```bash
python3 scripts/biomapi.py csv file1.json [file2.json ...] [--output /path/to/dir]
```

- Input: one or more `saved_json` paths (from `process` or `retrieve` output)
- `--output`: directory for the CSV file (default: current working directory)
- Output: `{"byeye": "/abs/path/biomapi_byeye.csv"}`

One row per eye (`right_eye` column: `1`=right, `0`=left). Columns: `filename`, `right_eye`, `biometer_device_name`, `biometer_manufacturer`, `patient_name`, `patient_patient_id`, `patient_date_of_birth`, `patient_gender`, `AL`, `ACD`, `K1_magnitude`, `K1_axis`, `K2_magnitude`, `K2_axis`, `WTW`, `LT`, `CCT`, `lens_status`, `post_refractive`, `keratometric_index`.

### Check API status

```bash
python3 scripts/biomapi.py status
```


## Output Behavior

**Be concise.** The user is a clinical expert. Do NOT comment on, interpret, or analyze biometric values. Provide commentary or recommendations only if the user **explicitly asks**.

## Script Output Format

The script always outputs a **compact summary** JSON (not the full API response) to stdout — one object per file in input order:

```json
{
  "patient_id": "12345",
  "patient_name": "J. DOE",
  "device": "IOLMaster 700",
  "biompin": "lunar-rocket-731904",
  "saved_json": "/abs/path/to/biomapi-12345-iolmaster700.json"
}
```

The **full raw API response** (including all metadata, LLM metrics, timings) is always saved to disk at `saved_json` automatically.

**Patient name**: ALWAYS use `patient_name` exactly as returned in the **compact stdout summary** (e.g., `"patient_name": "MAG"`). This is often an acronym or abbreviation — that is intentional. Do NOT replace it with the full name from the saved JSON, the PDF, the filename, or any other source. Even if the full JSON contains a longer or different name string, the compact summary's `patient_name` is the canonical display name. Never expand, reconstruct, or infer the name.

## Presenting Results

**Default output** — for each file:

1. Show the compact info block
2. Read `saved_json` with the `Read` tool and present the full JSON in a code block

```
Patient: J. DOE (ID: 12345)

BiomPIN: lunar-rocket-731904

BiomAPI: https://biomapi.com/pin/lunar-rocket-731904

ESCRS IOL Calculator: https://appiolcalculator-ts.azurewebsites.net/?biompin=lunar-rocket-731904
```

Each line (Patient, BiomPIN, BiomAPI link, ESCRS link) MUST be separated by a blank line for readability. Do not collapse them into a single block.

```json
{ ...full contents of saved_json... }
```

- **Process with `--pin` by default**; omit only if the user explicitly requests no BiomPIN
- If no BiomPIN: show patient line only (no URLs), then the JSON block
- No biometry table unless the user explicitly asks

**If the user asks for the biometry table**, use the `Read` tool on `saved_json` and render a compact table with device name as header, both eyes side by side, measurements in this exact order:

| {Device Name} | Right (OD) | Left (OS) |
|---|---|---|
| Lens Status | Phakic | Phakic |
| Post Refractive | None | None |
| AL (mm) | 23.45 | 23.52 |
| ACD (mm) | 3.12 | 3.08 |
| LT (mm) | 4.52 | 4.48 |
| WTW (mm) | 11.80 | 11.90 |
| CCT (μm) | 545 | 542 |
| n | 1.3375 | 1.3375 |
| K1 (D) | 43.25 | 43.00 |
| K1 Axis (°) | 5 | 175 |
| K2 (D) | 44.50 | 44.25 |
| K2 Axis (°) | 95 | 85 |

If `extra_data.posterior_keratometry` exists, add a **Posterior Keratometry** table:

| {PK Device Name} | Right (OD) | Left (OS) |
|---|---|---|
| PK1 (D) | 6.12 | 6.08 |
| PK1 Axis (°) | 8 | 172 |
| PK2 (D) | 6.45 | 6.38 |
| PK2 Axis (°) | 98 | 82 |

Table formatting rules:
- Show `null` values as `—`
- K1/K2 magnitude and axis are always separate rows (not combined)
- AL, ACD, LT, WTW: 2 decimal places. CCT: 0 decimals. n: 4 decimals. K1/K2/PK: 2 decimals. Axes: 0 decimals.


## ESCRS IOL Calculation Shortcut

When the user asks for an **ESCRS IOL calculation** (or similar phrasing like "calculate the IOL", "run this through ESCRS", etc.) given a biometry PDF or image, the default output already includes the ESCRS link — no special handling needed. Just process normally with `--pin`.


## Error Handling

The script outputs JSON with `"error": true` on failure. Keep error messages brief:
- **429**: Rate limited (30/day public). Suggest setting `BIOMAPI_KEY` for higher limits.
- **Connection failed**: Service may be temporarily unavailable.
- **Unsupported file type**: Only `.pdf`, `.png`, `.jpg`, `.jpeg` supported.
- **File too large**: Max 20MB.

## File Handling

Pass source file paths directly to `biomapi.py process` — never use the `Read` tool on them. The script handles all I/O; the LLM never sees the source file contents. Reading `saved_json` afterwards (to present the JSON artifact) is the only intentional file read.

For CSV export, use the `csv` command with the `saved_json` paths — never build CSV manually.

## Multiple Files

When multiple files are provided, pass all paths in a **single** `biomapi.py process` call — the script handles concurrency internally:

```bash
python3 scripts/biomapi.py process file1.pdf file2.pdf file3.pdf --pin
```

The script outputs one JSON object per line, in input order. Present each with its own info block and JSON artifact. Only add a comparison summary if the user asks for one.
