import time
from pypresence import Presence
from pydbus import SessionBus

# CONFIG

CLIENT_ID = "1420704039737233508"
LARGE_IMAGE = "fooyin_logo"
LARGE_TEXT = "fooyin"

POLL_INTERVAL = 0.2  # seconds
SEEK_THRESHOLD = 5   # seconds: detect large seeks
LOOP_POS_THRESHOLD = 2  # seconds: consider a loop if position < 2s

# HELPERS

def safe_get(metadata, key, default=''):
    val = metadata.get(key)
    if val is None:
        return default
    if isinstance(val, (list, tuple)) and val:
        return str(val[0])
    return str(val)

def build_presence(metadata, start_time=None, end_time=None):
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

    payload["large_image"] = LARGE_IMAGE
    payload["large_text"] = LARGE_TEXT

    return payload

# MAIN

def run_presence():
    try:
        rpc = Presence(CLIENT_ID)
        rpc.connect()
    except Exception as e:
        # can't connect to Discord RPC — nothing to do
        return

    bus = SessionBus()
    player = None
    last_key = None
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
                    # not running yet
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

            # Treat Paused same as Stopped -> clear presence and reset tracking
            if status in ("Stopped", "Paused"):
                if last_status not in ("Stopped", "Paused"):
                    try:
                        rpc.clear()
                    except Exception:
                        pass
                # reset per-track state so resume is handled as a fresh start
                initial_start_time = None
                pause_offset = 0
                paused_at = None
                last_key = None
                last_pos = 0
                last_status = status
                time.sleep(POLL_INTERVAL)
                continue

            # Track change -> reset timings
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
            else:
                # Detect loop or large seek
                if status == "Playing" and length_s > 0 and initial_start_time is not None:
                    expected_pos = time.time() - initial_start_time - pause_offset
                    if (pos_s < LOOP_POS_THRESHOLD and pos_s < last_pos - 1) or abs(pos_s - expected_pos) > SEEK_THRESHOLD:
                        # Track looped or large seek
                        initial_start_time = time.time() - pos_s
                        pause_offset = 0
                        paused_at = None

            # Pause/resume handling (since pause is treated as stop above, only Playing arrives here)
            if status == "Playing" and length_s > 0 and initial_start_time is not None:
                # If paused_at had been set earlier (shouldn't happen with pause-as-stop), adjust
                if paused_at is not None:
                    pause_offset += time.time() - paused_at
                    paused_at = None
                end_time = initial_start_time + pause_offset + length_s
            else:
                end_time = None

            # Calculate Discord start time including pause offset
            rpc_start_time = None
            if initial_start_time is not None:
                rpc_start_time = initial_start_time + pause_offset

            payload = build_presence(metadata, rpc_start_time, end_time)

            # Update Discord (we update on every loop to stay smooth during seeks; RPC rate is low)
            try:
                rpc.update(**{k: v for k, v in payload.items() if v is not None}, activity_type=ActivityType.LISTENING, name="fooyin")
            except Exception:
                # try reconnecting to RPC once
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
            # Lost player or D-Bus error -> clear presence and attempt reconnect later
            try:
                rpc.clear()
            except Exception:
                pass
            player = None
            last_status = "Offline"
            last_key = None
            initial_start_time = None
            pause_offset = 0
            paused_at = None
            last_pos = 0
            time.sleep(1.0)

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    run_presence()
