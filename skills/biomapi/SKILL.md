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
python3 scripts/biomapi.py process /path/to/report.pdf [--pin]
```

- Accepts: `.pdf`, `.png`, `.jpg`, `.jpeg` (max 20MB)
- `--pin`: Generate a BiomPIN for secure sharing

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
    "api_version": "0.9.6",
    "extraction_info": { "extraction_method": "BiomAI", "...": "..." },
    "biompin": { "pin": "lunar-rocket-731904", "expires_at_timestamp": "2025-01-18T10:30:00Z" }
  }
}
```

## Presenting Results

After a successful extraction, present results as a clinical biometry summary.

**Header**: Device name, manufacturer, patient info (name acronym, ID, DOB, gender).

**Biometry table** — both eyes side by side:

| Measurement | Right Eye (OD) | Left Eye (OS) |
|-------------|----------------|---------------|
| AL (mm) | 23.45 | 23.52 |
| ACD (mm) | 3.12 | 3.08 |
| K1 (D) @ axis | 43.25 @ 5° | 43.00 @ 175° |
| K2 (D) @ axis | 44.50 @ 95° | 44.25 @ 85° |
| WTW (mm) | 11.8 | 11.9 |
| LT (mm) | 4.52 | 4.48 |
| CCT (um) | 545 | 542 |
| Lens Status | Phakic | Phakic |

Rules:
- Show `null` values as `—`
- Combine K magnitude and axis: `43.25 @ 5°`
- If `extra_data.posterior_keratometry` exists, add a separate **Posterior Keratometry** table with PK1/PK2 values
- If a BiomPIN was generated, display it prominently with its expiry time

**Metadata footer**: Briefly note extraction method, model, and processing time.

## Saving Results

If the user asks to save or download the results:
- Save the full JSON response to a file (e.g., `patient_biometry.json`)
- For CSV export, create a row per eye with all measurements as columns

The JSON output can be re-uploaded to BiomAPI later for validation via the BiomJSON engine.

## Error Handling

The script outputs JSON with `"error": true` on failure:

- **Rate limit exceeded (429)**: Inform user of the 30/day public limit. Mention they can use an API key for higher limits by setting the `BIOMAPI_KEY` environment variable.
- **Connection failed**: The BiomAPI service may be temporarily unavailable. Suggest trying again shortly.
- **Unsupported file type**: Only PDF and images (.pdf, .png, .jpg, .jpeg) are supported.
- **File too large**: Maximum file size is 20MB.

## Multiple Files

If the user has multiple biometry reports, process each file sequentially and present a summary comparison table at the end showing key measurements (AL, K1, K2) for all patients/files.
