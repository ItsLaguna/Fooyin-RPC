import time
import requests
import os
import urllib.parse
import threading
from flask import Flask, request, abort
from pypresence import Presence
from pypresence.types import ActivityType
from pypresence.types import StatusDisplayType
from pydbus import SessionBus


# =======================
# CONFIG
# =======================
CLIENT_ID = "1420704039737233508" # If you don't want to use this one, change with one created via Discord's Developert Portal
LARGE_IMAGE = "fooyin_logo"
LARGE_TEXT = "fooyin"

# --- Folder Settings ---
USE_CUSTOM_PATH = True  # Set to True to use SPECIFIC_PATH
SPECIFIC_PATH = "/var/www/fooyinart/"

if USE_CUSTOM_PATH:
    UPLOAD_FOLDER = SPECIFIC_PATH
else:
    # Uses the directory where the script is currently located
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fooyinart")

# Ensure the folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

FILENAME = "_current_artwork" # Can change if you want, will be the name of the file for the art
PUBLIC_ART_URL = f"hostname" # Replace hostname with your actual hostname, even if its called "PUBLIC_ART_URL" it can be a local one
SECRET_TOKEN = "tokengoeshere" # This was a suggestion from Gemini/GPT, set it to whatever you want.

POLL_INTERVAL = 0.5  # seconds
SEEK_THRESHOLD = 5   # seconds: detect large seeks
LOOP_POS_THRESHOLD = 2  # seconds: consider a loop if position < 2s


# =======================
# BACKGROUND SERVER
# =======================
app = Flask(__name__)

@app.route('/upload', methods=['POST'])
def upload_endpoint():
    if request.form.get('token') != SECRET_TOKEN:
        abort(403)
    file = request.files.get('file')
    if file:
        file.save(os.path.join(UPLOAD_FOLDER, FILENAME))
        return "OK", 200
    return "No file", 400

def run_flask():
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)  # Keep console clean
    app.run(host='127.0.0.1', port=7000, debug=False, use_reloader=False)


# =======================
# HELPERS
# =======================
def safe_get(metadata, key, default=''):
    val = metadata.get(key)
    if val is None:
        return default
    if isinstance(val, (list, tuple)) and val:
        return str(val[0])
    return str(val)

def upload_art(mpris_url):
    """Processes embedded art path and uploads to the internal Flask thread."""
    if not mpris_url:
        return None
    # Use unquote to handle embedded art extracted to temp paths with spaces
    path = urllib.parse.unquote(mpris_url).replace("file://", "")
    if not os.path.exists(path):
        return None
    try:
        with open(path, 'rb') as f:
            requests.post("http://127.0.0.1:7000/upload",
                          files={'file': f},
                          data={'token': SECRET_TOKEN},
                          timeout=1)
        # Cache buster is required because the filename never changes
        return f"{PUBLIC_ART_URL}?t={int(time.time())}"
    except:
        return None

def build_presence(metadata, start_time=None, end_time=None, current_art=None):
    artist = safe_get(metadata, 'xesam:artist', '')
    title = safe_get(metadata, 'xesam:title', '')
    album = safe_get(metadata, 'xesam:album', '')

    details = title or "Unknown track"
    state = (artist)

    payload = {"details": details, "state": state or None}

    # include start/end only if meaningful
    if start_time is not None and end_time is not None and end_time > start_time:
        payload["start"] = int(start_time)
        payload["end"] = int(end_time)

    # Use uploaded URL if available, else fallback
    payload["large_image"] = current_art if current_art else LARGE_IMAGE
    payload["large_text"] = album or LARGE_TEXT

    return payload


# =======================
# MAIN
# =======================
def run_presence():
    # Start the integrated server thread
    threading.Thread(target=run_flask, daemon=True).start()

    try:
        rpc = Presence(CLIENT_ID)
        rpc.connect()
    except Exception as e:
        return

    bus = SessionBus()
    player = None
    last_key = None
    last_art_path = None
    current_art_url = None
    initial_start_time = None
    pause_offset = 0
    paused_at = None
    last_status = None
    last_pos = 0

    while True:
        try:
            # ensure player connection
            if player is None:
                try:
                    player = bus.get("org.mpris.MediaPlayer2.fooyin", "/org/mpris/MediaPlayer2")
                except Exception:
                    time.sleep(1.0)
                    continue

            metadata = dict(player.Metadata)
            status = getattr(player, "PlaybackStatus", "Stopped")
            pos_s = getattr(player, "Position", 0) // 1_000_000
            length_s = metadata.get("mpris:length", 0) // 1_000_000

            key = (
                safe_get(metadata, "xesam:title", ""),
                safe_get(metadata, "xesam:artist", ""),
                safe_get(metadata, "xesam:album", "")
            )

            # Treat Paused same as Stopped
            if status in ("Stopped", "Paused"):
                if last_status not in ("Stopped", "Paused"):
                    try:
                        rpc.clear()
                    except Exception:
                        pass
                initial_start_time = None
                pause_offset = 0
                paused_at = None
                last_key = None
                last_pos = 0
                last_art_path = None # Reset art tracking on stop
                last_status = status
                time.sleep(POLL_INTERVAL)
                continue

            # Track change -> reset timings and handle art upload
            if last_key != key:
                if status == "Playing" and length_s > 0:
                    initial_start_time = time.time() - pos_s
                    pause_offset = 0
                    paused_at = None
                else:
                    initial_start_time = None
                    pause_offset = 0
                    paused_at = None
                last_key = key
                last_pos = pos_s

                # Trigger Art Upload for new track
                mpris_art = safe_get(metadata, 'mpris:artUrl', '')
                if mpris_art != last_art_path:
                    new_url = upload_art(mpris_art)
                    if new_url:
                        current_art_url = new_url
                    last_art_path = mpris_art
            else:
                # Detect loop or large seek
                if status == "Playing" and length_s > 0 and initial_start_time is not None:
                    expected_pos = time.time() - initial_start_time - pause_offset
                    if (pos_s < LOOP_POS_THRESHOLD and pos_s < last_pos - 1) or abs(pos_s - expected_pos) > SEEK_THRESHOLD:
                        initial_start_time = time.time() - pos_s
                        pause_offset = 0
                        paused_at = None

            if status == "Playing" and length_s > 0 and initial_start_time is not None:
                if paused_at is not None:
                    pause_offset += time.time() - paused_at
                    paused_at = None
                end_time = initial_start_time + pause_offset + length_s
            else:
                end_time = None

            rpc_start_time = None
            if initial_start_time is not None:
                rpc_start_time = initial_start_time + pause_offset

            # Build payload with current_art_url integrated
            payload = build_presence(metadata, rpc_start_time, end_time, current_art_url)

            # Update Discord
            try:
                rpc.update(**{k: v for k, v in payload.items() if v is not None}, activity_type=ActivityType.LISTENING, name="fooyin")
            except Exception:
                try:
                    rpc.close()
                except Exception:
                    pass
                try:
                    rpc = Presence(CLIENT_ID)
                    rpc.connect()
                    rpc.update(**{k: v for k, v in payload.items() if v is not None}, activity_type=ActivityType.LISTENING, name="fooyin")
                except Exception:
                    pass

            last_status = status
            last_pos = pos_s

        except Exception:
            try:
                rpc.clear()
            except Exception:
                pass
            player = None
            last_status = "Offline"
            last_key = None
            last_art_path = None
            initial_start_time = None
            pause_offset = 0
            paused_at = None
            last_pos = 0
            time.sleep(1.0)

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    run_presence()
