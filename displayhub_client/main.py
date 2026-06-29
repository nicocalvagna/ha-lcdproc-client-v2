#!/usr/bin/env python3
import json, os, re, socket, sys, time
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
    text = text.replace("°", "C")
    return re.sub(r"\s+", " ", text).strip()

def fit_left(text, width):
    text = clean(text)
    return text[:width].ljust(width)

def fit_center(text, width):
    text = clean(text)
    if len(text) > width:
        return text[:width]
    return text.center(width)

def scroll_text(text, width, step):
    text = clean(text)
    if len(text) <= width:
        return text.ljust(width)
    padded = text + "   "
    doubled = padded + padded
    pos = step % len(padded)
    return doubled[pos:pos + width]

def extract_number(value_text):
    m = re.search(r"(-?\d+(?:\.\d+)?)", str(value_text))
    if not m:
        return None
    try:
        return float(m.group(1))
    except Exception:
        return None

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

def scaled_percent(value_text, bar_min=0, bar_max=100):
    value = extract_number(value_text)
    if value is None:
        return None
    try:
        bar_min = float(bar_min)
        bar_max = float(bar_max)
    except Exception:
        bar_min = 0
        bar_max = 100
    if bar_max == bar_min:
        return None
    pct = (value - bar_min) / (bar_max - bar_min) * 100
    return max(0, min(100, pct))

def progress_bar(value_text, width, style="bar", bar_min=0, bar_max=100):
    pct = scaled_percent(value_text, bar_min, bar_max)
    if pct is None:
        return None

    style = str(style or "bar").lower()

    if style == "percent":
        prefix = f"{int(round(pct))}% "
        bar_width = max(0, width - len(prefix))
        filled = round(pct / 100 * bar_width)
        return (prefix + "#" * filled + "-" * (bar_width - filled))[:width]

    if style == "needle":
        pos = round(pct / 100 * (width - 1))
        chars = ["-"] * width
        chars[pos] = "|"
        return "".join(chars)

    filled = round(pct / 100 * width)
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

class DisplayHub:
    def __init__(self, host, port, debug=False):
        self.host = host
        self.port = int(port)
        self.debug = debug

    def send_lines(self, target, lines):
        payload = {
            "cmd": "display",
            "target": target,
            "lines": lines,
        }

        msg = json.dumps(payload) + "\n"

        if self.debug:
            log("DisplayHub <<", msg.strip())

        try:
            with socket.create_connection((self.host, self.port), timeout=5) as sock:
                sock.sendall(msg.encode("utf-8"))
                response = sock.recv(1024).decode("utf-8", errors="replace").strip()
        except Exception as exc:
            log("DisplayHub error:", exc)
            return False

        if self.debug:
            log("DisplayHub >>", response)

        try:
            data = json.loads(response)
            return data.get("status") == "ok"
        except Exception:
            return False

def render(ha, screen, width, scroll_step):
    entity = str(screen.get("entity", "")).strip()
    title = str(screen.get("name") or entity).strip()

    if bool(screen.get("scroll", False)):
        title = scroll_text(title, width, scroll_step)

    ok, data, err = ha.get_entity(entity)
    if not ok:
        return fit_left(title, width), fit_center(err, width)

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
        bar = progress_bar(
            value,
            width,
            screen.get("bar_style", "bar"),
            screen.get("bar_min", 0),
            screen.get("bar_max", 100),
        )
        if bar:
            value = bar

    return fit_left(title, width), fit_center(value, width)

def main():
    cfg = load_config()

    host = str(cfg.get("displayhub_host", "")).strip()
    port = int(cfg.get("displayhub_port", 4510))
    width = int(cfg.get("lcd_width", 16))
    rotation = max(1, int(cfg.get("rotation_seconds", 5)))
    refresh = max(1, int(cfg.get("refresh_seconds", 1)))
    debug = bool(cfg.get("debug", False))

    screens = [s for s in cfg.get("screens", []) if isinstance(s, dict) and s.get("entity") and s.get("display")]

    if not host:
        log("ERROR: displayhub_host vacío")
        sys.exit(1)

    ha = HA()
    hub = DisplayHub(host, port, debug)

    if not screens:
        log("No screens configured")
        while True:
            time.sleep(10)

    index_by_display = {}
    last_rotation_by_display = {}
    scroll_step_by_display = {}

    displays = sorted(set(str(s["display"]) for s in screens))

    for display in displays:
        index_by_display[display] = 0
        last_rotation_by_display[display] = 0
        scroll_step_by_display[display] = 0

    log("Display Hub Client running")
    log("Display Hub:", host, port)
    log("Displays:", displays)

    while True:
        now = time.time()

        for display in displays:
            display_screens = [s for s in screens if str(s.get("display")) == display]

            if not display_screens:
                continue

            if now - last_rotation_by_display[display] >= rotation:
                index_by_display[display] = (index_by_display[display] + 1) % len(display_screens)
                last_rotation_by_display[display] = now
                scroll_step_by_display[display] = 0

            screen = display_screens[index_by_display[display]]
            line1, line2 = render(ha, screen, width, scroll_step_by_display[display])

            hub.send_lines(display, [line1, line2])
            scroll_step_by_display[display] += 1

        time.sleep(refresh)

if __name__ == "__main__":
    main()
