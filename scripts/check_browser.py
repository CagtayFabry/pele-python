"""Local headless Chromium checks and screenshots; development tooling only."""

from __future__ import annotations

import json
import os
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from make_preview import main as make_preview

ROOT = Path(__file__).resolve().parents[1]


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass


def main():
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(ROOT / ".pixi/browsers")
    from playwright.sync_api import sync_playwright

    make_preview()
    output = ROOT / "build/browser"
    output.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0), partial(QuietHandler, directory=str(ROOT / "build"))
    )
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    url = f"http://127.0.0.1:{server.server_port}/preview.html"
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1100, "height": 1000}, device_scale_factor=2)
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(url, wait_until="networkidle")
            page.evaluate("document.fonts.ready")
            assert page.locator("article svg").count() == 7
            assert page.locator("#large-tree .pele-node").count() == 63
            assert page.locator("#large-tree .pele-edge").count() == 62
            results = page.locator("article").evaluate_all("""
                cards => cards.map(card => {
                    const svg = card.querySelector('svg');
                    const box = svg.getBoundingClientRect();
                    return {
                        diagram: card.querySelector('h2').textContent,
                        width: box.width, height: box.height,
                        labels: [...svg.querySelectorAll('text')].map(e => e.textContent)
                    };
                })
            """)
            for result in results:
                assert result["width"] > 0 and result["height"] > 0, result
                assert result["labels"], result
            assert not errors, errors
            for index, name in enumerate(("flowchart", "sequence")):
                page.locator("article").nth(index).screenshot(path=str(output / f"{name}.png"))
            page.locator("#large-tree").screenshot(path=str(output / "large-tree.png"))
            page.screenshot(path=str(output / "all-diagrams.png"), full_page=True)
            report = {"browser": browser.version, "url": url, "diagrams": results, "errors": errors}
            (output / "report.json").write_text(json.dumps(report, indent=2) + "\n", "utf-8")
            browser.close()
            print(
                f"PASS: six diagram types and a 63-node tree displayed in Chromium "
                f"{report['browser']}; no page errors"
            )
            print(f"Screenshots and report: {output}")
    finally:
        server.shutdown()
        server.server_close()
        worker.join()


if __name__ == "__main__":
    main()
