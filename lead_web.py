"""Serve the leadEngine dashboard on the local network."""
import argparse
import base64
import csv
from functools import partial
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import StringIO
from ipaddress import ip_address, ip_network
import json
from pathlib import Path
import secrets
import subprocess
from threading import Lock
from urllib.parse import urlsplit

from lead_engine import blocked, campaigns, closing, database, domain, load_rows
from lead_discovery import find_leads
from lead_coohom import PRESET

ROOT = Path(__file__).resolve().parent
STATE = ROOT / "state"
WEB = STATE / "web"
DB = STATE / "leadengine.sqlite"
LOG = WEB / "run.log"
STATUS = WEB / "status.json"
CAMPAIGN = WEB / "campaign.json"
LEADS = WEB / "leads.csv"
EXPORT = STATE / "review.csv"
MAX_BODY = 1_048_576
LOCK = Lock()
DISCOVERY_LOCK = Lock()
PROCESS = None


def save_status(status):
    pending = STATUS.with_suffix(".tmp")
    pending.write_text(json.dumps(status), encoding="utf-8")
    pending.replace(STATUS)


def status():
    global PROCESS
    with LOCK:
        if PROCESS is not None:
            code = PROCESS.poll()
            if code is not None:
                previous = json.loads(STATUS.read_text(encoding="utf-8"))
                save_status({**previous, "phase": "complete" if code == 0 else "failed"})
                PROCESS = None
        if not STATUS.exists():
            return {"phase": "idle"}
        current = json.loads(STATUS.read_text(encoding="utf-8"))
        if current["phase"] == "running" and PROCESS is None:
            return {"phase": "interrupted"}
        return current


def launch(kind):
    global PROCESS
    args = [str(ROOT / "bin/leadengine"), "run", str(LEADS), "--campaign", str(CAMPAIGN),
            "--verify-only" if kind == "verify" else "--qualify-only"]
    with LOG.open("wb") as stream:
        PROCESS = subprocess.Popen(args, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT)
    save_status({"phase": "running", "kind": kind})


def start_verification():
    current = status()
    with LOCK:
        if PROCESS is not None:
            raise ValueError("A run is already in progress.")
        if current["phase"] not in ("complete", "failed", "interrupted") or not LEADS.exists():
            raise ValueError("Qualify selected businesses before verifying.")
        launch("verify")


def start_run(data):
    config = data["campaign"]
    values = data["csv"]
    if not isinstance(config, dict) or not isinstance(values, str):
        raise ValueError("Provide a campaign and a lead CSV.")
    with LOCK:
        if PROCESS is not None and PROCESS.poll() is None:
            raise ValueError("A run is already in progress.")
        candidate_campaign = CAMPAIGN.with_suffix(".pending")
        candidate_leads = LEADS.with_suffix(".pending")
        candidate_campaign.write_text(json.dumps(config, indent=2), encoding="utf-8")
        candidate_leads.write_text(values, encoding="utf-8")
        try:
            campaigns(candidate_campaign)
            count, _ = load_rows(candidate_leads)
            if not count:
                raise ValueError("Add at least one business to the CSV.")
            candidate_campaign.replace(CAMPAIGN)
            candidate_leads.replace(LEADS)
        finally:
            candidate_campaign.unlink(missing_ok=True)
            candidate_leads.unlink(missing_ok=True)
        launch("qualify")


def run_details():
    current = status()
    if not LOG.exists():
        return current
    results = {}
    summary = {}
    with LOG.open(encoding="utf-8", errors="replace") as stream:
        for line in stream:
            if not line.startswith("{"):
                continue
            try:
                item = json.loads(line)
            except ValueError:
                continue
            if "domain" in item:
                results.setdefault(item["domain"], {}).update(item)
            elif "input" in item:
                summary = item
    if current.get("kind") == "qualify" and current["phase"] == "complete":
        failed = summary.get("crawl_failures", 0)
        processed = summary.get("qualified", 0) + summary.get("review", 0) + summary.get("out_of_scope", 0)
        if failed:
            current["phase"] = "crawl failed" if failed == processed else "completed with crawl failures"
    return {**current, "results": list(results.values()), "summary": summary}


def review_csv():
    with EXPORT.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        output = StringIO(newline="")
        writer = csv.DictWriter(output, reader.fieldnames)
        writer.writeheader()
        with closing(database(DB)) as db:
            for row in reader:
                if not blocked(db, row["email"].removeprefix("'"), domain(row["website_url"])):
                    writer.writerow(row)
    return output.getvalue().encode("utf-8-sig")


