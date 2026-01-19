#!/usr/bin/env python3

from http.server import BaseHTTPRequestHandler, HTTPServer
import os

from timetable_svg import ROUTE_COLORS, get_schedule, generate_svg_string


class SvgHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path in ("/", "/mobile"):
            self._handle_mobile()
            return
        if self.path in ("/timetable.svg", "/svg"):
            self._handle_svg()
            return
        if self.path == "/manifest.json":
            self._serve_file("manifest.json", "application/manifest+json; charset=utf-8")
            return
        if self.path == "/sw.js":
            self._serve_file("sw.js", "application/javascript; charset=utf-8")
            return
        if self.path == "/icon.svg":
            self._serve_file("icon.svg", "image/svg+xml; charset=utf-8")
            return
        if self.path == "/favicon.ico":
            self._serve_file("favicon.ico", "image/x-icon")
            return

        self.send_error(404, "Not found")

    def _handle_svg(self) -> None:
        svg = generate_svg_string()
        payload = svg.encode("utf-8")

        self.send_response(200)
        self.send_header("Content-Type", "image/svg+xml; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _handle_mobile(self) -> None:
        rows, now = get_schedule(limit=None)

        def esc(text: str) -> str:
            return (
                text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
            )

        def fmt_time(t, now_dt) -> str:
            minutes = max(0, int((t - now_dt).total_seconds() // 60))
            return f"{t.strftime('%H:%M')} · {minutes}m"

        cards = []
        for row in rows:
            route = str(row["route"])
            stop_name = str(row["stop_name"])
            direction = str(row["direction"])
            times = row["times"]
            t1 = fmt_time(times[0], now) if len(times) > 0 else "--:--"
            t2 = fmt_time(times[1], now) if len(times) > 1 else "--:--"
            remaining = [fmt_time(t, now) for t in times[2:]]
            color = ROUTE_COLORS.get(route, "#222222")
            extra_html = ""
            if remaining:
                items = "".join(f"<li>{esc(t)}</li>" for t in remaining)
                extra_html = f"""
        <div class="more">
          <button class="more-toggle" type="button" aria-expanded="false">More trains</button>
          <ul class="more-list">
            {items}
          </ul>
        </div>
"""
            cards.append(f"""
      <article class="card">
        <div class="badge" style="background:{color}">{esc(route)}</div>
        <div class="meta">
          <div class="stop">{esc(stop_name)} <span class="dir">{esc(direction)}</span></div>
        </div>
        <div class="times">
          <div class="time">{esc(t1)}</div>
          <div class="time muted">{esc(t2)}</div>
        </div>
        {extra_html}
      </article>
""")

        cards_html = (
            "".join(cards) if cards else '<div class="empty">No arrivals found.</div>'
        )
        html = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Jackson Park MTA Arrivals</title>
    <link rel="manifest" href="/manifest.json" />
    <link rel="icon" href="/icon.svg" />
    <link rel="shortcut icon" href="/favicon.ico" />
    <meta name="theme-color" content="#111111" />
    <style>
      :root {{
        color-scheme: light dark;
        --bg: #fafaf7;
        --card: #ffffff;
        --text: #151515;
        --muted: #5c6169;
        --muted-2: #6f6f6f;
        --shadow: 0 10px 24px rgba(0, 0, 0, 0.06);
        --button-bg: rgba(0, 0, 0, 0.06);
        --button-text: #151515;
      }}
      @media (prefers-color-scheme: dark) {{
        :root {{
          --bg: #0f1114;
          --card: #161a20;
          --text: #f2f2f2;
          --muted: #9aa3ad;
          --muted-2: #7f8792;
          --shadow: 0 12px 28px rgba(0, 0, 0, 0.45);
          --button-bg: rgba(255, 255, 255, 0.12);
          --button-text: #f2f2f2;
        }}
      }}
      body[data-theme="dark"] {{
        --bg: #0f1114;
        --card: #161a20;
        --text: #f2f2f2;
        --muted: #9aa3ad;
        --muted-2: #7f8792;
        --shadow: 0 12px 28px rgba(0, 0, 0, 0.45);
        --button-bg: rgba(255, 255, 255, 0.12);
        --button-text: #f2f2f2;
      }}
      body[data-theme="light"] {{
        --bg: #fafaf7;
        --card: #ffffff;
        --text: #151515;
        --muted: #5c6169;
        --muted-2: #6f6f6f;
        --shadow: 0 10px 24px rgba(0, 0, 0, 0.06);
        --button-bg: rgba(0, 0, 0, 0.06);
        --button-text: #151515;
      }}
      body {{
        margin: 0;
        font-family: "Avenir Next", Avenir, "Helvetica Neue", Helvetica, Arial, sans-serif;
        background: var(--bg);
        color: var(--text);
        transition: background-color 240ms ease, color 240ms ease;
      }}
      header {{
        padding: 20px 18px 10px;
        display: flex;
        align-items: baseline;
        justify-content: space-between;
        gap: 12px;
        animation: fade-in 420ms ease-out;
      }}
      .title {{
        font-size: 20px;
        font-weight: 600;
        letter-spacing: 0.12em;
        text-transform: uppercase;
      }}
      .asof {{
        font-size: 14px;
        color: var(--muted-2);
      }}
      .actions {{
        display: inline-flex;
        align-items: center;
        gap: 10px;
      }}
      .theme-toggle {{
        appearance: none;
        border: 0;
        border-radius: 999px;
        padding: 6px 12px;
        font-size: 14px;
        font-weight: 600;
        background: var(--button-bg);
        color: var(--button-text);
        cursor: pointer;
        transition: background-color 240ms ease, color 240ms ease;
      }}
      .refresh {{
        appearance: none;
        border: 0;
        border-radius: 999px;
        width: 36px;
        height: 36px;
        background: var(--button-bg);
        color: var(--button-text);
        cursor: pointer;
        display: grid;
        place-items: center;
        transition: background-color 240ms ease, color 240ms ease;
      }}
      .refresh svg {{
        width: 18px;
        height: 18px;
        display: block;
      }}
      .refresh.spin svg {{
        animation: spin 600ms linear infinite;
      }}
      main {{
        padding: 6px 18px 18px;
        display: grid;
        gap: 12px;
      }}
      .card {{
        display: grid;
        grid-template-columns: 52px 1fr auto;
        align-items: center;
        gap: 12px;
        padding: 12px 14px;
        background: var(--card);
        border-radius: 14px;
        box-shadow: var(--shadow);
        transition: background-color 240ms ease, box-shadow 240ms ease;
        animation: rise-in 520ms ease-out both;
      }}
      .more {{
        grid-column: 1 / -1;
        margin-top: 8px;
        font-size: 20px;
        color: var(--muted);
      }}
      .more-toggle {{
        appearance: none;
        background: transparent;
        border: 0;
        padding: 0;
        font: inherit;
        font-weight: 600;
        color: inherit;
        cursor: pointer;
      }}
      .more-toggle::after {{
        content: "▾";
        margin-left: 6px;
        font-size: 12px;
        color: var(--muted-2);
      }}
      .more.open .more-toggle::after {{
        content: "▴";
      }}
      .more-list {{
        margin: 8px 0 0;
        padding-left: 18px;
        display: grid;
        gap: 4px;
        color: var(--muted-2);
        max-height: 0;
        opacity: 0;
        transform: translateY(-4px);
        overflow: hidden;
        transition: max-height 260ms ease, opacity 260ms ease, transform 260ms ease;
      }}
      .more.open .more-list {{
        opacity: 1;
        transform: translateY(0);
      }}
      .badge {{
        width: 58px;
        height: 58px;
        border-radius: 29px;
        display: grid;
        place-items: center;
        color: #ffffff;
        font-weight: 700;
        font-size: 24px;
      }}
      .stop {{
        font-size: 20px;
        font-weight: 600;
      }}
      .dir {{
        font-size: 20px;
        color: var(--muted);
        margin-left: 6px;
        font-weight: 500;
      }}
      .times {{
        text-align: right;
        display: grid;
        gap: 6px;
        font-weight: 600;
        font-size: 20px;
      }}
      .muted {{
        color: var(--muted-2);
        font-weight: 500;
      }}
      .empty {{
        padding: 22px 0;
        text-align: center;
        color: var(--muted-2);
      }}
      @keyframes rise-in {{
        from {{
          opacity: 0;
          transform: translateY(10px);
        }}
        to {{
          opacity: 1;
          transform: translateY(0);
        }}
      }}
      @keyframes fade-in {{
        from {{
          opacity: 0;
        }}
        to {{
          opacity: 1;
        }}
      }}
      @keyframes spin {{
        from {{
          transform: rotate(0deg);
        }}
        to {{
          transform: rotate(360deg);
        }}
      }}
      .card:nth-child(1) {{ animation-delay: 40ms; }}
      .card:nth-child(2) {{ animation-delay: 80ms; }}
      .card:nth-child(3) {{ animation-delay: 120ms; }}
      .card:nth-child(4) {{ animation-delay: 160ms; }}
      .card:nth-child(5) {{ animation-delay: 200ms; }}
      .card:nth-child(6) {{ animation-delay: 240ms; }}
      .card:nth-child(7) {{ animation-delay: 280ms; }}
      .card:nth-child(8) {{ animation-delay: 320ms; }}
    </style>
  </head>
  <body>
    <header>
      <div class="title">Jackson Park MTA Arrivals</div>
      <div class="actions">
        <button class="theme-toggle" type="button" aria-pressed="false">Dark</button>
        <button class="refresh" type="button" aria-label="Refresh arrivals" title="Refresh">
          <svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 12a9 9 0 1 1-2.64-6.36" />
            <polyline points="21 3 21 9 15 9" />
          </svg>
        </button>
        <div class="asof">As of {now.strftime("%a %b %d %H:%M")}</div>
      </div>
    </header>
    <main>
      {cards_html}
    </main>
    <script>
      if ("serviceWorker" in navigator) {{
        window.addEventListener("load", () => {{
          navigator.serviceWorker.register("/sw.js");
        }});
      }}
      const refreshButton = document.querySelector(".refresh");
      const themeButton = document.querySelector(".theme-toggle");
      const storedTheme = localStorage.getItem("theme");
      if (storedTheme) {{
        document.body.setAttribute("data-theme", storedTheme);
        if (themeButton) {{
          themeButton.setAttribute("aria-pressed", storedTheme === "dark" ? "true" : "false");
          themeButton.textContent = storedTheme === "dark" ? "Light" : "Dark";
        }}
      }}
      if (themeButton) {{
        themeButton.addEventListener("click", () => {{
          const current = document.body.getAttribute("data-theme");
          const next = current === "dark" ? "light" : "dark";
          document.body.setAttribute("data-theme", next);
          localStorage.setItem("theme", next);
          themeButton.setAttribute("aria-pressed", next === "dark" ? "true" : "false");
          themeButton.textContent = next === "dark" ? "Light" : "Dark";
        }});
      }}
      const triggerRefresh = () => {{
        if (refreshButton) refreshButton.classList.add("spin");
        window.location.reload();
      }};
      if (refreshButton) {{
        refreshButton.addEventListener("click", triggerRefresh);
      }}
      setInterval(triggerRefresh, 30000);
      document.querySelectorAll(".more").forEach((section) => {{
        const button = section.querySelector(".more-toggle");
        const list = section.querySelector(".more-list");
        if (!button || !list) return;
        button.addEventListener("click", () => {{
          const isOpen = section.classList.toggle("open");
          button.setAttribute("aria-expanded", String(isOpen));
          if (isOpen) {{
            list.style.maxHeight = list.scrollHeight + "px";
          }} else {{
            list.style.maxHeight = "0px";
          }}
        }});
      }});
    </script>
  </body>
</html>
"""
        payload = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _serve_file(self, path: str, content_type: str) -> None:
        try:
            with open(path, "rb") as handle:
                data = handle.read()
        except OSError:
            self.send_error(404, "Not found")
            return
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format: str, *args) -> None:
        return


def run_server(host: str = "0.0.0.0", port: int = 8100) -> None:
    server = HTTPServer((host, port), SvgHandler)
    print(f"Serving on http://{host}:{port}")
    try:
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == "__main__":
    env_port = os.getenv("PORT")
    port = int(env_port) if env_port else 8100
    run_server(port=port)
