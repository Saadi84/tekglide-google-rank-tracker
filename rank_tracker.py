from __future__ import annotations

import csv
import argparse
import json
import random
import time
from datetime import datetime
from pathlib import Path
from typing import Callable
from urllib.error import HTTPError
from urllib.parse import parse_qs, quote_plus, unquote, urljoin, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

from selenium import webdriver
from selenium.common.exceptions import JavascriptException, WebDriverException


BASE_DIR = Path(__file__).resolve().parent
TARGETS_FILE = BASE_DIR / "targets.csv"
RESULTS_FILE = BASE_DIR / "rank_results.csv"
PROFILE_DIR = BASE_DIR / "chrome_profile"
DIAGNOSTICS_DIR = BASE_DIR / "diagnostics"
MAX_PAGES = 10
PAGE_WAIT_SECONDS = 4
CAPTCHA_WAIT_SECONDS = 300
WIX_TEST_KEYWORD = "Wix Development Agency"
WIX_TEST_TARGET = "https://tekglide.com/wix-development/"


def canonical(url: str) -> str:
    """Normalize a URL for exact landing-page comparison."""
    if not url:
        return ""
    url = unquote(url.strip())
    parsed = urlparse(url)
    if "google." in parsed.netloc and parsed.path == "/url":
        url = parse_qs(parsed.query).get("q", parse_qs(parsed.query).get("url", [url]))[0]
        parsed = urlparse(url)
    host = parsed.netloc.lower().split(":")[0]
    if host.startswith("www."):
        host = host[4:]
    path = "/" + "/".join(part for part in parsed.path.split("/") if part)
    if path != "/":
        path += "/"
    return f"{host}{path}".lower()


def load_targets() -> list[dict[str, str]]:
    with TARGETS_FILE.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return [r for r in rows if r.get("keyword", "").strip() and r.get("target_url", "").strip()]


def load_test_target(keyword: str) -> dict[str, str]:
    requested = keyword.strip()
    for target in load_targets():
        if target["keyword"].strip().casefold() == requested.casefold():
            return target
    raise SystemExit(f'Keyword not found in targets.csv: "{keyword}"')


def is_captcha(driver: webdriver.Chrome) -> bool:
    text = (driver.title + " " + driver.page_source[:250000]).lower()
    return any(x in text for x in ("unusual traffic", "our systems have detected", "recaptcha", "/sorry/"))


def wait_for_manual_captcha(
    driver: webdriver.Chrome,
    progress_callback: Callable[[str], None] | None = None,
) -> bool:
    try:
        if not is_captcha(driver):
            return True
    except WebDriverException:
        print("Chrome window band ho gayi; keyword skip kiya gaya.")
        return False
    report_progress(progress_callback, "Waiting for manual CAPTCHA. Solve it in the visible Chrome window.")
    deadline = time.time() + CAPTCHA_WAIT_SECONDS
    while time.time() < deadline:
        time.sleep(2)
        try:
            if not is_captcha(driver):
                time.sleep(1.5)
                if not is_captcha(driver):
                    report_progress(progress_callback, "CAPTCHA verification complete. Continuing rank check.")
                    return True
        except WebDriverException:
            return False
    print("5 minutes mein CAPTCHA complete nahi hua; keyword skip kiya gaya.")
    return False


def scroll_full_page(driver: webdriver.Chrome) -> None:
    previous = -1
    for _ in range(18):
        height = driver.execute_script("return Math.max(document.body.scrollHeight, document.documentElement.scrollHeight)")
        driver.execute_script("window.scrollTo(0, arguments[0])", height)
        time.sleep(0.45)
        if height == previous:
            break
        previous = height


def report_progress(callback: Callable[[str], None] | None, message: str) -> None:
    if callback:
        callback(message)
    else:
        print(message)


