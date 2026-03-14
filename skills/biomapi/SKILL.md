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

### Check API status

```bash
python3 scripts/biomapi.py status
```


## Output Behavior

**Be concise.** The user is a clinical expert. Do NOT:
- Comment on, interpret, or analyze the biometric values
- Provide clinical opinions or surgical recommendations
- Explain what the measurements mean
- Flag values as unusual or noteworthy
- Add any commentary beyond what is specified below

The only exception: if a value falls **outside the validation ranges** defined in [reference.md](reference.md) (e.g., AL outside 14–40mm, K outside 20–99D), append a brief warning. Otherwise, stay silent — the user knows how to interpret the data.

Provide commentary, interpretation, or recommendations only if the user **explicitly asks**.

## Presenting Results

**Default output** — one compact block per file:

```
Patient: NAME (ID: 12345)
BiomPIN: word-word-123456
BiomAPI: https://biomapi.com/pin/word-word-123456
ESCRS IOL Calculator: https://appiolcalculator-ts.azurewebsites.net/?biompin=word-word-123456
```

- **Process with `--pin` by default**; omit only if the user explicitly requests no BiomPIN
- If no BiomPIN: show patient line only, no URLs
- No table, no raw JSON unless the user explicitly asks

**If the user asks for the biometry table**, present it as a compact table with device name as header, both eyes side by side, measurements in this exact order:

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

**If the user asks to save the JSON**, write it as an artifact/object (a named file attachment the user can download), not a fenced code block. The JSON can be re-uploaded to BiomAPI for validation via the BiomJSON engine.

## ESCRS IOL Calculation Shortcut

When the user asks for an **ESCRS IOL calculation** (or similar phrasing like "calculate the IOL", "run this through ESCRS", etc.) given a biometry PDF or image, the default output already includes the ESCRS link — no special handling needed. Just process normally with `--pin`.

## Saving Results

Only save if the user asks. For CSV, create a row per eye with all measurements as columns — but only if requested.

## Error Handling

The script outputs JSON with `"error": true` on failure. Keep error messages brief:
- **429**: Rate limited (30/day public). Suggest setting `BIOMAPI_KEY` for higher limits.
- **Connection failed**: Service may be temporarily unavailable.
- **Unsupported file type**: Only `.pdf`, `.png`, `.jpg`, `.jpeg` supported.
- **File too large**: Max 20MB.

## File Handling

When the user explicitly provides files as biometry printouts for processing, pass the file path directly to `biomapi.py process` without using the Read tool first — the script handles all file I/O and reading it beforehand wastes time and context.

## Multiple Files

When multiple files are provided, pass all paths in a **single** `biomapi.py process` call — the script handles concurrency internally:

```bash
python3 scripts/biomapi.py process file1.pdf file2.pdf file3.pdf --pin
```

The script outputs one JSON object per line, in input order. Present each as its own compact block. Only add a comparison summary if the user asks for one.
