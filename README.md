# Telecom Anomaly Detection

Synthetic telecom Call Detail Records (CDR) generator with configurable anomalies for benchmarking fraud/anomaly detection methods.

## 🚀 Features

- **Realistic CDR generation**: Users, towers, social communities, and daily calling behavior
- **Anomaly injection**: Short calls, long calls, off-hour calls, burst patterns
- **Reproducible**: Seeded randomness for consistent datasets
- **Visual analysis**: Auto-generated plots summarizing distributions
- **Extensible**: Modular design for adding new anomaly types or generators

## 📁 Project Structure

```text
dataset/
  raw/                      # Generated CSVs and analysis plot
docs/                       # Papers and references
src/
  data/
    config.py               # Centralized configuration (dataset scale, distributions)
    main.py                 # Entrypoint to generate the dataset
    utils.py                # Helpers (towers, profiles, IMEI generator)
    generators/
      anomaly_injector.py   # Implements anomaly injections
      cdr_generator.py      # (Expected) CDR generation logic
      social_struct_generator.py  # (Expected) Social graph and communities
    schemas/
      cdr_schema.py         # CDR schema
      user_schema.py        # User schema
README.md
requirements.txt
```

## 🛠️ Quick Start

### Prerequisites
- Python 3.9+ (recommended 3.12.10)
- pip/venv (or Conda)

### Installation
```bash
# From repository root
python -m venv .venv
. .venv/Scripts/activate   # Windows PowerShell
pip install -r requirements.txt
```

### Generate the dataset
The current imports in `src/data/main.py` assume you run the script from inside `src/data`.

```bash
cd src/data
python main.py
```

Outputs will be written to `dataset/raw/` at repository root:

- `cdr_call_records.csv`
- `cdr_user_profiles.csv`
- `cdr_cell_towers.csv`
- `cdr_communities.csv`
- `cdr_dataset_analysis.png`

## ⚙️ Configuration

Adjust dataset size, anomaly ratio, and distributions in `src/data/config.py`:

- `Config.NUM_USERS`: number of users
- `Config.NUM_CELL_TOWERS`: number of towers
- `Config.DAYS`: number of simulated days
- `Config.ANOMALY_RATIO`: fraction of calls that are anomalous (e.g., 0.05)

Time-of-day and duration distributions can be tuned via `TIME_DISTRIBUTIONS` and `DURATION_DISTRIBUTIONS` in the same file.

## 📦 Generated Data Schema (high level)

- `cdr_call_records.csv` (subset): `call_id`, `caller_id`, `callee_id`, `call_start_ts`, `call_end_ts`, `call_duration`,
  `first_cell_id`, `last_cell_id`, `caller_imei`, `caller_imsi`, `callee_imsi`, `is_anomaly`, `anomaly_type`
- `cdr_user_profiles.csv`: `user_id`, `phone_number`, `imei`, `imsi`, `home_cell_id`, `user_type`, `creation_date`, `call_pattern`
- `cdr_cell_towers.csv`: `cell_id`, `latitude`, `longitude`, `area_type`, `tower_type`
- `cdr_communities.csv`: `user_id`, `community_type`, `community_id`, `community_size`

## 🔎 Anomaly Types

- `short_call`: 1–5 seconds
- `long_call`: 1–2 hours
- `off_hour_call`: calls between 02:00–05:00
- `burst_call`: 10–20 short calls within ~1 hour window

## 🧪 Reproducibility

Random seeds are set in `config.py` to ensure deterministic generation across runs with the same configuration.

## 🧰 Development Notes

- Run from `src/data` as shown above to satisfy import paths in `main.py`.
- To extend anomalies, add methods to `generators/anomaly_injector.py` and integrate in `main.py`.
- To change social structures or base CDR logic, update `social_struct_generator.py` and `cdr_generator.py`.

## ❗ Troubleshooting

- If you see import errors like `from config import Config` not found, ensure you are running from `src/data`.
- If plotting fails in headless environments, set a non-interactive backend before imports:
  ```python
  import matplotlib
  matplotlib.use("Agg")
  ```
- If dependency resolution fails, verify Python version and the versions in `requirements.txt`.

## 📚 References

Relevant background and reference materials are in `docs/`. See particularly:
- Real-time fraud detection references in charging systems
- CDR-based anomaly detection and social network analysis papers

---

Maintained for research and benchmarking purposes. Contributions welcome via pull requests.