class Dashboard(BaseHTTPRequestHandler):
    def __init__(self, *args, token, allowed, **kwargs):
        self.expected = "Basic " + base64.b64encode(f"leadengine:{token}".encode()).decode()
        self.allowed = allowed
        super().__init__(*args, **kwargs)

    def send(self, status_code, body, content_type="application/json", **headers):
        self.send_response(status_code)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Content-Length", str(len(body)))
        for name, value in headers.items():
            self.send_header(name.replace("_", "-"), value)
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, status_code, item):
        self.send(status_code, json.dumps(item).encode())

    def authorized(self):
        if not any(ip_address(self.client_address[0]) in network for network in self.allowed):
            self.send_json(403, {"error": "Access is limited to the local network."})
            return False
        provided = self.headers.get("Authorization", "").encode()
        if not hmac.compare_digest(provided, self.expected.encode()):
            self.send(401, b"Sign in to leadEngine.", "text/plain; charset=utf-8",
                      WWW_Authenticate='Basic realm="leadEngine dashboard"')
            return False
        return True

    def log_request(self, code="-", size="-"):
        # Avoid logging request URLs and credentials.
        pass

    def do_GET(self):
        if not self.authorized():
            return
        path = urlsplit(self.path).path
        if path == "/":
            self.send(200, (ROOT / "web.html").read_bytes(), "text/html; charset=utf-8")
        elif path == "/api/status":
            self.send_json(200, run_details())
        elif path == "/api/config":
            config = CAMPAIGN if CAMPAIGN.exists() else ROOT / "campaign.example.json"
            lead_file = LEADS if LEADS.exists() else ROOT / "leads.example.csv"
            self.send_json(200, {"campaign": json.loads(config.read_text(encoding="utf-8")),
                                 "coohom": PRESET,
                                 "csv": lead_file.read_text(encoding="utf-8-sig"),
                                 "reoon": (ROOT / "_reoonAPI").is_file()})
        elif path == "/review.csv" and EXPORT.is_file():
            self.send(200, review_csv(), "text/csv; charset=utf-8",
                      Content_Disposition='attachment; filename="leadengine-review.csv"')
        else:
            self.send_json(404, {"error": "No resource at this address."})

    def do_POST(self):
        if not self.authorized():
            return
        if self.headers.get("X-LeadEngine") != "dashboard" or self.headers.get_content_type() != "application/json":
            self.send_json(403, {"error": "Invalid dashboard request."})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= MAX_BODY:
                raise ValueError("The request must be under 1 MiB.")
            data = json.loads(self.rfile.read(length))
            path = urlsplit(self.path).path
            if path == "/api/discover":
                with DISCOVERY_LOCK:
                    results = find_leads(STATE / "discovery/cities15000.zip",
                                         data["city"].strip().casefold(), data["country"].strip().upper(),
                                         data["category"].strip().casefold(), data.get("radius", 10))
                self.send_json(200, results)
                return
            if path == "/api/run":
                start_run(data)
            elif path == "/api/verify":
                start_verification()
            elif path == "/api/event":
                event, address, website = (data[key] for key in ("event", "email", "website"))
                if event not in ("sent", "bounce", "opt_out"):
                    raise ValueError("Choose a supported outreach event.")
                result = subprocess.run([str(ROOT / "bin/leadengine"), "record", event, address, website],
                                        cwd=ROOT, capture_output=True, text=True, timeout=10)
                if result.returncode:
                    raise ValueError("Could not record the event. Check the address and website, or wait for the active run.")
            else:
                self.send_json(404, {"error": "No resource at this address."})
                return
        except (ValueError, TypeError, KeyError, AttributeError, OSError, subprocess.SubprocessError) as error:
            message = str(error) if isinstance(error, ValueError) and not isinstance(error, json.JSONDecodeError) else "Invalid data or request could not be completed."
            self.send_json(400, {"error": message})
            return
        self.send_json(202, {"accepted": True})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bind", default="192.168.1.101")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--allow", default="192.168.1.0/24")
    args = parser.parse_args()
    WEB.mkdir(parents=True, exist_ok=True, mode=0o700)
    password = WEB / "password"
    try:
        with password.open("x", encoding="utf-8") as stream:
            password.chmod(0o600)
            stream.write(secrets.token_urlsafe(18) + "\n")
    except FileExistsError:
        pass
    allowed = (ip_network(args.allow), ip_network("127.0.0.0/8"))
    handler = partial(Dashboard, token=password.read_text().strip(), allowed=allowed)
    with ThreadingHTTPServer((args.bind, args.port), handler) as server:
        print(f"leadEngine dashboard listening at http://{args.bind}:{args.port}/", flush=True)
        server.serve_forever()


if __name__ == "__main__":
    main()
