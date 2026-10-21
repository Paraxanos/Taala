"""Taala — minimal local web page for password strength checking."""
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse

PORT = 8080
MAX_BODY = 4096
MAX_PWD = 72  # zxcvbn rejects longer input

HTML = """<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Taala — Password Strength Analyzer</title>
    <style>
        :root {
            --bg: #f8fafc; --card: #ffffff; --text: #0f172a; --muted: #64748b;
            --weak: #ef4444; --fair: #f59e0b; --strong: #10b981;
            --border: #e2e8f0; --accent: #2563eb;
        }
        body { font-family: system-ui, -apple-system, sans-serif; background: var(--bg); color: var(--text); margin: 0; padding: 2rem; display: flex; justify-content: center; }
        .container { max-width: 600px; width: 100%; }
        h1 { font-size: 1.5rem; margin-bottom: 0.5rem; }
        p.subtitle { color: var(--muted); margin-top: 0; margin-bottom: 2rem; }
        .input-group { display: flex; gap: 0.5rem; margin-bottom: 1.5rem; }
        input { flex: 1; padding: 0.75rem 1rem; font-size: 1rem; border: 1px solid var(--border); border-radius: 6px; outline: none; }
        input:focus { border-color: var(--accent); box-shadow: 0 0 0 3px rgba(37,99,235,0.1); }
        button { padding: 0.75rem 1.5rem; font-size: 1rem; font-weight: 600; background: var(--accent); color: white; border: none; border-radius: 6px; cursor: pointer; }
        button:hover { background: #1d4ed8; }
        
        .card { background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 1.5rem; margin-bottom: 1rem; box-shadow: 0 1px 3px rgba(0,0,0,0.05); display: none; }
        .card.active { display: block; }
        
        .band-badge { display: inline-block; padding: 0.25rem 0.75rem; border-radius: 99px; color: white; font-weight: 600; font-size: 0.875rem; text-transform: uppercase; }
        .band-weak { background: var(--weak); }
        .band-fair { background: var(--fair); }
        .band-strong { background: var(--strong); }
        
        .metric { display: flex; justify-content: space-between; padding: 0.5rem 0; border-bottom: 1px solid var(--border); }
        .metric:last-child { border-bottom: none; }
        .metric-label { color: var(--muted); }
        .metric-value { font-weight: 600; }
        
        .recipe-title { font-weight: 600; margin-bottom: 1rem; display: flex; align-items: center; gap: 0.5rem; }
        .recipe-step { display: flex; gap: 1rem; padding: 0.75rem 0; border-bottom: 1px dashed var(--border); }
        .recipe-step:last-child { border-bottom: none; }
        .step-num { background: var(--bg); border: 1px solid var(--border); width: 24px; height: 24px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 0.75rem; font-weight: 600; flex-shrink: 0; }
        .step-details { flex: 1; }
        .step-name { font-weight: 500; }
        .step-guesses { color: var(--muted); font-size: 0.875rem; }
        
        .fix-box { background: #eff6ff; border: 1px solid #bfdbfe; color: #1e40af; padding: 1rem; border-radius: 6px; font-size: 0.875rem; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Taala Password Analyzer</h1>
        <p class="subtitle">Spelling-independent strength estimation for Hinglish passwords.</p>
        
        <div class="input-group">
            <input type="password" id="password" placeholder="Enter a password (e.g., priyanka@1998)" autofocus>
            <button onclick="checkPassword()">Analyze</button>
        </div>
        
        <p id="error-msg" role="alert" style="display:none;color:var(--weak);margin:0 0 1rem"></p>

        <div id="results-card" class="card">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                <span style="font-weight: 600;">Strength Band</span>
                <span id="band-badge" class="band-badge"></span>
            </div>
            <div class="metric">
                <span class="metric-label">Estimated Guesses (log10)</span>
                <span id="guesses-log10" class="metric-value"></span>
            </div>
            <div class="metric">
                <span class="metric-label">Canonical Forms Found</span>
                <span id="forms-count" class="metric-value"></span>
            </div>
            <div class="metric">
                <span class="metric-label">Blocklist Hit</span>
                <span id="blocklist-hit" class="metric-value"></span>
            </div>
        </div>

        <div id="recipe-card" class="card">
            <div class="recipe-title">🛡️ Attack Recipe (How an attacker would guess this)</div>
            <div id="recipe-steps"></div>
        </div>

        <div id="fix-card" class="card fix-box">
            <strong>💡 Fix:</strong> Add <span id="words-to-add"></span> unrelated random words to reach the "Strong" band.
        </div>
    </div>

    <script>
        function showError(msg) {
            const el = document.getElementById('error-msg');
            el.textContent = `Could not analyze the password (${msg}).`;
            el.style.display = 'block';
        }

        async function checkPassword() {
            document.getElementById('error-msg').style.display = 'none';
            const pwd = document.getElementById('password').value;
            if (!pwd) return;
            
            try {
                const response = await fetch('/check', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({pwd: pwd}),
                });
                if (!response.ok) throw new Error(`HTTP ${response.status}`);
                const data = await response.json();
                
                // Results Card
                document.getElementById('results-card').classList.add('active');
                const badge = document.getElementById('band-badge');
                badge.textContent = data.band;
                badge.className = `band-badge band-${data.band.toLowerCase()}`;
                document.getElementById('guesses-log10').textContent = data.guesses_log10;
                document.getElementById('forms-count').textContent = data.forms.length;
                document.getElementById('blocklist-hit').textContent = data.blocklist_hit ? 'Yes (Weak)' : 'No';
                
                // Recipe Card
                document.getElementById('recipe-card').classList.add('active');
                const stepsContainer = document.getElementById('recipe-steps');
                stepsContainer.innerHTML = '';
                data.recipe.forEach((step, i) => {
                    const stepEl = document.createElement('div');
                    stepEl.className = 'recipe-step';
                    stepEl.innerHTML = `
                        <div class="step-num">${i + 1}</div>
                        <div class="step-details">
                            <div class="step-name">${step.step.replace(/_/g, ' ').replace(/\\b\\w/g, l => l.toUpperCase())}</div>
                            <div class="step-guesses">~10^${step.guesses_log10.toFixed(1)} guesses</div>
                        </div>
                    `;
                    stepsContainer.appendChild(stepEl);
                });
                
                // Fix Card
                document.getElementById('fix-card').classList.add('active');
                document.getElementById('words-to-add').textContent = data.words_to_add;
                
            } catch (e) { 
                showError(e.message);
            }
        }
        
        document.getElementById('password').addEventListener('keypress', function (e) {
            if (e.key === 'Enter') checkPassword();
        });
    </script>
</body>
</html>"""

class TaalaHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/":
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML.encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()
    def do_POST(self):
        # The password travels in the body, never in the URL (URLs reach logs and history).
        if urllib.parse.urlparse(self.path).path != "/check":
            self.send_response(404)
            self.end_headers()
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            if not 0 < length <= MAX_BODY:
                raise ValueError("bad length")
            pwd = json.loads(self.rfile.read(length).decode("utf-8")).get("pwd", "")
            if not isinstance(pwd, str) or not pwd or len(pwd) > MAX_PWD:
                raise ValueError("bad password")
        except (ValueError, UnicodeDecodeError):
            self.send_response(400)
            self.end_headers()
            return
        from taala.canon import analyze
        from taala.estimate import estimate
        analysis = analyze(pwd)
        est = estimate(pwd)
        response_data = {
            "band": est["band"], "forms": list(analysis["forms"]),
            "blocklist_hit": analysis["blocklist_hit"], "guesses_log10": est["guesses_log10"],
            "words_to_add": est["words_to_add"], "reasons": est["reasons"], "recipe": est["recipe"]
        }
        self.send_response(200)
        self.send_header("Content-type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(json.dumps(response_data).encode("utf-8"))

    def log_message(self, format, *args): pass

def main():
    server = HTTPServer(("127.0.0.1", PORT), TaalaHandler)
    from taala import pack
    if not pack.has_word_lists():
        print("Note: Hinglish word lists not found. Run: python tools/fetch_wordlists.py")
    print(f"Taala running at http://127.0.0.1:{PORT}/")
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()

if __name__ == "__main__":
    main()