# Golemio Municipal Libraries Extractor

This project is a Python-based extractor for municipal library data from the [Golemio API](https://api.golemio.cz/). It fetches, processes, and saves information about libraries in Prague and its districts, outputting the results in both CSV and JSON formats.

## Features
- Fetches municipal library data from the Golemio API.
- Supports configuration of districts, coordinates, range, limits, and more via a config file.
- Outputs data in both CSV and JSON formats with Slovak field names.
- Supports scheduled extraction using a cron-like scheduler.
- Logs all operations to a log file for traceability.

## Requirements
- Python 3.13+
- Dependencies: see `requirements.txt` (mainly `requests`, `pytz`, `apscheduler`)

## Configuration
All settings are managed in `config.py`:
- `API_URL`, `API_KEY`: API endpoint and access token.
- `OUTPUT_DIR`: Directory for output files.
- `TIMEZONE`: Timezone for scheduling and timestamps.
- `DISTRICTS`, `LATLNG`, `RANGE`, `LIMIT`, `OFFSET`, `UPDATED_SINCE`: Parameters for API queries.
- `SCHEDULED_TIMES`: List of (hour, minute) tuples for scheduled runs.

## Usage
1. **Configure**: Edit `config.py` to set your desired parameters.
2. **Run**: Execute the extractor:
   ```bash
   python golemio_extractor.py
   ```
3. **Output**: Results are saved in `data/csv/` and `data/json/` with filenames like `libraries_YYYY-MM-DD_ALL.csv`.
4. **Logs**: See `golemio_extractor.log` for detailed logs.

## Scheduling
The extractor uses APScheduler to run automatically at times specified in `SCHEDULED_TIMES` (by default, daily at 07:00). You can add more times as needed.

## Custom Parameters
You can adjust the following in `config.py`:
- `DISTRICTS`: List of Prague districts to query (e.g., `['praha-1', 'praha-2']`).
- `LATLNG`: List of latitude/longitude strings for the search center.
- `RANGE`: List of search radii in meters.
- `LIMIT`: List of limits for the number of results.
- `OFFSET`: List of offsets for pagination.
- `UPDATED_SINCE`: List of ISO timestamps to filter updated records.

## Extending
- To add new output formats, extend the `save_data` function in `golemio_extractor.py`.
- To change the API endpoint or add new parameters, update `config.py` and the `fetch_data` function.

## License
This project is for educational and demonstration purposes. See the API provider's terms of use for data usage restrictions.

## Author
- [Oleksandr Shapran]

---
