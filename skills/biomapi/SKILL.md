---
name: biomapi
description: Process optical biometry reports (PDF/images) using BiomAPI AI extraction at biomapi.com. Use when the user uploads or references a biometry PDF or image and wants structured biometry data extracted, or when they mention a BiomPIN code (word-word-123456) to retrieve shared results. Returns measurements like axial length, keratometry, ACD, and more — formatted as a clinical biometry table.
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

See [reference.md](reference.md) for the complete schema: all biometry fields with units and validation ranges, supported devices, enum values, posterior keratometry, and typical clinical ranges. Consult it to interpret results and answer clinical questions about the data.

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

## API Response Structure

```json
{
  "success": true,
  "data": {
    "biometer": { "device_name": "IOLMaster700", "manufacturer": "Zeiss" },
    "patient": { "name": "JD", "patient_id": "12345", "date_of_birth": "1965-03-15", "gender": "Male" },
    "right_eye": {
      "AL": 23.45, "ACD": 3.12,
      "K1_magnitude": 43.25, "K1_axis": 5,
      "K2_magnitude": 44.50, "K2_axis": 95,
      "WTW": 11.8, "LT": 4.52, "CCT": 545,
      "lens_status": "Phakic", "post_refractive": "None",
      "keratometric_index": 1.3375
    },
    "left_eye": { "AL": 23.52, "ACD": 3.08, "...": "..." }
  },
  "extra_data": {
    "posterior_keratometry": {
      "pk_device_name": "IOLMaster700",
      "right_eye": { "PK1_magnitude": 6.12, "PK1_axis": 8, "PK2_magnitude": 6.45, "PK2_axis": 98 },
      "left_eye": { "PK1_magnitude": 6.08, "PK1_axis": 172, "PK2_magnitude": 6.38, "PK2_axis": 82 }
    }
  },
  "metadata": {
    "api_version": "0.9.7",
    "extraction_info": { "extraction_method": "BiomAI", "...": "..." },
    "biompin": { "pin": "lunar-rocket-731904", "expires_at_timestamp": "2025-01-18T10:30:00Z" }
  }
}
```

## Output Behavior

**Be concise.** The user is a clinical expert. After extraction, present ONLY the data table below. Do NOT:
- Comment on, interpret, or analyze the biometric values
- Provide clinical opinions or surgical recommendations
- Explain what the measurements mean
- Flag values as unusual or noteworthy
- Add any commentary beyond the table itself

The only exception: if a value falls **outside the validation ranges** defined in [reference.md](reference.md) (e.g., AL outside 14–40mm, K outside 20–99D), append a brief warning below the table. Otherwise, stay silent — the user knows how to interpret the data.

Provide commentary, interpretation, or recommendations only if the user **explicitly asks**.

## Presenting Results

Present results as a compact table matching the BiomAPI website format.

**Patient info** (one line): `NAME (ID) • DOB • Gender`

**Biometry table** — device name as header, both eyes side by side, measurements in this exact order:

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

Rules:
- Show `null` values as `—`
- K1/K2 magnitude and axis are always separate rows (not combined)
- AL, ACD, LT, WTW: 2 decimal places. CCT: 0 decimals. n: 4 decimals. K1/K2/PK: 2 decimals. Axes: 0 decimals.
- **Process with `--pin` by default**; omit only if the user explicitly requests no BiomPIN

**After the table(s)**, always include:

1. **BiomPIN block** — the PIN, expiration, and a clickable URL:

```
BiomPIN: word-word-123456
URL: https://biomapi.com/pin/word-word-123456
ESCRS IOL Calculator: https://appiolcalculator-ts.azurewebsites.net/?biompin=word-word-123456
```

2. **Raw JSON** — the full API response in a fenced code block for easy copy-paste:

~~~
```json
{ full JSON response here }
```
~~~

If the user opted out of BiomPIN, skip the BiomPIN block and URL — just show the table and raw JSON.

**That's it.** No metadata footer, no commentary. Just the table, BiomPIN, and raw JSON.

## ESCRS IOL Calculation Shortcut

When the user asks for an **ESCRS IOL calculation** (or similar phrasing like "calculate the IOL", "run this through ESCRS", etc.) given a biometry PDF or image:

1. Process the file normally with `--pin` (the BiomPIN is required for the ESCRS link)
2. Present **only** the preformed ESCRS IOL Calculator link — no table, no BiomPIN block, no raw JSON:

```
ESCRS IOL Calculator: https://appiolcalculator-ts.azurewebsites.net/?biompin=word-word-123456
```

That's the entire output. The user wants to go straight to the calculator.

## Saving Results

Only offer to save if the user asks. Default format is the full JSON response saved to a file (e.g., `patient_biometry.json`). The JSON can be re-uploaded to BiomAPI for validation via the BiomJSON engine. For CSV, create a row per eye with all measurements as columns — but only if requested.

## Error Handling

The script outputs JSON with `"error": true` on failure. Keep error messages brief:
- **429**: Rate limited (30/day public). Suggest setting `BIOMAPI_KEY` for higher limits.
- **Connection failed**: Service may be temporarily unavailable.
- **Unsupported file type**: Only `.pdf`, `.png`, `.jpg`, `.jpeg` supported.
- **File too large**: Max 20MB.

## Multiple Files

Process sequentially. Present each result as its own table. Only add a comparison summary if the user asks for one.
