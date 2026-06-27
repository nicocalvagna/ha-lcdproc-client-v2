#!/usr/bin/env python3
import json, os, re, socket, sys, time
from typing import Any, Dict, List, Tuple
import requests

OPTIONS_FILE = "/data/options.json"

def log(*args):
    print(*args, flush=True)

def load_config():
    with open(OPTIONS_FILE, "r") as f:
        return json.load(f)

def clean(text):
    text = "" if text is None else str(text)
    text = text.replace("\n", " ").replace("\r", " ")
    text = text.replace("{", "(").replace("}", ")")
    text = text.replace("°", chr(223))
    return re.sub(r"\s+", " ", text).strip()

def fit_left(text, width):
    text = clean(text)
    return text[:width].ljust(width)

def fit_center(text, width):
    text = clean(text)
    if len(text) > width:
        return text[:width]
    return text.center(width)

def format_value(state, unit="", decimals=None):
    s = "" if state is None else str(state).strip()
    if s.lower() in ("unknown", "unavailable", "none", ""):
        return "sin dato"
    try:
        n = float(s)
        if decimals is None:
            decimals = 2
        s = f"{n:.{int(decimals)}f}".rstrip("0").rstrip(".")
    except Exception:
        pass
    unit = "" if unit is None else str(unit).strip()
    return f"{s} {unit}" if unit else s

def progress_bar(value_text, width):
    m = re.search(r"(-?\d+(?:\.\d+)?)", value_text)
    if not m:
        return None
    try:
        value = max(0, min(100, float(m.group(1))))
    except Exception:
        return None
    filled = round(value / 100 * width)
    return ("#" * filled + "-" * (width - filled))[:width]

class HA:
    def __init__(self):
        token = os.environ.get("SUPERVISOR_TOKEN", "")
        if not token:
            raise RuntimeError("SUPERVISOR_TOKEN not found")
        self.headers = {"Authorization": "Bearer " + token, "Content-Type": "application/json"}

    def get_entity(self, entity_id):
        url = "http://supervisor/core/api/states/" + entity_id
        try:
            r = requests.get(url, headers=self.headers, timeout=8)
        except Exception:
            return False, {}, "API exception"
        if r.status_code != 200:
            return False, {}, f"API {r.status_code}"
        try:
            return True, r.json(), ""
        except Exception:
            return False, {}, "JSON error"

class LCD:
    def __init__(self, host, port, width, debug=False):
        self.host, self.port, self.width, self.debug = host, port, width, debug
        self.sock = None

    def connect(self):
        self.close()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(10)
        self.sock.connect((self.host, self.port))
        self.raw("hello")
        hello = self.recv()
        log("LCDproc connected:", hello.strip())
        self.send("client_set name {HA_LCD_V2}")
        self.send("screen_add main")
        self.send("screen_set main name {HA LCD V2}")
        self.send("screen_set main heartbeat off")
        self.send("widget_add main title title")
        self.send("widget_add main line1 string")
        self.send("widget_add main line2 string")

    def close(self):
        try:
            if self.sock:
                self.sock.close()
        except Exception:
            pass
        self.sock = None

    def recv(self):
        try:
            return self.sock.recv(512).decode("utf-8", errors="replace")
        except Exception:
            return ""

    def raw(self, msg):
        if self.debug:
            log("LCD <<", msg)
        self.sock.sendall((msg + "\n").encode("utf-8"))

    def send(self, msg):
        self.raw(msg)
        old = self.sock.gettimeout()
        try:
            self.sock.settimeout(0.15)
            resp = self.recv().strip()
            if resp and self.debug:
                log("LCD >>", resp)
        except Exception:
            pass
        finally:
            try:
                self.sock.settimeout(old)
            except Exception:
                pass

    def display(self, line1, line2):
        l1 = fit_left(line1, self.width)
        l2 = fit_center(line2, self.width)
        self.send("widget_set main title {" + clean(l1) + "}")
        self.send("widget_set main line1 1 1 {" + clean(l1) + "}")
        self.send("widget_set main line2 1 2 {" + clean(l2) + "}")

def render(ha, screen, width):
    entity = str(screen.get("entity", "")).strip()
    title = str(screen.get("name") or entity).strip()
    ok, data, err = ha.get_entity(entity)
    if not ok:
        return title, err
    attrs = data.get("attributes", {}) or {}
    state = data.get("state", "")
    domain = entity.split(".", 1)[0] if "." in entity else ""
    if domain == "binary_sensor":
        value = "ON" if state == "on" else "OFF" if state == "off" else str(state)
    else:
        unit = screen.get("unit")
        if unit is None:
            unit = attrs.get("unit_of_measurement", "") or ""
        value = format_value(state, unit, screen.get("decimals"))
    if bool(screen.get("progressbar", False)):
        bar = progress_bar(value, width)
        if bar:
            return title, bar
    return title, value

def main():
    cfg = load_config()
    host = str(cfg.get("lcdproc_host", "")).strip()
    if not host:
        log("ERROR: lcdproc_host vacío")
        sys.exit(1)
    port = int(cfg.get("lcdproc_port", 13666))
    width = int(cfg.get("lcd_width", 16))
    rotation = max(1, int(cfg.get("rotation_seconds", 5)))
    refresh = max(1, int(cfg.get("refresh_seconds", 2)))
    debug = bool(cfg.get("debug", False))
    screens = [s for s in cfg.get("screens", []) if isinstance(s, dict) and s.get("entity")]

    ha = HA()
    lcd = LCD(host, port, width, debug)

    while True:
        try:
            lcd.connect()
            break
        except Exception as e:
            log("Cannot connect to LCDproc:", e)
            time.sleep(10)

    idx = -1
    last = 0
    while True:
        try:
            if not screens:
                lcd.display("Sin pantallas", "Config add-on")
                time.sleep(5)
                continue
            now = time.time()
            if idx < 0 or now - last >= rotation:
                idx = (idx + 1) % len(screens)
                last = now
            line1, line2 = render(ha, screens[idx], width)
            lcd.display(line1, line2)
            time.sleep(refresh)
        except (BrokenPipeError, ConnectionResetError, OSError) as e:
            log("LCDproc disconnected:", e)
            time.sleep(3)
            try:
                lcd.connect()
            except Exception as e2:
                log("Reconnect failed:", e2)
                time.sleep(10)
        except Exception as e:
            log("Runtime error:", e)
            try:
                lcd.display("Error", str(e))
            except Exception:
                pass
            time.sleep(5)

if __name__ == "__main__":
    main()
