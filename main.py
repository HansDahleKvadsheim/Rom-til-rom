#!/usr/bin/env python3
"""
main.py — ROM-TIL-ROM festgenerator

Kjør:
  python main.py                  # starter server, åpner nettleser
  python main.py deltakere.txt    # laster inn deltakere og starter
  python main.py timeplan.json    # gjenopptar lagret timeplan

Åpner http://localhost:7331 i nettleseren.
"""

import json
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import state as st
from models import parse_participants_text, build_frontend_state, SLOTS
from scheduler import (
    assign_host_groups,
    assign_routes,
    flytt_rom,
    bytt_rom,
    bytt_deltakere,
    flytt_deltaker,
    fjern_deltaker,
    legg_til_deltaker,
    endre_deltaker,
)

PORT = 7331
STATIC_DIR = Path(__file__).parent / "static"


# ─────────────────────────────────────────────────
# HTTP Handler
# ─────────────────────────────────────────────────

class Handler(BaseHTTPRequestHandler):

    def log_message(self, *args):
        pass  # Skru av request-logging i terminalen

    # ── Hjelpemetoder ──

    def send_json(self, data: dict, code: int = 200) -> None:
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def send_file(self, path: Path) -> None:
        content_types = {
            ".html": "text/html; charset=utf-8",
            ".css":  "text/css; charset=utf-8",
            ".js":   "application/javascript; charset=utf-8",
        }
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_types.get(path.suffix, "text/plain"))
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def read_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(length)) if length else {}

    def ok(self, ps) -> None:
        """Lagre ny tilstand og svar med oppdatert state."""
        st.set_participants(ps)
        self.send_json({"ok": True, "state": build_frontend_state(ps)})

    def error(self, msg: str) -> None:
        self.send_json({"error": msg})

    # ── GET ──

    def do_GET(self) -> None:
        if self.path == "/api/state":
            ps = st.get_participants()
            v  = st.get_version()
            s  = build_frontend_state(ps) if ps else None
            self.send_json({"version": v, "state": s})
            return

        # Statiske filer
        url_path = self.path.split("?")[0]
        if url_path == "/" or url_path == "/index.html":
            self.send_file(STATIC_DIR / "index.html")
        elif url_path.startswith("/static/"):
            rel = url_path[len("/static/"):]
            file_path = STATIC_DIR / rel
            if file_path.exists() and file_path.is_file():
                self.send_file(file_path)
            else:
                self.send_response(404); self.end_headers()
        else:
            # Fallback: send index for single-page-app navigasjon
            self.send_file(STATIC_DIR / "index.html")

    # ── POST ──

    def do_POST(self) -> None:
        body = self.read_body()
        path = self.path.split("?")[0]

        try:
            ps = st.get_participants()  # fersk kopi per forespørsel

            if path == "/api/load":
                ps = parse_participants_text(body["text"])
                if not ps:
                    raise ValueError("Ingen deltakere funnet. Sjekk formatet (Navn, Rom).")
                assign_host_groups(ps, SLOTS)
                assign_routes(ps, SLOTS)

            elif path == "/api/load_json":
                ps = st.participants_from_json(body["text"])

            elif path == "/api/generate":
                if not ps:
                    raise ValueError("Ingen deltakere å regenerere.")
                assign_host_groups(ps, SLOTS)
                assign_routes(ps, SLOTS)

            elif path == "/api/swap_rooms":
                bytt_rom(body["room1"], body["room2"], ps)

            elif path == "/api/move_room":
                flytt_rom(body["room"], int(body["target_slot"]), ps)

            elif path == "/api/swap_people":
                bytt_deltakere(int(body["slot"]), body["name1"], body["name2"], ps)

            elif path == "/api/move_person":
                flytt_deltaker(int(body["slot"]), body["name"], body["room"], ps)

            elif path == "/api/add":
                legg_til_deltaker(body["name"], body["room"], ps)

            elif path == "/api/edit":
                endre_deltaker(body["old_name"], body["name"], body["room"], ps)

            elif path == "/api/remove":
                fjern_deltaker(body["name"], ps)

            else:
                self.send_json({"error": f"Ukjent endepunkt: {path}"}, 404)
                return

            self.ok(ps)

        except (KeyError, TypeError) as e:
            self.error(f"Manglende parameter: {e}")
        except Exception as e:
            self.error(str(e))

    # ── OPTIONS (CORS preflight) ──

    def do_OPTIONS(self) -> None:
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()


# ─────────────────────────────────────────────────
# Oppstart
# ─────────────────────────────────────────────────

def load_initial(filename: str) -> None:
    path = Path(filename)
    if not path.exists():
        print(f"  Feil: finner ikke '{filename}'")
        return
    try:
        if path.suffix == ".json":
            ps = st.participants_from_json(path.read_text(encoding="utf-8"))
            print(f"  Gjenopptatt fra {filename} ({len(ps)} deltakere)")
        else:
            from models import parse_participants_text
            ps = parse_participants_text(path.read_text(encoding="utf-8"))
            if not ps:
                print("  Ingen deltakere funnet i filen.")
                return
            assign_host_groups(ps, SLOTS)
            assign_routes(ps, SLOTS)
            print(f"  Lastet {len(ps)} deltakere fra {filename}")
        st.set_participants(ps)
    except Exception as e:
        print(f"  Feil ved lasting: {e}")


def main() -> None:
    # Last inn fil fra argument, eller prøv autosave
    if len(sys.argv) > 1:
        load_initial(sys.argv[1])
    else:
        ps = st.load_autosave()
        if ps:
            st.set_participants(ps)
            print(f"  Gjenopptatt fra autosave ({len(ps)} deltakere)")

    server = HTTPServer(("127.0.0.1", PORT), Handler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()

    url = f"http://127.0.0.1:{PORT}"
    print(f"  Server kjører på {url}")
    webbrowser.open(url)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n  Stopper server.")
        server.shutdown()


if __name__ == "__main__":
    main()