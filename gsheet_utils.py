import os
import gspread
from dotenv import load_dotenv
from oauth2client.service_account import ServiceAccountCredentials
from collections import defaultdict

_sheet_cache = {
    "categories": None,
    "responses": None,
    "specials": None,
    "role_ask_responses": None,
    "role_responses": None,
}

load_dotenv()
DATA_FOLDER = "data"
CREDS_PATH = os.getenv("GOOGLE_CREDS_PATH")
SHEET_NAME = os.getenv("SHEET_NAME", "Kringbot Data")
SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

# Authenticate using the service account file
CREDS = ServiceAccountCredentials.from_json_keyfile_name(CREDS_PATH, SCOPE)
client = gspread.authorize(CREDS)

sheet = client.open(SHEET_NAME)

def _load_from_sheet(sheet, name):
    try:
        return sheet.worksheet(name)
    except gspread.exceptions.WorksheetNotFound:
        print(f"[ERROR] Worksheet '{name}' not found in Google Sheet!")
        return None

def load_categories_from_sheet():
    worksheet = _load_from_sheet(sheet, "categories")
    if not worksheet:
        return {}
    rows = worksheet.get_all_values()[1:]
    category_keywords = defaultdict(list)
    for row in rows:
        if row:
            category = row[0].strip().lower()
            for keyword in row[1:]:
                if keyword.strip():
                    category_keywords[category].append(keyword.strip().lower())
    return category_keywords

def load_responses_from_sheet():
    worksheet = _load_from_sheet(sheet, "responses")
    if not worksheet:
        return {}
    rows = worksheet.get_all_values()[1:]
    responses = defaultdict(list)
    for row in rows:
        if row:
            category = row[0].strip().lower()
            for response in row[1:]:
                if response.strip():
                    responses[category].append(response.strip())
    return responses

def load_specials_from_sheet():
    worksheet = _load_from_sheet(sheet, "specials")
    if not worksheet:
        return {}
    rows = worksheet.get_all_values()[1:]
    return {row[0].strip().lower(): row[1].strip() for row in rows if len(row) >= 2}

def load_role_substring_responses():
    worksheet = _load_from_sheet(sheet, "role_ask_responses")
    if not worksheet:
        return {}
    rows = worksheet.get_all_values()[1:]  # skip header
    result = []

    for row in rows:
        if len(row) >= 3:
            role = row[0].strip()
            substr = row[1].strip().lower()
            responses = [cell.strip() for cell in row[2:] if cell.strip()]
            result.append((role, substr, responses))
    return result

def load_role_responses():
    worksheet = _load_from_sheet(sheet, "role_responses")
    if not worksheet:
        return {}
    rows = worksheet.get_all_values()
    headers = rows[0][1:]  # e.g. hello, status, ...
    data = {}

    for row in rows[1:]:
        role = row[0].strip()
        responses = {header: row[i + 1].strip() for i, header in enumerate(headers) if i + 1 < len(row) and row[i + 1].strip()}
        data[role] = responses
    return data

def get_response_for_role(role_names: list, header: str) -> str:
    role_response_map = try_get_from_cache("role_responses")
    for role in role_names:
        if role in role_response_map and header in role_response_map[role]:
            return role_response_map[role][header]
    return None



def load_keylist_from_sheet(key):
    if key == "categories":
        return load_categories_from_sheet()
    elif key == "responses":
        return load_responses_from_sheet()
    elif key == "specials":
        return load_specials_from_sheet()
    elif key == "role_ask_responses":
        return load_role_substring_responses()
    elif key == "role_responses":
        return load_role_responses()
    else:
        raise ValueError(f"Unknown sheet cache key: {key}")

def try_get_from_cache(key, force = False):
    if force or key not in _sheet_cache or not _sheet_cache[key]:
        _sheet_cache[key] = load_keylist_from_sheet(key)
    return _sheet_cache[key]
