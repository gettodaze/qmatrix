# CSV conversion

Run with [uv](https://docs.astral.sh/uv/):

```bash
uv run --no-project --with pandas python parse_records.py
```

Reads `input.csv` and writes `output/yyyymmdd_hhss/<database>.csv`.
Each record uses its alphabetically first database.

Optional paths:

```bash
uv run --no-project --with pandas python parse_records.py other.csv --output outputs
```

## AI Usage
Codex was used to create this README.md and parse_records.py.