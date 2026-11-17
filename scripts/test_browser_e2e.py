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
    assert page.locator("html").evaluate("(el)=>el.classList.contains('skip-joker-intro')"), "Returning visitor did not get early intro bypass"

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
    # The largest discovery queue must be searchable and distinguish
    # HTTP/browser observations from gameplay verification.
    page.locator("#lab-sort").select_option("source")
    page.locator("#lab-list .lab-item .lab-source").first.wait_for(timeout=8000)
    assert page.locator("#lab-list .lab-item").first.locator(".lab-evidence").count() == 1, "Discovery evidence missing"
    assert "not a playable-game test" in page.locator("#lab-list .lab-item").first.locator(".lab-evidence").inner_text().lower() or "not checked" in page.locator("#lab-list .lab-item").first.locator(".lab-evidence").inner_text().lower() or "not-tested" in page.locator("#lab-list .lab-item").first.locator(".lab-evidence").inner_text().lower()
    page.locator("#lab-list .lab-item").first.locator("select").select_option("notgame")
    assert page.evaluate("Object.values(JSON.parse(localStorage.getItem('jdj-testlab-v1')||'{}')).includes('notgame')"), "Review result was not saved"
    page.locator("#lab-filter").select_option("notgame")
    page.locator("#lab-list .lab-item").first.wait_for(timeout=8000)
    page.locator("#lab-filter").select_option("pending")

    page.locator("#lab-search").fill("OpenLara")
    page.wait_for_timeout(200)
    page.locator("#lab-search").fill("")
    page.locator("#lab-list .lab-item button").first.click()
    assert not page.locator("#lab-player").evaluate("(el)=>el.hidden"), "Inline player did not open"
    assert page.locator("#lab-player-frame").get_attribute("src", timeout=3000).startswith("https://")
    page.locator("#lab-player-close").click()
    assert page.locator("#lab-player").evaluate("(el)=>el.hidden"), "Inline player did not close"
    # Newly indexed category pages must really load and remain usable on phones.
    assert page.locator('.vault-genre-nav a[href="./genres/racing/"]').count() == 1
    page.locator('.vault-genre-nav a[href="./genres/racing/"]').click()
    page.wait_for_url("**/genres/racing/", timeout=10000)
    assert page.locator('.grid .card').count() >= 4
    assert page.locator('link[rel="canonical"]').get_attribute("href") == "https://johnnydajoker.com/genres/racing/"
    if mobile:
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 4"), "Racing genre page overflows mobile viewport"
    # The two MADHOUSE originals must load and their START actions respond.
    for path in ("games/neon-dodge/", "games/nightshift-racer/"):
        page.goto(url + path, wait_until="domcontentloaded", timeout=15000)
        page.locator("canvas#c").wait_for(timeout=8000)
        assert page.locator("canvas#c").evaluate("(c) => c.width > 0 && c.height > 0")
        start = page.locator("#start")
        start.wait_for(timeout=8000)
        if mobile:
            start.tap(timeout=8000)
        else:
            start.click(timeout=8000)
        page.wait_for_timeout(250)
    assert not errors, "Browser JS errors: " + repr(errors[:3])
    print("PASS " + ("mobile" if mobile else "desktop") +
          " catalogue/search/favourites/daily/roulette/shuffle/feed/player/genre/originals")

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
                ctx = browser.new_context(viewport=size, is_mobile=mobile,
                                          has_touch=mobile, device_scale_factor=2 if mobile else 1,
                                          service_workers="block")
                page = ctx.new_page()
                try:
                    check_site(page, url, mobile)
                finally:
                    ctx.close()
            # First visit must still show Johnny's full cinematic intro;
            # tapping SKIP should save preference and make the next navigation instant.
            first = browser.new_context(viewport={"width":390,"height":844}, is_mobile=True, has_touch=True, service_workers="block")
            fresh = first.new_page()
            fresh.route("https://**", lambda route: route.abort())
            fresh.goto(url, wait_until="domcontentloaded", timeout=20000)
            fresh.locator("#joker-intro").wait_for(state="visible", timeout=6000)
            assert not fresh.locator("html").evaluate("(el)=>el.classList.contains('skip-joker-intro')"), "First visitor lost branded intro"
            fresh.locator("#intro-skip").tap(timeout=6000)
            assert fresh.evaluate("localStorage.getItem('jdj-intro-skip-v1')==='1'"), "Skip choice not saved"
            fresh.reload(wait_until="domcontentloaded")
            assert fresh.locator("html").evaluate("(el)=>el.classList.contains('skip-joker-intro')"), "Intro replayed unexpectedly on return"
            first.close()
            browser.close()
    finally:
        server.shutdown()
        server.server_close()

if __name__ == "__main__":
    main()