SCAN_SCRIPT = r"""
const badHosts = ['google.com', 'googleusercontent.com', 'gstatic.com', 'youtube.com'];
const containers = [...document.querySelectorAll('div.MjjYud')];

function unwrap(raw) {
    try {
        const url = new URL(raw, location.href);
        if (url.hostname.includes('google.') && url.pathname === '/url') {
            return url.searchParams.get('q') || url.searchParams.get('url') || raw;
        }
        return url.href;
    } catch (_) {
        return raw || '';
    }
}

function hasClearAdMarker(container) {
    // The old scanner walked distant ancestors and matched any attribute containing
    // "ad". That caused organic cards to inherit unrelated page-level ad text.
    for (const element of [container, ...container.querySelectorAll('*')]) {
        for (const name of ['aria-label', 'data-text-ad', 'data-is-ad', 'data-ad-slot']) {
            const value = (element.getAttribute(name) || '').trim();
            if (/^(ad|ads|advertisement|sponsored|sponsored results)$/i.test(value)) return true;
        }
    }
    const lines = (container.innerText || '').split(/\n+/).map(line => line.trim()).filter(Boolean);
    return lines.some(line => /^(ad|ads|advertisement|sponsored|sponsored results)$/i.test(line));
}

const output = [];
const allAnchorUrls = [...document.querySelectorAll('a[href]')].map(a => unwrap(a.href || a.getAttribute('href') || ''));
for (const container of containers) {
    const anchor = [...container.querySelectorAll('a')].find(a => a.querySelector('h3'));
    if (!anchor) continue;
    const titleNode = anchor.querySelector('h3');
    const href = unwrap(anchor.href || anchor.getAttribute('href') || '');
    const ad = hasClearAdMarker(container);
    const dataRank = container.getAttribute('data-rank');
    try {
        const url = new URL(href);
        const host = url.hostname.replace(/^www\./, '').toLowerCase();
        const googleRedirect = url.hostname.includes('google.') && url.pathname === '/goto';
        if (!url.protocol.startsWith('http') || (!googleRedirect && badHosts.some(value => host === value || host.endsWith('.' + value)))) continue;
        if (ad) continue;
        output.push({
            url: href,
            anchor_href: href,
            google_href: googleRedirect ? href : '',
            title: (titleNode.innerText || '').trim(),
            ad_status: 'Organic',
            data_rank: dataRank || ''
        });
    } catch (_) {}
}
return {
    results: output,
    diagnostics: {
        selector_counts: {
            'div.MjjYud': containers.length,
            'h3': document.querySelectorAll('h3').length,
            'a[href]': document.querySelectorAll('a[href]').length,
            'a containing h3': containers.filter(container => [...container.querySelectorAll('a')].some(a => a.querySelector('h3'))).length
        },
        anchor_urls: allAnchorUrls,
        page_url: location.href,
        page_title: document.title,
        cards_with_data_rank: containers.filter(container => container.hasAttribute('data-rank')).map(container => container.getAttribute('data-rank'))
    }
};
"""


def scan_results(driver: webdriver.Chrome) -> dict[str, object]:
    try:
        scan = driver.execute_script(SCAN_SCRIPT)
        if not isinstance(scan, dict):
            return {"results": [], "diagnostics": {}}
        results = scan.get("results", [])
        if isinstance(results, list):
            resolved = []
            for result in results:
                if not isinstance(result, dict):
                    continue
                if result.get("google_href"):
                    result["url"] = resolve_google_destination(result.get("url", ""))
                if result.get("url"):
                    resolved.append(result)
            scan["results"] = resolved
        return scan
    except JavascriptException:
        return {"results": [], "diagnostics": {}}


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, file, code, message, headers, new_url):
        return None


def resolve_google_destination(url: str) -> str:
    """Resolve Google's /goto wrapper without guessing its opaque token."""
    if not url:
        return ""
    parsed = urlparse(url)
    if not ((parsed.hostname or "").lower().endswith("google.com") and parsed.path == "/goto"):
        return url
    try:
        request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        build_opener(_NoRedirect).open(request, timeout=10)
    except HTTPError as error:
        location = error.headers.get("Location", "")
        return urljoin(url, location) if location else ""
    except OSError:
        return ""
    return ""


def global_position(google_page: int, local_position: int) -> int:
    return ((google_page - 1) * 10) + local_position


