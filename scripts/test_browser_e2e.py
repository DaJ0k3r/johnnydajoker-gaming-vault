#!/usr/bin/env python3
"""Real desktop/mobile browser smoke test for MADHOUSE (no external-site play claims).

Uses installed Chrome through Playwright, serves checkout locally and deliberately
blocks third-party traffic. Covers core user journeys, not every external game.
"""
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import threading
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]

class QuietFiles(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)
    def log_message(self, *args):
        pass

def check_site(page, url, mobile=False):
    errors = []
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    page.add_init_script("try { sessionStorage.setItem(\'jdj-intro-seen\',\'1\'); localStorage.setItem(\'jdj-intro-skip-v1\',\'1\'); } catch(e) {}")
    # No analytics, external adverts, game pages or third-party images in CI.
    page.route("https://**", lambda route: route.abort())
    page.goto(url, wait_until="domcontentloaded", timeout=20000)
    page.locator("#grid .card").first.wait_for(timeout=12000)
    assert page.locator("#grid .card").count() > 3, "No live catalogue cards"
    assert int(page.locator("#total").inner_text()) >= 100, "Unexpected catalogue count"
    assert page.locator("#daily-play").get_attribute("href") not in ("", "#", None), "Daily game not resolved"
    page.locator("#search").fill("Krunker")
    page.wait_for_timeout(250)
    assert page.locator("#grid .card").count() >= 1, "Search did not find Krunker"
    page.locator("#search").fill("")
    page.locator("#grid .card .heart").first.click()
    assert page.locator("#grid .card .heart.on").count() >= 1, "Favourite was not saved"
    page.reload(wait_until="domcontentloaded")
    page.locator("#grid .card").first.wait_for(timeout=12000)
    assert page.locator("#grid .card .heart.on").count() >= 1, "Favourites did not persist"
    page.locator("#roulette-spin").click()
    page.locator("#roulette-play").wait_for(state="visible", timeout=12000)
    page.locator("#shuffle-picks").click()
    page.locator("#lab-source-status").wait_for(timeout=12000)
    page.wait_for_function("document.querySelector('#lab-source-status').textContent.includes('loaded for testing')", timeout=12000)
    page.locator("#lab-list .lab-item").first.wait_for(timeout=12000)
    page.locator("#lab-search").fill("OpenLara")
    page.wait_for_timeout(200)
    page.locator("#lab-search").fill("")
    page.locator("#lab-list .lab-item button").first.click()
    assert not page.locator("#lab-player").evaluate("(el)=>el.hidden"), "Inline player did not open"
    assert page.locator("#lab-player-frame").get_attribute("src", timeout=3000).startswith("https://")
    page.locator("#lab-player-close").click()
    assert page.locator("#lab-player").evaluate("(el)=>el.hidden"), "Inline player did not close"
    assert not errors, "Browser JS errors: " + repr(errors[:3])
    print("PASS " + ("mobile" if mobile else "desktop") +
          " catalogue/search/favourites/daily/roulette/shuffle/feed/player")

def main():
    server = ThreadingHTTPServer(("127.0.0.1", 0), QuietFiles)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = "http://127.0.0.1:" + str(server.server_port) + "/"
    try:
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch(channel="chrome", headless=True, args=["--no-sandbox"])
            except Exception:
                browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
            for mobile, size in ((False, {"width": 1366, "height": 768}),
                                 (True, {"width": 390, "height": 844})):
                ctx = browser.new_context(viewport=size, service_workers="block")
                page = ctx.new_page()
                try:
                    check_site(page, url, mobile)
                finally:
                    ctx.close()
            browser.close()
    finally:
        server.shutdown()
        server.server_close()

if __name__ == "__main__":
    main()
