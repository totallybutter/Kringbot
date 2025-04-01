import os
import gspread
from dotenv import load_dotenv
from oauth2client.service_account import ServiceAccountCredentials
from collections import defaultdict

_sheet_cache = {
    "categories": None,
    "responses": None,
    "specials": None
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

def load_from_sheet(sheet, name):
    try:
        return sheet.worksheet(name)
    except gspread.exceptions.WorksheetNotFound:
        print(f"[ERROR] Worksheet '{name}' not found in Google Sheet!")
        return None

def load_categories_from_sheet():
    worksheet = load_from_sheet(sheet, "categories")
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
    worksheet = load_from_sheet(sheet, "responses")
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
    worksheet = load_from_sheet(sheet, "specials")
    if not worksheet:
        return {}
    rows = worksheet.get_all_values()[1:]
    return {row[0].strip().lower(): row[1].strip() for row in rows if len(row) >= 2}

def load_sheet_cache():
    print("loaded sheet cache")
    _sheet_cache["categories"] = load_categories_from_sheet()
    _sheet_cache["responses"] = load_responses_from_sheet()
    _sheet_cache["specials"] = load_specials_from_sheet()