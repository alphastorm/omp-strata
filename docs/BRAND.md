# OMP Strata — brand spec

Identity for `alphastorm/omp-strata`: the profile, lifecycle tool and evidence that run the stock
[Oh My Pi](https://github.com/can1357/oh-my-pi) coding agent against a stock, local
[Strata](https://github.com/Niko1221/Strata) inference server on one Windows host, with every component
pinned and every claim measured on real hardware.

**Brand sibling of [OMP Session Gateway](https://github.com/alphastorm/omp-session-gateway),
[OMP NInfer](https://github.com/alphastorm/omp-ninfer) and
[OMP Oracle](https://github.com/alphastorm/omp-oracle).** OMP Strata shares the family ground, neutrals,
type, kinship rule and voice register defined by the gateway; this file is the complete authority for the
OMP Strata identity. Live emerald `#31C48D` belongs to the gateway, Local violet `#8E7BE8` to NInfer and
Answer rose `#DE82B7` to Oracle; the retired signal blue `#3FA9DC` and exec amber `#E0A33E` stay retired.

## Naming and message

- Repository: `alphastorm/omp-strata`. Display name: **OMP Strata**. The CLI stays `scripts/omp_strata.py`.
- Category: **stock local inference for coding agents**.
- Headline: **Nothing forked. Everything pinned.** The README's long form leads with what it is: "Stock Oh My
  Pi on a stock, local Strata server. Nothing forked, everything pinned."
- Entity grammar: *Oh My Pi (coding-agent client) → OMP Strata (profile, lifecycle tool, evidence) → Strata
  (inference engine) → the pinned model (served model).* Spell out "Oh My Pi" before using "OMP" on any
  surface that can be read standalone.
- Proof comes from what the repository does, stated as the README states it: every download pinned by URL,
  size and SHA-256; stock `setup.py` run unmodified from verified local inputs; loopback behind an API key;
  stock OMP in an isolated profile; a gate ledger with receipts for every claim.
- Status grammar: say **Candidate, not qualified** until a ledger says otherwise, and name the gate that
  fails. Never round a partial evaluation up, never publish a self-assigned score, and never transfer one
  profile's figures to another GPU or tuple.
- Primary action: **Get started**, linked to `docs/QUICKSTART.md`. The release ledger and
  `docs/DECISION.md` are the proof surfaces, never a second call to action.

## The mark: "The Seam"

Two strata, offset like beds across a fault: stock Oh My Pi above, stock Strata below. The dot sits at the
seam between them: the pinned, verified loopback integration this repository owns. Nothing else is drawn
because nothing else is added. Geometry (96×96 viewBox, all radii 2):

- upper stratum `x12 y22 w60 h10`
- lower stratum `x24 y64 w60 h10`
- dot `cx48 cy48 r8` in Seam teal

Rules, the family's numbers:

- Never use upstream OMP's π-with-plug mark or derivatives of it, and never set Strata's name in a way that
  implies the mark is theirs.
- Clearspace: one dot diameter (16 units) on all sides. Minimum size 16px.
- The dot is always Seam teal; the strata are Ink on dark surfaces (`logo.svg`) or Ink-dark on light
  surfaces (`logo-light.svg`). Never recolor, never give the dot a sibling's accent, never add a third
  stratum (three bars read as a menu icon).

## Color

The family ground and neutral ramp: `ground #060809`, `ink-dark #0B0E11`, `surface #0E1319`,
`border-subtle #161C22`, `border #1C232B`, `ink #E8ECEF`, `body #B6BEC7`, `muted #8A939D`.
OMP Strata owns:

| Token | Hex | oklch | Use |
|---|---|---|---|
| seam | `#37C4CB` | oklch(0.75 0.115 200) | the dot, links, eyebrows, the primary action, focus rings |
| seam-hover | `#78D6DB` | oklch(0.82 0.09 200) | link and action hover |
| kinship | `#F97316` | — (upstream orange) | citation micro-dot only; see the rule below |

Seam teal sits in the open gap between the gateway's emerald (163°) and the retired signal blue (233°),
clear of NVIDIA green, Qwen's purple gradient and any color Strata uses, so it implies no partnership. It
measures 9.5:1 against `ground`, and `ink-dark` text on it measures 9.1:1. Danger red `#C85045` stays the
family error color; never use teal for pass/fail states, and never use green or red for them either on a
branded surface: a gate result is a word in the ledger, not a color.

**Kinship rule (the gateway's):** upstream orange appears at most once per surface, only as a micro-dot
(≤5px UI, ≤8px artwork) beside an Oh My Pi mention — never in the mark, never on interactive elements,
never as a fill.

## Type

- **Public site:** system font stacks only — `system-ui, sans-serif` and `ui-monospace, monospace`. No
  remote fonts, scripts, stylesheets or CDNs.
- **Exported artwork:** `assets/banner.html` and `assets/og.html` use Space Grotesk 500/600 and JetBrains
  Mono 400/500, imported from Google Fonts by `assets/brand.css` at render time. Never copy that import into
  the site.
- Wordmark: "OMP Strata", weight 600, letter-spacing −0.015em. Mono eyebrows: 11–12px, uppercase,
  letter-spacing 0.16–0.18em.

## Voice

Sober and exact, in the gateway's register: sentence case except mono eyebrows, no emoji, no exclamation
marks. Every claim on an owned surface already appears in the README, the site or `docs/`, and every
measured number traces to a receipt under `releases/`. Artwork carries no version, date, GPU name or
measured number, so it never goes stale between candidates. Keep the standing disclaimer: "Community
project; not affiliated with or endorsed by the Oh My Pi maintainers, the Strata maintainer, Qwen or
NVIDIA." Never set OMP, Strata, Qwen or NVIDIA marks on an owned surface.

## Asset inventory

Paths are relative to the repository root. `assets/` and `site/` are presentation only; nothing under them
is read by the tooling, the tests that exercise it, or a release ledger.

| File | Purpose |
|---|---|
| `assets/logo.svg` | mark for dark backgrounds; site header mark and README dark mode |
| `assets/logo-light.svg` | mark for light backgrounds; README light mode |
| `assets/favicon.svg` | site favicon (96, rx22 tile) |
| `assets/brand.css` | shared tokens and primitives for the artwork sources |
| `assets/banner.html` | banner source (1280×320) |
| `assets/banner.png` | rendered banner @2x (2560×640) |
| `assets/og.html` | social preview source (1280×640) |
| `assets/og.png` | GitHub social preview and site `og:image` (1280×640) |
| `site/` | public site (`alphastorm.github.io/omp-strata`), system font stacks only. `.github/workflows/pages.yml` stages `logo.svg`, `favicon.svg` and `og.png` from `assets/` at deploy time, so `site/` never carries copies |

`tests/unit/test_site.py` (host-free, part of the normal `unittest` discovery and CI) fails when a site page
references an asset the deployment would not serve, when a staged copy is not ignored by Git, when
`og:image:width`/`og:image:height` disagree with `og.png`, when the sitemap, `robots.txt` and canonical
links disagree about the site's pages, or when the README badges or the site name a Strata or OMP version
other than the current candidate profile's pins.

## Regeneration

After editing an artwork source, run `python3 scripts/render_assets.py`. It renders `banner` and `og` with
headless Chrome (from `--chrome <path>`, `CHROME`, `PATH` or the default install) and verifies each PNG's
dimensions; name targets to render only some (`python3 scripts/render_assets.py og`). The render needs
network access for the webfonts. `--check` renders without writing and fails when a committed PNG no longer
matches its source. Byte equality holds only for the Chrome build and fonts that produced the committed
PNG, so `--check` is a same-machine check and stays out of CI.

## README header

The theme-aware mark heads the centered header block, as in the gateway README:

```html
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/logo.svg">
  <source media="(prefers-color-scheme: light)" srcset="assets/logo-light.svg">
  <img src="assets/logo-light.svg" alt="" width="72" height="72">
</picture>
```

Badges are shields.io flat style, one row, `labelColor 0B0E11`, values in `border` `#1C232B` or Seam teal
`#37C4CB` — never green or red status colors. Sanctioned badges: CI, the current candidate's Strata pin,
its OMP pin, license. The pin badges are static and must equal the current candidate profile's
`strata.tag` and `omp.version`; `tests/unit/test_site.py` enforces that, so a new candidate updates them in
the same change as the README's status.

## GitHub social preview

GitHub has no API for the repository social preview. After changing `assets/og.png`, upload it at
GitHub → Settings → General → Social preview.

## Relationship to upstream

Independent community project; not affiliated with or endorsed by the Oh My Pi maintainers or the Strata
maintainer. "OMP" and "Strata" appear in the name as plain nominative reference to the two stock projects
this repository runs unmodified; do not restyle either project's logo.
