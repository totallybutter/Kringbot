import os
import random
from googleapiclient.discovery import build
from google.oauth2 import service_account
from dotenv import load_dotenv

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
SERVICE_ACCOUNT_JSON = os.environ.get("GOOGLE_CREDS_PATH")
if not SERVICE_ACCOUNT_JSON:
    raise RuntimeError("Missing GOOGLE_CREDS_PATH environment variable.")
credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_JSON, scopes=SCOPES)
drive_service = build('drive', 'v3', credentials=credentials)

# Caches
_folder_id_cache = {}      # folder_name → folder_id
_image_list_cache = {}     # folder_id → list of images

# --- Internal helpers ---
def _get_folder_id_by_name(folder_name: str):
    """Fetch and cache the folder ID from its name."""
    folder_name = folder_name.strip().lower()
    if folder_name in _folder_id_cache:
        return _folder_id_cache[folder_name]

    query = f"mimeType = 'application/vnd.google-apps.folder' and name = '{folder_name}' and trashed = false"
    results = drive_service.files().list(q=query, fields="files(id, name)").execute()
    folders = results.get('files', [])

    if folders:
        folder_id = folders[0]['id']
        _folder_id_cache[folder_name] = folder_id
        return folder_id
    return None

def _load_image_list_for_folder(folder_id: str):
    """List all images inside the given folder ID."""
    query = f"'{folder_id}' in parents and mimeType contains 'image/' and trashed = false"
    results = drive_service.files().list(
        q=query,
        fields="files(id, name)",
        pageSize=1000
    ).execute()

    return results.get("files", [])

def _get_images_in_folder(folder_name: str):
    """Return cached or freshly loaded list of images for a folder."""
    folder_id = _get_folder_id_by_name(folder_name)
    if not folder_id:
        return []

    if folder_id not in _image_list_cache:
        _image_list_cache[folder_id] = _load_image_list_for_folder(folder_id)

    return _image_list_cache[folder_id]

# --- Access API ---
def refresh_folder_cache(folder_name: str) -> bool:
    """Manually re-fetch image list for a folder by name."""
    folder_id = _get_folder_id_by_name(folder_name)
    if not folder_id:
        return False

    _image_list_cache[folder_id] = _load_image_list_for_folder(folder_id)
    return True

def get_random_image_url(folder_name: str):
    """Return a random image URL from the specified folder."""
    images = _get_images_in_folder(folder_name)
    if not images:
        return None

    chosen = random.choice(images)
    return f"https://drive.google.com/uc?id={chosen['id']}"

def get_named_image_url(folder_name: str, name: str):
    """Return an image that matches the given name (partial match, case-insensitive)."""
    images = _get_images_in_folder(folder_name)
    if not images:
        return None

    name = name.strip().lower()
    for img in images:
        if name in img['name'].lower():
            return f"https://drive.google.com/uc?id={img['id']}"
    return None