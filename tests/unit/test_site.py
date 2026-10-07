"""site/, assets/, the Pages workflow and the README header stay coherent (docs/BRAND.md).

The site carries no copies of brand assets: `.github/workflows/pages.yml` stages them from `assets/` at deploy
time, so a page may only reference a file that is either tracked under `site/` or staged by that workflow. The
README's pin badges and the site's status paragraph must name the current candidate's Strata and OMP pins.
"""

from __future__ import annotations

from html.parser import HTMLParser
import json
import re
import unittest

from scripts.render_assets import ASSETS, ROOT, TARGETS, png_dimensions
from tests.candidate import CURRENT

SITE = ROOT / "site"
SITE_URL = "https://alphastorm.github.io/omp-strata/"
WORKFLOW = ROOT / ".github/workflows/pages.yml"
PROFILE = json.loads((ROOT / "profiles" / f"{CURRENT}.json").read_text(encoding="utf-8"))


def staged() -> dict[str, str]:
    """`site/<name>` -> `assets/<source>` for every `cp` line of the Pages workflow."""
    pairs = re.findall(r"^\s*cp (assets/\S+) site/(\S+)\s*$", WORKFLOW.read_text(encoding="utf-8"), re.M)
    return {name: source for source, name in pairs}


class References(HTMLParser):
    """Local hrefs/srcs plus the metadata the site's URLs must agree on."""

    def __init__(self) -> None:
        super().__init__()
        self.local: list[tuple[str, str]] = []
        self.meta: dict[str, str] = {}
        self.canonical: str | None = None
        self.remote_loads: list[str] = []

    def handle_starttag(self, tag, attrs):
        a = {key: value or "" for key, value in attrs}
        prop = a.get("property")
        if tag == "meta" and prop:
            self.meta[prop] = a.get("content", "")
        if tag == "link" and a.get("rel") == "canonical":
            self.canonical = a.get("href")
        loads = tag in ("img", "script") or (tag == "link" and a.get("rel") in ("stylesheet", "icon", "preload", "manifest"))
        url = (a.get("src") if tag in ("img", "script") else a.get("href")) if loads else None
        if url is None:
            return
        if url.startswith(("http://", "https://", "//")):
            self.remote_loads.append(url)
        else:
            self.local.append((tag, url))


def parse(path) -> References:
    refs = References()
    refs.feed(path.read_text(encoding="utf-8"))
    return refs


class SiteTests(unittest.TestCase):
    def test_staged_assets_have_a_source_and_are_ignored(self):
        names = staged()
        self.assertEqual({"logo.svg", "favicon.svg", "og.png"}, set(names))
        ignored = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
        for name, source in names.items():
            self.assertTrue((ROOT / source).is_file(), source)
            self.assertIn(f"/site/{name}", ignored)

    def test_every_local_reference_is_served(self):
        refs = parse(SITE / "index.html")
        names = staged()
        self.assertTrue(refs.local)
        for tag, url in refs.local:
            if url in ("", "#") or url.startswith("#"):
                continue
            self.assertTrue(url in names or (SITE / url).is_file(), f"<{tag}> references {url!r}")

    def test_site_loads_nothing_remote(self):
        refs = parse(SITE / "index.html")
        self.assertEqual([], refs.remote_loads)
        self.assertNotIn("fonts.googleapis", (SITE / "index.html").read_text(encoding="utf-8"))

    def test_canonical_sitemap_robots_and_llms_agree(self):
        refs = parse(SITE / "index.html")
        self.assertEqual(SITE_URL, refs.canonical)
        self.assertEqual(SITE_URL, refs.meta.get("og:url"))
        locs = re.findall(r"<loc>([^<]+)</loc>", (SITE / "sitemap.xml").read_text(encoding="utf-8"))
        self.assertEqual([SITE_URL], locs)
        self.assertIn(f"Sitemap: {SITE_URL}sitemap.xml", (SITE / "robots.txt").read_text(encoding="utf-8"))
        self.assertIn(SITE_URL, (SITE / "llms.txt").read_text(encoding="utf-8"))

    def test_social_preview_matches_the_rendered_png(self):
        refs = parse(SITE / "index.html")
        self.assertEqual(f"{SITE_URL}og.png", refs.meta.get("og:image"))
        self.assertEqual("assets/og.png", staged()["og.png"])
        width, height = png_dimensions(ASSETS / "og.png")
        self.assertEqual((str(width), str(height)), (refs.meta.get("og:image:width"), refs.meta.get("og:image:height")))

    def test_rendered_artwork_has_the_declared_dimensions(self):
        for name, (width, height, scale) in TARGETS.items():
            self.assertEqual((width * scale, height * scale), png_dimensions(ASSETS / f"{name}.png"), name)

    def test_readme_header_and_pin_badges_name_the_current_candidate(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        for mark in ("assets/logo.svg", "assets/logo-light.svg"):
            self.assertIn(f'srcset="{mark}"', readme)
            self.assertTrue((ROOT / mark).is_file(), mark)
        self.assertEqual(PROFILE["strata"]["tag"], self.badge(readme, "Strata"))
        self.assertEqual(PROFILE["omp"]["version"], self.badge(readme, "OMP"))
        self.assertIn(CURRENT, readme)

    def test_site_status_names_the_current_candidate(self):
        text = (SITE / "index.html").read_text(encoding="utf-8")
        self.assertIn(CURRENT, text)
        self.assertIn(f"stock Strata {PROFILE['strata']['tag']}", text)
        self.assertIn(f"stock OMP {PROFILE['omp']['version']}", text)

    def badge(self, readme: str, label: str) -> str:
        match = re.search(rf"img\.shields\.io/badge/{label}-([^-?]+)-", readme)
        self.assertIsNotNone(match, f"{label} pin badge")
        assert match is not None
        return match[1]


if __name__ == "__main__":
    unittest.main()

