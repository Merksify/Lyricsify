import asyncio, os, sys, threading
from datetime import datetime, timezone
import requests
import webview

try:
    from winsdk.windows.media.control import (
        GlobalSystemMediaTransportControlsSessionManager as Manager,
    )
except ImportError:
    Manager = None

BASE = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
CFG_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "SpotifyLyrics")
CSS_FILE = os.path.join(CFG_DIR, "custom.css")
os.makedirs(CFG_DIR, exist_ok=True)

state = {"playing": False, "title": "", "artist": "", "pos_ms": 0,
         "synced": "", "plain": "", "error": ""}
current_key = None


def fetch_lyrics(key, artist, title, dur_ms):
    """Look up lyrics on lrclib.net (free, no key) and store them if the song is still current."""
    headers = {"User-Agent": "SpotifyLyricsWidget/1.0"}
    synced, plain = "", "No lyrics found."
    try:
        r = requests.get("https://lrclib.net/api/get", headers=headers, timeout=8,
                         params={"artist_name": artist, "track_name": title,
                                 "duration": int(dur_ms / 1000)})
        if not r.ok:
            r = requests.get("https://lrclib.net/api/search", headers=headers, timeout=8,
                             params={"q": f"{artist} {title}"})
            data = r.json()[0] if r.ok and r.json() else None
        else:
            data = r.json()
        if data:
            synced = data.get("syncedLyrics") or ""
            plain = data.get("plainLyrics") or plain
    except Exception as e:
        print("lyrics error:", e)
    if key == current_key:
        state["synced"], state["plain"] = synced, plain


async def poll():
    global current_key
    mgr = await Manager.request_async()
    while True:
        try:
            session = next((s for s in mgr.get_sessions()
                            if "spotify" in s.source_app_user_model_id.lower()), None)
            if session is None:
                state["playing"] = False
            else:
                props = await session.try_get_media_properties_async()
                tl = session.get_timeline_properties()
                playing = int(session.get_playback_info().playback_status) == 4
                dur = (tl.end_time - tl.start_time).total_seconds() * 1000
                pos = tl.position.total_seconds() * 1000
                if playing:
                    updated = tl.last_updated_time
                    if updated.tzinfo is None:
                        updated = updated.replace(tzinfo=timezone.utc)
                    pos += max(0, (datetime.now(timezone.utc) - updated).total_seconds() * 1000)
                state.update(playing=playing, title=props.title, artist=props.artist,
                             pos_ms=min(pos, dur) if dur else pos)
                key = (props.title, props.artist)
                if key != current_key:
                    current_key = key
                    state["synced"], state["plain"] = "", ""
                    threading.Thread(target=fetch_lyrics,
                                     args=(key, props.artist, props.title, dur),
                                     daemon=True).start()
        except Exception as e:
            print("poll error:", e)
        await asyncio.sleep(0.25)


class Api:
    def status(self):
        return state

    def get_css(self):
        return open(CSS_FILE, encoding="utf-8").read() if os.path.exists(CSS_FILE) else ""

    def save_css(self, css):
        with open(CSS_FILE, "w", encoding="utf-8") as f:
            f.write(css)


if __name__ == "__main__":
    if Manager is None:
        state["error"] = "Windows only: install winsdk (pip install winsdk)."
    else:
        threading.Thread(target=lambda: asyncio.run(poll()), daemon=True).start()
    webview.create_window("Lyrics", os.path.join(BASE, "index.html"), js_api=Api(),
                          width=460, height=680, background_color="#14121a")
    webview.start()
