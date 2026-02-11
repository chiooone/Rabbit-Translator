import asyncio
import json
import os
import threading
import time
import webbrowser
import subprocess
import shutil
import sys
import socket
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import urllib.request

from pythonosc import udp_client
import websockets

def open_app_window(url: str):
    """
    Open a lightweight app-like window using Edge/Chrome app mode.
    This keeps Web Speech API support while avoiding heavy embed dependencies.
    """
    edge = shutil.which("msedge")
    chrome = shutil.which("chrome")
    if not edge:
        candidates = [
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        ]
        for path in candidates:
            if os.path.exists(path):
                edge = path
                break
    if not chrome:
        candidates = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        ]
        for path in candidates:
            if os.path.exists(path):
                chrome = path
                break
    user_data = os.path.join(APP_DIR, "browser_profile")
    args = [
        f"--app={url}",
        f"--user-data-dir={user_data}",
        "--window-size=1100,640",
        "--disable-backgrounding-occluded-windows",
        "--disable-background-timer-throttling",
        "--disable-renderer-backgrounding",
        "--disable-features=CalculateNativeWinOcclusion",
    ]
    if edge:
        return subprocess.Popen([edge, *args])
    if chrome:
        return subprocess.Popen([chrome, *args])
    return None


def resolve_web_dir(app_dir: str) -> str:
    candidates = []
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.append(os.path.join(meipass, "web"))
    candidates.append(os.path.join(app_dir, "web"))
    candidates.append(os.path.join(app_dir, "_internal", "web"))
    for path in candidates:
        if os.path.isdir(path):
            return os.path.abspath(path)
    return candidates[0] if candidates else os.path.join(app_dir, "web")


if getattr(sys, "frozen", False):
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = resolve_web_dir(APP_DIR)
CONFIG_PATH = os.path.join(APP_DIR, "config.json")
LOG_PATH = os.path.join(APP_DIR, "app.log")


def log_line(message: str):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {message}\n")
    except Exception:
        pass

DEFAULT_CONFIG = {
    "osc_address": "127.0.0.1",
    "osc_port": 9000,
    "language": "zh-CN",
    "http_port": 8780,
    "ws_port": 8781,
    "auto_open_browser": True,
    "silence_stop_sec": 4.0,
    "final_hold_sec": 10.0,
    "voice_threshold": 0.02,
}


def load_config():
    if not os.path.exists(CONFIG_PATH):
        return DEFAULT_CONFIG.copy()
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        cfg = DEFAULT_CONFIG.copy()
        cfg.update({k: v for k, v in data.items() if k in cfg})
        return cfg
    except Exception:
        return DEFAULT_CONFIG.copy()


def save_config(cfg):
    data = DEFAULT_CONFIG.copy()
    data.update(cfg)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


class OscSender:
    def __init__(self, address: str, port: int):
        self.address = address
        self.port = port
        self.client = udp_client.SimpleUDPClient(self.address, self.port)

    def update(self, address: str, port: int):
        self.address = address
        self.port = port
        self.client = udp_client.SimpleUDPClient(self.address, self.port)

    def send_typing(self, active: bool = True):
        self.client.send_message("/chatbox/typing", bool(active))

    def send_message(self, text: str, notify: bool = True):
        # 3rd param controls notification SFX when sending immediately.
        self.client.send_message("/chatbox/input", [text, True, bool(notify)])


class RabbitTranslatorServer:
    def __init__(self, cfg):
        self.cfg = cfg
        self.osc = OscSender(cfg["osc_address"], int(cfg["osc_port"]))
        self.active_clients = 0
        self.had_client = False
        self.last_disconnect = None
        self._lock = threading.Lock()

    def register_client(self):
        with self._lock:
            self.active_clients += 1
            self.had_client = True

    def unregister_client(self):
        with self._lock:
            self.active_clients = max(0, self.active_clients - 1)
            self.last_disconnect = time.monotonic()

    def should_auto_close(self, idle_seconds: float = 2.0) -> bool:
        with self._lock:
            if not self.had_client:
                return False
            if self.active_clients > 0:
                return False
            if self.last_disconnect is None:
                return False
            return (time.monotonic() - self.last_disconnect) >= idle_seconds

    async def ws_handler(self, websocket):
        self.register_client()
        try:
            async for message in websocket:
                try:
                    payload = json.loads(message)
                except Exception:
                    continue

                msg_type = payload.get("type")
                if msg_type == "config":
                    address = payload.get("osc_address", self.cfg["osc_address"])
                    port = int(payload.get("osc_port", self.cfg["osc_port"]))
                    language = payload.get("language", self.cfg["language"])
                    silence_stop_sec = float(payload.get("silence_stop_sec", self.cfg["silence_stop_sec"]))
                    final_hold_sec = float(payload.get("final_hold_sec", self.cfg["final_hold_sec"]))
                    self.cfg.update(
                        {
                            "osc_address": address,
                            "osc_port": port,
                            "language": language,
                            "silence_stop_sec": silence_stop_sec,
                            "final_hold_sec": final_hold_sec,
                            "voice_threshold": float(
                                payload.get("voice_threshold", self.cfg["voice_threshold"])
                            ),
                        }
                    )
                    self.osc.update(address, port)
                    save_config(self.cfg)
                elif msg_type == "typing":
                    try:
                        value = payload.get("value", True)
                        self.osc.send_typing(bool(value))
                    except Exception:
                        pass
                elif msg_type == "partial":
                    text = (payload.get("text") or "").strip()
                    if text:
                        try:
                            self.osc.send_message(text, notify=False)
                        except Exception:
                            pass
                elif msg_type == "final":
                    raw = payload.get("text")
                    if raw is None:
                        continue
                    text = str(raw)
                    if text.strip() == "":
                        # Allow explicit clear without notification.
                        try:
                            self.osc.send_message("", notify=False)
                        except Exception:
                            pass
                        continue
                    try:
                        self.osc.send_message(text.strip(), notify=True)
                    except Exception:
                        pass
        finally:
            self.unregister_client()


class LoggingHTTPRequestHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        try:
            msg = format % args
        except Exception:
            msg = format
        log_line(f"HTTP: {msg}")

    def send_error(self, code, message=None, explain=None):
        log_line(f"HTTP error {code}: {message}")
        super().send_error(code, message, explain)

    def do_GET(self):
        log_line(f"HTTP GET {self.path}")
        try:
            super().do_GET()
        except Exception as exc:
            log_line(f"HTTP handler exception: {exc}")
            raise


def start_http_server(port: int):
    log_line(f"HTTP server start. WEB_DIR={WEB_DIR}, port={port}")
    if not os.path.isdir(WEB_DIR):
        log_line("WEB_DIR not found. HTTP server cannot start.")
        raise FileNotFoundError(f"WEB_DIR not found: {WEB_DIR}")
    try:
        handler = lambda *args, **kwargs: LoggingHTTPRequestHandler(*args, directory=WEB_DIR, **kwargs)
        httpd = ThreadingHTTPServer(("127.0.0.1", port), handler)
    except Exception as exc:
        log_line(f"Failed to bind HTTP server: {exc}")
        raise
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    log_line("HTTP server started.")
    return httpd


def wait_for_http(port: int, timeout: float = 3.0) -> bool:
    start = time.monotonic()
    while time.monotonic() - start < timeout:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                return True
        except OSError:
            time.sleep(0.1)
    log_line("HTTP server did not respond during wait_for_http.")
    return False


def self_test_http(url: str):
    try:
        with urllib.request.urlopen(url, timeout=2) as resp:
            log_line(f"Self-test HTTP status: {resp.status}")
    except Exception as exc:
        log_line(f"Self-test HTTP failed: {exc}")


async def ws_main(server: RabbitTranslatorServer, port: int, stop_event: threading.Event):
    async with websockets.serve(server.ws_handler, "127.0.0.1", port):
        while not stop_event.is_set():
            await asyncio.sleep(0.2)


def run_ws_server(server: RabbitTranslatorServer, port: int, stop_event: threading.Event):
    try:
        asyncio.run(ws_main(server, port, stop_event))
    except Exception as exc:
        log_line(f"WS server crashed: {exc}")


def main():
    log_line("App start.")
    cfg = load_config()
    log_line(f"Config loaded. http_port={cfg['http_port']}, ws_port={cfg['ws_port']}")
    httpd = start_http_server(int(cfg["http_port"]))
    server = RabbitTranslatorServer(cfg)

    stop_event = threading.Event()
    ws_thread = threading.Thread(
        target=run_ws_server, args=(server, int(cfg["ws_port"]), stop_event), daemon=True
    )
    ws_thread.start()

    url = (
        f"http://127.0.0.1:{cfg['http_port']}/index.html"
        f"?osc_address={cfg['osc_address']}"
        f"&osc_port={cfg['osc_port']}"
        f"&lang={cfg['language']}"
        f"&ws_port={cfg['ws_port']}"
        f"&silence_stop_sec={cfg['silence_stop_sec']}"
        f"&final_hold_sec={cfg['final_hold_sec']}"
        f"&voice_threshold={cfg['voice_threshold']}"
    )

    wait_for_http(int(cfg["http_port"]))
    self_test_http(url)
    proc = open_app_window(url)
    if proc is None:
        webbrowser.open(url)

    try:
        if server.should_auto_close():
            stop_event.set()
        while not stop_event.is_set():
            if server.should_auto_close():
                stop_event.set()
            time.sleep(0.2)
    except KeyboardInterrupt:
        pass
    finally:
        stop_event.set()
        httpd.shutdown()


if __name__ == "__main__":
    main()