def create_driver() -> webdriver.Chrome:
    options = webdriver.ChromeOptions()
    options.add_argument(f"--user-data-dir={PROFILE_DIR}")
    options.add_argument("--lang=en-US")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-search-engine-choice-screen")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
    options.add_experimental_option("useAutomationExtension", False)
    driver = webdriver.Chrome(options=options)
    try:
        driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {
                "source": """
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                    window.chrome = {
                        runtime: {}
                    };
                """
            },
        )
    except Exception:
        pass
    return driver


def highlight_found_result(driver: webdriver.Chrome, anchor_href: str, position: int) -> None:
    highlighted = driver.execute_script(
        """
        const wanted = arguments[0];
        const anchor = [...document.querySelectorAll('div.MjjYud a[href]')]
            .find(item => item.href === wanted || item.getAttribute('href') === wanted);
        if (!anchor) return false;
        const card = anchor.closest('div.MjjYud') || anchor;
        card.scrollIntoView({block: 'center', inline: 'nearest'});
        card.style.outline = '4px solid #e11d48';
        card.style.outlineOffset = '6px';
        card.style.backgroundColor = 'rgba(225, 29, 72, 0.12)';
        return true;
        """,
        anchor_href,
    )
    print(f"  FOUND: calculated organic position {position}.")
    if not highlighted:
        print("  Matched result was found, but its browser card could not be highlighted.")
    input("  Press Enter in this terminal to close Chrome and continue... ")


def save_diagnostics(driver: webdriver.Chrome, keyword: str, page: int, diagnostics: dict[str, object]) -> None:
    DIAGNOSTICS_DIR.mkdir(exist_ok=True)
    stem = f"{keyword.lower().replace(' ', '_')}_page_{page}"
    (DIAGNOSTICS_DIR / f"{stem}.html").write_text(driver.page_source, encoding="utf-8")
    driver.save_screenshot(str(DIAGNOSTICS_DIR / f"{stem}.png"))
    (DIAGNOSTICS_DIR / f"{stem}.json").write_text(
        json.dumps(diagnostics, indent=2, ensure_ascii=True), encoding="utf-8"
    )
    print(f"  Zero-result diagnostics saved in {DIAGNOSTICS_DIR.name}/ ({stem}.*).")


