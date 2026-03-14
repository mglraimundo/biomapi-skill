# BiomAPI CLI

Standalone Python client for [BiomAPI](https://biomapi.com) — zero dependencies, pure stdlib, runs anywhere Python 3.11+ is installed.

Processes optical biometry reports (PDF/images) via the BiomAPI cloud service and saves structured results as JSON files. No AI assistant required.

## Requirements

- Python 3.11 or newer
- Internet access to `biomapi.com` (or a self-hosted BiomAPI instance)
- No external packages — only Python standard library

## Installation

Download `biomapi.py` and place it wherever you like:

```bash
# Make executable (macOS / Linux)
chmod +x biomapi.py

# Run directly
./biomapi.py status

# Or always via python
python biomapi.py status
```

## Configuration

Set environment variables before running, or export them in your shell profile:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `BIOMAPI_URL` | No | `https://biomapi.com` | API base URL (change for self-hosted) |
| `BIOMAPI_KEY` | No | *(none)* | API key for higher daily rate limits |

```bash
export BIOMAPI_URL=https://biomapi.com
export BIOMAPI_KEY=biom_your_key_here   # optional
```

**Public access** works out of the box with a daily limit of 30 extractions per IP. Set `BIOMAPI_KEY` for higher limits.

---

## Commands

### `process` — Extract biometry from a file

```
biomapi.py process <file> [<file2> ...] [--pin]
```

- Accepts PDF, PNG, JPG, JPEG (max 20 MB each)
- Multiple files are processed concurrently
- `--pin` generates a shareable BiomPIN for each file

**Results are always saved as JSON files** next to the source file, named `biomapi-{patient_id}-{device}.json`.

**Stdout** prints a compact summary line per file (useful for scripting):

```json
{"patient_id": "12345", "patient_name": "JD", "device": "IOLMaster 700", "biompin": "lunar-rocket-731904", "saved_json": "/abs/path/biomapi-12345-iolmaster700.json"}
```

**Examples:**

```bash
# Single file
python biomapi.py process patient_report.pdf

# Multiple files, generate BiomPINs
python biomapi.py process *.pdf --pin

# With custom API key
BIOMAPI_KEY=biom_abc123 python biomapi.py process scan.pdf
```

**Sample saved JSON structure** (abbreviated):

```json
{
  "data": {
    "biometer": { "device_name": "IOLMaster 700", "manufacturer": "Zeiss" },
    "patient": { "patient_id": "12345", "patient_name": "JD", "date_of_birth": "1960-01-15", "gender": "M" },
    "right_eye": {
      "AL": 23.45,
      "ACD": 3.12,
      "K1_magnitude": 43.50, "K1_axis": 90,
      "K2_magnitude": 44.25, "K2_axis": 180,
      "WTW": 11.8, "LT": 4.2, "CCT": 545,
      "lens_status": "phakic",
      "post_refractive": false,
      "keratometric_index": 1.3375
    },
    "left_eye": { "..." : "..." }
  },
  "extra_data": {
    "posterior_keratometry": {
      "device_name": "IOLMaster 700",
      "right_eye": { "PK1_magnitude": 6.15, "PK1_axis": 87, "PK2_magnitude": 6.32, "PK2_axis": 177 },
      "left_eye": { "PK1_magnitude": 6.20, "PK1_axis": 92, "PK2_magnitude": 6.38, "PK2_axis": 182 }
    }
  },
  "metadata": {
    "extraction_method": "BiomAI",
    "model": "gemini-3-flash-preview",
    "processing_time_ms": 3821
  },
  "biompin": "lunar-rocket-731904"
}
```

**Exit codes:**
- `0` — all files processed successfully
- `1` — one or more files failed (error details in stdout JSON)

---

### `retrieve` — Retrieve results using a BiomPIN

```
biomapi.py retrieve <biompin_code>
```

Fetches previously extracted data using a BiomPIN sharing code. The full JSON is saved to the current directory.

```bash
python biomapi.py retrieve lunar-rocket-731904
```

**Stdout:**
```json
{"patient_id": "12345", "patient_name": "JD", "device": "IOLMaster 700", "biompin": "lunar-rocket-731904", "saved_json": "/abs/path/biomapi-12345-iolmaster700.json"}
```

BiomPINs expire after 24 hours by default (configurable per instance).

---

### `csv` — Export JSON results to CSV

```
biomapi.py csv <file.json> [<file2.json> ...] [--output <dir>]
```

Converts one or more saved BiomAPI JSON files into a by-eye CSV. Each report contributes two rows (right eye, left eye).

```bash
# Export a single file
python biomapi.py csv biomapi-12345-iolmaster700.json

# Export multiple files to a specific folder
python biomapi.py csv *.json --output ./exports
```

**Output:** `biomapi_byeye.csv` in the current directory (or `--output` dir).

**Stdout:**
```json
{"byeye": "/abs/path/biomapi_byeye.csv"}
```

**CSV columns:**

| Column | Description |
|--------|-------------|
| `filename` | Source JSON filename |
| `right_eye` | `1` = right eye, `0` = left eye |
| `biometer_device_name` | Device model (e.g. IOLMaster 700) |
| `biometer_manufacturer` | Manufacturer (e.g. Zeiss) |
| `patient_name` | Patient name / acronym |
| `patient_patient_id` | Patient ID |
| `patient_date_of_birth` | Date of birth (ISO format) |
| `patient_gender` | Gender (M/F/Other/Unknown) |
| `AL` | Axial length (mm) |
| `ACD` | Anterior chamber depth (mm) |
| `K1_magnitude` | Flattest keratometry (D) |
| `K1_axis` | K1 axis (°) |
| `K2_magnitude` | Steepest keratometry (D) |
| `K2_axis` | K2 axis (°) |
| `WTW` | White-to-white corneal diameter (mm) |
| `LT` | Lens thickness (mm) |
| `CCT` | Central corneal thickness (μm) |
| `lens_status` | `phakic`, `pseudophakic`, or `aphakic` |
| `post_refractive` | `True` / `False` (prior refractive surgery) |
| `keratometric_index` | Keratometric index used (e.g. 1.3375) |

*Note: Posterior keratometry (PK1/PK2) is not included in the CSV export — it is available in the full JSON under `extra_data.posterior_keratometry`.*

---

### `status` — Check API health

```
biomapi.py status
```

Quick connectivity and health check:

```bash
python biomapi.py status
```

**Stdout:**
```json
{"status": "ok", "version": "0.9.7", "models": ["gemini-3-flash-preview"]}
```

---

## Scripting Examples

### Batch process a folder

```bash
#!/bin/bash
# Process all PDFs in a directory
for f in /path/to/reports/*.pdf; do
    echo "Processing: $f"
    python biomapi.py process "$f" --pin
done
```

### Batch process and collect results

```bash
# Process all files and collect compact summaries
python biomapi.py process /path/to/reports/*.pdf --pin > results.jsonl

# View with pretty-print (one line at a time)
while IFS= read -r line; do echo "$line" | python -m json.tool; done < results.jsonl
```

### Process and immediately export to CSV

```bash
#!/bin/bash
DIR=/path/to/reports
python biomapi.py process "$DIR"/*.pdf

# Collect all generated JSON files and export
python biomapi.py csv "$DIR"/biomapi-*.json --output "$DIR/exports"
```

### Check for errors in batch run

```bash
# Exit code 1 if any file fails
python biomapi.py process *.pdf || echo "One or more files failed"
```

### Use with jq (if installed)

```bash
# Extract just the BiomPIN from stdout
python biomapi.py process report.pdf --pin | jq -r '.biompin'

# Extract saved JSON path
python biomapi.py process report.pdf | jq -r '.saved_json'
```

---

## Error Handling

Errors are returned as JSON to stdout (not stderr), with `"error": true`:

```json
{"error": true, "status": 429, "detail": "Rate limit exceeded. Try again later or set BIOMAPI_KEY for higher limits."}
{"error": true, "file": "/path/to/file.pdf", "detail": "File not found: /path/to/file.pdf"}
{"error": true, "detail": "Connection failed: <urlopen error [Errno -2] Name or service not known>"}
```

**Common errors:**

| Status | Cause | Fix |
|--------|-------|-----|
| 429 | Rate limit exceeded | Wait 24h or use `BIOMAPI_KEY` |
| 400 | Invalid file format | Ensure file is PDF/PNG/JPG/JPEG |
| 413 | File too large | Maximum 20 MB per file |
| 503 | API temporarily overloaded | Retry after a short wait |
| Connection failed | Cannot reach biomapi.com | Check internet access / firewall |

---

## Supported Devices

| Device | Manufacturer | Posterior Keratometry |
|--------|-------------|----------------------|
| Aladdin | Topcon | — |
| Anterion | Heidelberg | Yes |
| Argos | Alcon | — |
| EyeStar ES900 | Haag-Streit | Yes |
| IOLMaster 700 | Zeiss | Yes |
| Lenstar LS 900 | Haag-Streit | — |
| MS-39 | CSO | Yes |
| OA-2000 | Tomey | — |
| Pentacam AXL | Oculus | Yes |
| Other | — | — |

Posterior keratometry (PK1/PK2) is extracted when available and stored under `extra_data.posterior_keratometry` in the JSON output.

---

## Re-uploading Edited JSON

BiomAPI supports a round-trip workflow:

1. Process a PDF → JSON saved to disk
2. Open the JSON, manually correct any field
3. Re-upload the edited JSON via `process` — BiomJSON engine validates it and preserves original metadata

```bash
# Re-upload an edited JSON (treated as manual/BiomHAND extraction)
python biomapi.py process biomapi-12345-iolmaster700-edited.json
```

---

## License

MIT — see [LICENSE](https://github.com/mglraimundo/biomapi-skill/blob/main/LICENSE).
