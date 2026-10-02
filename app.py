"""Local Grok router. One chat, one API key, a budget you set."""
import json, urllib.request, urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SETTINGS = ROOT / "settings.json"
USAGE = ROOT / "usage.json"
PORT = 8765

MODELS = [
    {"id": "grok-4-fast", "label": "Fast", "accuracy": 2, "speed": 5, "cost": 5, "note": "drafts, captions, short answers"},
    {"id": "grok-4", "label": "Mid", "accuracy": 4, "speed": 3, "cost": 3, "note": "normal work"},
    {"id": "grok-4.7", "label": "Strong", "accuracy": 5, "speed": 2, "cost": 1, "note": "legal, title, money, code"},
]

TASKS = {
    "chat":  {"need": 2, "name": "chat"},
    "write": {"need": 3, "name": "writing"},
    "code":  {"need": 4, "name": "code"},
    "legal": {"need": 5, "name": "legal / title / money"},
    "image": {"need": 4, "name": "image or animation"},
}

def load(path, default):
    if path.exists():
        return json.loads(path.read_text())
    return default

def save(path, data):
    path.write_text(json.dumps(data, indent=2))

def classify(text):
    t = text.lower()
    if any(w in t for w in ("title", "deed", "closing", "contract", "invoice", "escrow")):
        return "legal"
    if any(w in t for w in ("gif", "image", "banner", "animate", "picture")):
        return "image"
    if any(w in t for w in ("code", "python", "bug", "function", "repo")):
        return "code"
    if any(w in t for w in ("write", "post", "email", "caption", "linkedin")):
        return "write"
    return "chat"

def pick(text, accuracy, speed, cost):
    task = TASKS[classify(text)]
    w = (accuracy + speed + cost) or 1
    best, score = None, -1
    for m in MODELS:
        if m["accuracy"] + 1 < task["need"]:
            continue
        s = (m["accuracy"] * accuracy + m["speed"] * speed + m["cost"] * cost) / w
        if s > score:
            best, score = m, s
    if best is None:
        best = MODELS[-1]
        score = 0
    return task, best, round(score, 2)

def spent():
    return float(load(USAGE, {"spent": 0})["spent"])

def add_spend(amount):
    data = load(USAGE, {"spent": 0, "calls": 0})
    data["spent"] = round(float(data.get("spent", 0)) + amount, 6)
    data["calls"] = int(data.get("calls", 0)) + 1
    save(USAGE, data)
    return data

