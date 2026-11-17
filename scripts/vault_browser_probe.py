#!/usr/bin/env python3
"""Headless Chromium observation, NOT gameplay verification.

Visit a few proposed URLs and record whether a browser renders an interactive
surface. Captchas, login walls and canvas decorations are not proof of playability.
"""
import json
import time
from vault_discovery import REPORT, safe_url

def main():
    data = json.loads(REPORT.read_text(encoding="utf-8"))
    try:
        from playwright.sync_api import sync_playwright, TimeoutError as BrowserTimeout
    except ImportError:
        for item in data.get("proposals", []):
            item["browser"] = "not-tested (Playwright not installed)"
        REPORT.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        except Exception:
            try:
                # GitHub-hosted Ubuntu runners generally have Google Chrome installed,
                # even if Playwright's downloadable Chromium failed to install.
                browser = p.chromium.launch(channel="chrome", headless=True, args=["--no-sandbox"])
            except Exception as exc:
                for item in data.get("proposals", []):
                    item["browser"] = "browser-unavailable (" + type(exc).__name__ + ")"
                REPORT.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
                print("Chrome/Chromium unavailable; no game marked playable.")
                return
        for item in data.get("proposals", [])[:6]:
            if not safe_url(item.get("url")):
                item["browser"] = "unsafe-url"
                continue
            context = browser.new_context(ignore_https_errors=False, service_workers="block",
                                          viewport={"width": 1280, "height": 720})
            page = context.new_page()
            try:
                response = page.goto(item["url"], wait_until="domcontentloaded", timeout=15000)
                page.wait_for_timeout(1400)
                state = page.evaluate("""() => ({
                    canvas: document.querySelectorAll('canvas').length,
                    iframe: document.querySelectorAll('iframe').length,
                    controls: document.querySelectorAll('button, [role=button], input').length,
                    text: (document.body?.innerText || '').slice(0, 1500).toLowerCase()
                })""")
                if not response or response.status >= 400:
                    item["browser"] = "blocked-or-error"
                elif any(w in state["text"] for w in ("verify you are human", "checking your browser", "access denied", "captcha")):
                    item["browser"] = "bot-challenge"
                elif state["canvas"] or state["iframe"]:
                    item["browser"] = "rendered-with-canvas-or-frame (NOT gameplay-tested)"
                elif state["controls"]:
                    item["browser"] = "rendered-with-controls (NOT gameplay-tested)"
                else:
                    item["browser"] = "rendered-static-or-unclear"
            except Exception as exc:
                item["browser"] = "browser-inconclusive (" + type(exc).__name__ + ")"
            finally:
                context.close()
        browser.close()
    REPORT.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("Browser observations updated for", len(data.get("proposals", [])), "proposals")

if __name__ == "__main__":
    main()
