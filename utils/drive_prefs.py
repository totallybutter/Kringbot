import os
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
import io
from googleapiclient.discovery import build
from google.oauth2 import service_account
from dotenv import load_dotenv

SCOPES = [
    "https://www.googleapis.com/auth/drive",  # Full access
    "https://www.googleapis.com/auth/drive.metadata.readonly",
    "https://www.googleapis.com/auth/drive.file"
]
SERVICE_ACCOUNT_JSON = os.environ.get("GOOGLE_CREDS_PATH")
if not SERVICE_ACCOUNT_JSON:
    raise RuntimeError("Missing GOOGLE_CREDS_PATH for Drive service.")

credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_JSON, scopes=SCOPES
)
drive_service = build('drive', 'v3', credentials=credentials)

PREFS_FILENAME = "kringbot_prefs.json"

def _get_folder_id_by_name(folder_name: str):
    query = f"mimeType = 'application/vnd.google-apps.folder' and name = '{folder_name}' and trashed = false"
    results = drive_service.files().list(q=query, fields="files(id, name)").execute()
    folders = results.get("files", [])
    if folders:
        return folders[0]['id']
    return None

FOLDER_ID = _get_folder_id_by_name(os.environ.get("BOT_PREFS_FOLDER_ID"))

def upload_to_drive(local_path=PREFS_FILENAME):
    if not FOLDER_ID:
        raise RuntimeError("Missing BOT_PREFS_FOLDER_ID in .env")

    # Delete any old copy with same name
    query = f"'{FOLDER_ID}' in parents and name = '{PREFS_FILENAME}' and trashed = false"
    existing = drive_service.files().list(q=query, fields="files(id)").execute().get("files", [])
    for file in existing:
        drive_service.files().delete(fileId=file["id"]).execute()

    # Upload fresh file
    media = MediaFileUpload(local_path, mimetype='application/json')
    metadata = {'name': PREFS_FILENAME, 'parents': [FOLDER_ID]}
    drive_service.files().create(body=metadata, media_body=media).execute()
    print(f"[DrivePrefs] ✅ Uploaded {PREFS_FILENAME} to Drive.")

def download_from_drive(local_path=PREFS_FILENAME):
    if not FOLDER_ID:
        raise RuntimeError("Missing BOT_PREFS_FOLDER_ID in .env")

    query = f"'{FOLDER_ID}' in parents and name = '{PREFS_FILENAME}' and trashed = false"
    results = drive_service.files().list(q=query, fields="files(id)").execute()
    files = results.get("files", [])
    if not files:
        print("[DrivePrefs] ⚠️ No prefs file found on Drive.")
        return False

    file_id = files[0]['id']
    request = drive_service.files().get_media(fileId=file_id)
    fh = io.FileIO(local_path, 'wb')
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()

    print(f"[DrivePrefs] ✅ Downloaded {PREFS_FILENAME} from Drive.")
    return True