def append_result(row: dict[str, object]) -> None:
    exists = RESULTS_FILE.exists()
    fields = ["keyword", "target_url", "position", "status", "google_page", "url_found", "title", "search_date", "search_time"]
    with RESULTS_FILE.open("a", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        if not exists:
            writer.writeheader()
        writer.writerow(row)


def check_keyword(
    driver: webdriver.Chrome,
    keyword: str,
    target_url: str,
    test_mode: bool = False,
    pause_after_found: bool = False,
    progress_callback: Callable[[str], None] | None = None,
) -> dict[str, object]:
    target = canonical(target_url)
    now = datetime.now()
    for page in range(1, MAX_PAGES + 1):
        start = (page - 1) * 10
        # Basic web rendering keeps the real destination in the result anchor;
        # the modern rendering can expose only opaque /goto tokens instead.
        url = f"https://www.google.com/search?q={quote_plus(keyword)}&hl=en&gl=us&gbv=1&pws=0&filter=0&start={start}"
        report_progress(progress_callback, f"Checking Google page {page}")
        driver.get(url)
        time.sleep(random.uniform(PAGE_WAIT_SECONDS, PAGE_WAIT_SECONDS + 2.5))
        if is_captcha(driver):
            report_progress(progress_callback, "Waiting for manual CAPTCHA. Solve it in the visible Chrome window.")
        if not wait_for_manual_captcha(driver, progress_callback):
            return build_row(keyword, target_url, "", "CAPTCHA/TIMEOUT", page, "", "", now)
        scroll_full_page(driver)
        report_progress(progress_callback, "Reading organic results")
        scan = scan_results(driver)
        results = scan.get("results", [])
        diagnostics = scan.get("diagnostics", {})
        if not isinstance(results, list):
            results = []
        report_progress(progress_callback, f"Page {page}: {len(results)} organic result cards read")
        if test_mode:
            print("Position | Title | URL | Ad status")
            for local_position, result in enumerate(results, start=1):
                position = global_position(page, local_position)
                print(f"{position} | {result.get('title', '')} | {result.get('url', '')} | {result.get('ad_status', 'Organic')}")
        if not results:
            save_diagnostics(driver, keyword, page, diagnostics if isinstance(diagnostics, dict) else {})
        for local_position, result in enumerate(results, start=1):
            if canonical(result.get("url", "")) == target:
                position = global_position(page, local_position)
                if pause_after_found:
                    highlight_found_result(driver, result.get("anchor_href", ""), position)
                report_progress(progress_callback, f"Exact target found at organic position {position}")
                return build_row(keyword, target_url, position, "FOUND", page, result.get("url", ""), result.get("title", ""), now)
    report_progress(progress_callback, "Not found in first 100 results")
    return build_row(keyword, target_url, "", "Not Found (>100)", "", "", "", now)


def build_row(keyword, target_url, position, status, page, found, title, started):
    return {
        "keyword": keyword,
        "target_url": target_url,
        "position": position,
        "status": status,
        "google_page": page,
        "url_found": found,
        "title": title,
        "search_date": started.strftime("%Y-%m-%d"),
        "search_time": started.strftime("%H:%M:%S"),
    }


def run_local_parser_tests() -> None:
    assert canonical("https://www.tekglide.com/wix-development/?utm_source=test#top") == "tekglide.com/wix-development/"
    assert canonical("https://tekglide.com/wix-development/blog-post") != "tekglide.com/wix-development/"
    assert canonical("https://google.com/url?q=https%3A%2F%2Ftekglide.com%2Fwix-development%2F") == "tekglide.com/wix-development/"
    assert global_position(1, 3) == 3
    assert global_position(2, 5) == 15
    assert global_position(3, 5) == 25
    print("Local parser tests passed.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Track exact Tekglide Google landing-page rankings.")
    test_group = parser.add_mutually_exclusive_group()
    test_group.add_argument("--test-wix", action="store_true", help="Scan only Wix Development Agency.")
    test_group.add_argument("--test-keyword", help="Scan one keyword found in targets.csv.")
    parser.add_argument("--self-test", action="store_true", help="Run local URL parser tests without opening Chrome.")
    parser.add_argument("--pause-after-found", action="store_true", help="Highlight a found result and wait for Enter before closing Chrome.")
    args = parser.parse_args()
    print("=== TEKGLIDE EXACT-URL RANK TRACKER V10 ===")
    print("Sponsored results ignore honge; exact approved landing page hi accept hogi.\n")
    if args.self_test:
        run_local_parser_tests()
        return
    if args.test_keyword:
        targets = [load_test_target(args.test_keyword)]
    elif args.test_wix:
        targets = [{"keyword": WIX_TEST_KEYWORD, "target_url": WIX_TEST_TARGET}]
    else:
        targets = load_targets()
    if args.test_wix:
        print(f"TEST MODE: {WIX_TEST_KEYWORD} -> {WIX_TEST_TARGET}\n")
    elif args.test_keyword:
        print(f"TEST MODE: {targets[0]['keyword']} -> {targets[0]['target_url']}\n")
    driver = create_driver()
    try:
        for index, item in enumerate(targets, start=1):
            keyword = item["keyword"].strip()
            target_url = item["target_url"].strip()
            print(f"\n[{index}/{len(targets)}] {keyword}")
            result = check_keyword(
                driver,
                keyword,
                target_url,
                test_mode=args.test_wix or bool(args.test_keyword),
                pause_after_found=args.pause_after_found,
            )
            append_result(result)
            if result["status"] == "FOUND":
                print(f"  FOUND: position {result['position']} | {result['url_found']}")
            else:
                print(f"  {result['status']}")
            if index < len(targets):
                time.sleep(8)
    finally:
        print(f"\nComplete. Results saved: {RESULTS_FILE.name}")
        driver.quit()


if __name__ == "__main__":
    main()