def call_xai(key, model, messages):
    body = json.dumps({"model": model, "messages": messages, "temperature": 0.4}).encode()
    req = urllib.request.Request(
        "https://api.x.ai/v1/chat/completions",
        data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as res:
        return json.loads(res.read().decode())

PAGE = """<!doctype html>
<html><head><meta charset=\"utf-8\"><title>Grok router</title>
<style>
body{font-family:Segoe UI,sans-serif;background:#0e1420;color:#e8eef8;margin:0}
main{max-width:820px;margin:0 auto;padding:24px}
h1{font-size:22px;margin:0 0 8px}
p{color:#a9b6c9;line-height:1.4}
label{display:block;margin:12px 0 4px}
input,textarea,button{width:100%;box-sizing:border-box;background:#172033;color:#fff;border:1px solid #2c3b55;border-radius:8px;padding:10px}
button{width:auto;background:#c9a227;color:#111;font-weight:700;cursor:pointer}
.row{display:flex;gap:12px} .row div{flex:1}
#log{white-space:pre-wrap;background:#101826;padding:12px;border-radius:8px;min-height:120px}
</style></head><body><main>
<h1>Grok router</h1>
<p>One window. It picks the model, counts what this app spends, and stops at your budget. It cannot see Grok chat, Grok bot, or Grok code.</p>
<label>xAI API key (saved only on this computer)</label>
<input id=\"key\" type=\"password\" placeholder=\"xai-...\">
<div class=\"row\">
<div><label>Budget USD</label><input id=\"budget\" type=\"number\" value=\"5\" step=\"1\"></div>
<div><label>Accuracy <span id=\"av\">70</span></label><input id=\"accuracy\" type=\"range\" min=\"0\" max=\"100\" value=\"70\"></div>
<div><label>Speed <span id=\"sv\">20</span></label><input id=\"speed\" type=\"range\" min=\"0\" max=\"100\" value=\"20\"></div>
<div><label>Cost <span id=\"cv\">10</span></label><input id=\"cost\" type=\"range\" min=\"0\" max=\"100\" value=\"10\"></div>
</div>
<label>Message</label>
<textarea id=\"msg\" rows=\"4\" placeholder=\"Ask one thing\"></textarea>
<p><button id=\"go\">Send through router</button></p>
<p id=\"stat\"></p>
<div id=\"log\"></div>
<script>
const $ = id => document.getElementById(id);
for (const [a,b] of [[\"accuracy\",\"av\"],[\"speed\",\"sv\"],[\"cost\",\"cv\"]])
  $(a).oninput = () => $(b).textContent = $(a).value;
async function refresh(){
  const s = await (await fetch(\"/api/state\")).json();
  $(\"stat\").textContent = \"Spent by this app $\" + s.spent.toFixed(4) + \" of $\" + s.budget + \" \u00b7 \" + s.calls + \" calls\";
  if (s.has_key) $(\"key\").placeholder = \"key saved\";
}
$(\"go\").onclick = async () => {
  $(\"log\").textContent = \"Routing...\";
  const res = await fetch(\"/api/chat\", {method:\"POST\", headers:{\"Content-Type\":\"application/json\"},
    body: JSON.stringify({key:$(\"key\").value, budget:Number($(\"budget\").value),
      accuracy:Number($(\"accuracy\").value), speed:Number($(\"speed\").value),
      cost:Number($(\"cost\").value), message:$(\"msg\").value})});
  const data = await res.json();
  $(\"log\").textContent = data.error ? data.error : (data.route + \"\\n\\n\" + data.answer);
  refresh();
};
refresh();
</script></main></body></html>"""

class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, kind="application/json"):
        raw = body if isinstance(body, bytes) else body.encode()
        self.send_response(code)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if self.path == "/api/state":
            s = load(SETTINGS, {})
            u = load(USAGE, {"spent": 0, "calls": 0})
            self._send(200, json.dumps({
                "spent": u.get("spent", 0), "calls": u.get("calls", 0),
                "budget": s.get("budget", 5), "has_key": bool(s.get("key")),
            }))
            return
        self._send(200, PAGE, "text/html; charset=utf-8")

    def do_POST(self):
        if self.path != "/api/chat":
            self._send(404, '{"error":"not found"}')
            return
        n = int(self.headers.get("Content-Length", 0))
        data = json.loads(self.rfile.read(n) or b"{}")
        settings = load(SETTINGS, {})
        if data.get("key"):
            settings["key"] = data["key"].strip()
        settings["budget"] = float(data.get("budget") or settings.get("budget") or 5)
        save(SETTINGS, settings)
        key = settings.get("key")
        if not key:
            self._send(400, json.dumps({"error": "Add an API key from console.x.ai"}))
            return
        if spent() >= settings["budget"]:
            self._send(200, json.dumps({"error": "Budget reached. This app will not call Grok until you raise the budget."}))
            return
        text = (data.get("message") or "").strip()
        if not text:
            self._send(400, json.dumps({"error": "Type a message"}))
            return
        task, model, score = pick(text, int(data.get("accuracy", 70)), int(data.get("speed", 20)), int(data.get("cost", 10)))
        try:
            result = call_xai(key, model["id"], [
                {"role": "system", "content": "Answer directly. Do not mention the router."},
                {"role": "user", "content": text},
            ])
        except urllib.error.HTTPError as e:
            self._send(200, json.dumps({"error": e.read().decode()[:800]}))
            return
        except Exception as e:
            self._send(200, json.dumps({"error": str(e)}))
            return
        usage = result.get("usage") or {}
        ticks = usage.get("cost_in_usd_ticks") or 0
        dollars = ticks / 1e10 if ticks else 0
        add_spend(dollars)
        answer = result["choices"][0]["message"]["content"]
        route = f"{task['name']} -> {model['label']} ({model['id']}) score {score} \u00b7 this call ${dollars:.6f}"
        self._send(200, json.dumps({"route": route, "answer": answer}))

    def log_message(self, *args):
        return

if __name__ == "__main__":
    print(f"Open http://127.0.0.1:{PORT}")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
