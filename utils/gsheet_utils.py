import os
import gspread
from dotenv import load_dotenv
from oauth2client.service_account import ServiceAccountCredentials
from collections import defaultdict

_sheet_cache = {}
load_dotenv()
CREDS_PATH = os.getenv("GOOGLE_CREDS_PATH")
SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]
# Authenticate using the service account file
CREDS = ServiceAccountCredentials.from_json_keyfile_name(CREDS_PATH, SCOPE)
client = gspread.authorize(CREDS)

def _load_from_sheet(sheet_name, tab_name):
    try:
        sheet = client.open(sheet_name)
        return sheet.worksheet(tab_name)
    except gspread.exceptions.WorksheetNotFound:
        print(f"[ERROR] Worksheet '{tab_name}' not found in Google Sheet: {sheet_name}")
        return None
    except gspread.exceptions.SpreadsheetNotFound:
        print(f"[ERROR] Sheet '{sheet_name}' not found in Google Drive!")
        return None

def load_generic_table(sheet_name: str, tab_name: str, num_key_columns: int = 1, num_value_columns: int = None) -> dict:
    """Load a table from any sheet and tab dynamically."""
    # If it's already cached, return it.
    cache_key = f"{sheet_name}:{tab_name}"
    if cache_key in _sheet_cache and _sheet_cache[cache_key]:
        return _sheet_cache[cache_key]

    # If not cached, load from the sheet.
    worksheet = _load_from_sheet(sheet_name, tab_name)
    if not worksheet:
        return {}

    rows = worksheet.get_all_values()[1:]  # Skip the header row.
    result = defaultdict(list)

    for row in rows:
        if len(row) < num_key_columns:
            continue

        # Extract keys (multiple if needed)
        keys = tuple(cell.strip() for cell in row[:num_key_columns])
        # Extract values (after the key columns)
        values = [cell.strip() for cell in row[num_key_columns:] if cell.strip()]

        if num_value_columns is not None:
            values = values[:num_value_columns]

        # Store in the cache (multi-key or key-value)
        if len(keys) == 1:
            result[keys[0]].extend(values)  # Single key → multi-value
        else:
            result[keys] = values  # Multi-key → multi-value

    _sheet_cache[cache_key] = result  # Store in cache
    return result

def try_get_from_cache(sheet_name: str, tab_name: str, num_key_columns: int = 1, num_value_columns: int = None, force: bool = False):
    cache_key = f"{sheet_name}:{tab_name}"
    # Check if the cache is already populated
    if force or cache_key not in _sheet_cache or not _sheet_cache[cache_key]:
        # Load data if cache is empty or force refresh
        _sheet_cache[cache_key] = load_generic_table(sheet_name, tab_name, num_key_columns, num_value_columns)
    return _sheet_cache[cache_key]
