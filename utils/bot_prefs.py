import json
import time
import os

# Internal store
_store = {}

### Singleton API ###
def set(key, value, time_based=False):
    _store[key] = {
        "value": value,
        "time_based": time_based,
        "saved_at": time.time() if time_based else None
    }

def get(key, default=None):
    entry = _store.get(key)
    if not entry:
        return default

    value = entry["value"]
    if entry.get("time_based"):
        saved_at = entry.get("saved_at", time.time())
        elapsed = time.time() - saved_at
        adjusted = max(0, value - elapsed)
        return adjusted
    return value

def has(key):
    return key in _store

def delete(key):
    _store.pop(key, None)

def all_keys():
    return list(_store.keys())


### Persistence API ###
def save(filepath):
    """Save to a JSON file."""
    try:
        with open(filepath, "w") as f:
            json.dump(_store, f, indent=2)
        print(f"[BotPrefs] ✅ Saved state to {filepath}")
    except Exception as e:
        print(f"[BotPrefs] ❌ Failed to save: {e}")

def load(filepath):
    """Load from a JSON file, adjusting time-based values."""
    if not os.path.exists(filepath):
        print(f"[BotPrefs] ⚠️ No existing file at {filepath}, starting fresh.")
        return

    global _store
    try:
        with open(filepath, "r") as f:
            raw = json.load(f)

        now = time.time()
        _store = {}
        for key, entry in raw.items():
            time_based = entry.get("time_based", False)
            saved_at = entry.get("saved_at", now)
            value = entry.get("value")

            # Adjust time-based values
            if time_based:
                elapsed = now - saved_at
                adjusted = max(0, value - elapsed)
                _store[key] = {
                    "value": adjusted,
                    "time_based": True,
                    "saved_at": now  # reset clock
                }
            else:
                _store[key] = entry

        print(f"[BotPrefs] ✅ Loaded state from {filepath}")
    except Exception as e:
        print(f"[BotPrefs] ❌ Failed to load: {e}")