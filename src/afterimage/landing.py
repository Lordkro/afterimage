from __future__ import annotations

from html import escape

from afterimage.pricing import HIT_USDC, MISS_USDC, SEARCH_USDC
from afterimage.settings import Settings

ICON_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" fill="none">
  <rect width="32" height="32" rx="7" fill="#090807"/>
  <rect x="0.75" y="0.75" width="30.5" height="30.5" rx="6.25" stroke="#3d3426"/>
  <text x="6" y="23" font-family="Georgia, serif" font-size="18" fill="#e09b3d">A</text>
  <text x="8" y="24.5" font-family="Georgia, serif" font-size="18" fill="#f2e6d0">A</text>
</svg>
"""

_CSS = """
:root {
  --bg: #090807;
  --paper: #f2e6d0;
  --muted: #9a8b72;
  --amber: #e09b3d;
  --line: #2a251c;
  --line-2: #3d3628;
  --card: #12100c;
  --ink: #1a140c;
  --serif: "Fraunces", "Iowan Old Style", "Palatino Linotype", Palatino, "Times New Roman", serif;
  --mono: "IBM Plex Mono", ui-monospace, "Cascadia Code", "SF Mono", Menlo, Consolas, monospace;
}
* { box-sizing: border-box; }
html { color-scheme: dark; }
html, body { margin: 0; padding: 0; }
body {
  font-family: var(--serif);
  font-size: 1.12rem;
  line-height: 1.55;
  background: var(--bg);
  color: var(--paper);
  min-height: 100vh;
  background-image:
    radial-gradient(1100px 520px at 8% -8%, rgba(224,155,61,.11), transparent 55%),
    radial-gradient(900px 480px at 100% 0%, rgba(224,155,61,.05), transparent 46%);
}
::selection { background: var(--amber); color: var(--ink); }
a { color: var(--amber); text-decoration-thickness: 1px; text-underline-offset: 0.18em; }
a:hover { color: var(--paper); }
.grain {
  position: fixed; inset: 0; pointer-events: none; z-index: 50;
  opacity: .07; mix-blend-mode: overlay;
  background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='180' height='180'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='.85' numOctaves='4' stitchTiles='stitch'/></filter><rect width='100%' height='100%' filter='url(%23n)'/></svg>");
}
.sprocket {
  display: none;
}
.wrap {
  width: min(72rem, calc(100% - 2.4rem));
  margin: 0 auto;
}
.nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 1.05rem 0 0.9rem;
  position: sticky;
  top: 0;
  z-index: 20;
  background: rgba(9, 8, 7, 0.92);
  backdrop-filter: blur(12px);
}
.brand {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  color: var(--paper);
  text-decoration: none;
  font-size: 1.2rem;
  letter-spacing: -0.03em;
}
.brand img { width: 28px; height: 28px; display: block; }
.nav-links {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: flex-end;
  gap: 0.35rem 1.15rem;
  font-family: var(--mono);
  font-size: 0.7rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}
.nav-links a { color: var(--muted); text-decoration: none; }
.nav-links a:hover { color: var(--paper); }
.pulse { color: var(--amber); }
.hero {
  display: grid;
  grid-template-columns: 1.12fr 0.88fr;
  gap: 3rem;
  align-items: start;
  padding: 4.2vh 0 3.1rem;
}
.kicker {
  font-family: var(--mono);
  font-size: 0.68rem;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: var(--amber);
  margin: 0 0 1.15rem;
}
.mark {
  position: relative;
  margin: 0 0 1.35rem;
  font-size: clamp(3rem, 11vw, 7.4rem);
  font-weight: 500;
  letter-spacing: -0.054em;
  line-height: 0.86;
  font-optical-sizing: auto;
  font-variation-settings: "SOFT" 40, "WONK" 1;
}
.mark::before {
  content: "AfterImage";
  position: absolute;
  left: 0.12em;
  top: 0.055em;
  color: var(--amber);
  opacity: 0.34;
  filter: blur(0.5px);
  pointer-events: none;
  animation: drift 9s ease-in-out infinite;
}
@keyframes drift {
  0%, 100% { transform: translate(0, 0); }
  50% { transform: translate(0.045em, 0.03em); }
}
.lead {
  font-size: clamp(1.28rem, 2.3vw, 1.85rem);
  font-style: italic;
  font-weight: 400;
  line-height: 1.28;
  margin: 0 0 1.15rem;
  max-width: 18ch;
}
.deck { max-width: 38rem; margin: 0 0 1.4rem; color: var(--paper); }
.muted { color: var(--muted); }
.prices {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.55rem;
  margin: 0 0 1.35rem;
  padding: 0;
  list-style: none;
}
.prices li {
  background: var(--card);
  border: 1px solid var(--line);
  padding: 1rem 0.95rem 1.05rem;
}
.prices strong {
  display: block;
  font-family: var(--serif);
  font-size: 1.35rem;
  font-weight: 500;
  letter-spacing: -0.03em;
}
.prices span {
  color: var(--muted);
  font-family: var(--mono);
  font-size: 0.68rem;
  letter-spacing: 0.04em;
}
.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.65rem;
  margin: 0 0 0.9rem;
}
button, .btn {
  appearance: none;
  border: 0;
  background: var(--amber);
  color: var(--ink);
  font-family: var(--mono);
  font-size: 0.9rem;
  padding: 0.72rem 1.05rem;
  cursor: pointer;
  text-decoration: none;
  display: inline-block;
  line-height: 1.2;
  transition: filter .15s ease, transform .15s ease, background .15s ease, color .15s ease;
}
button:hover, .btn:hover { filter: brightness(1.08); }
button:focus-visible, .btn:focus-visible, a:focus-visible {
  outline: 2px solid var(--amber);
  outline-offset: 3px;
}
button.secondary, .btn.secondary {
  background: transparent;
  color: var(--paper);
  border: 1px solid var(--line-2);
  filter: none;
}
button.secondary:hover, .btn.secondary:hover {
  border-color: var(--amber);
  color: var(--amber);
}
button:disabled { opacity: 0.55; cursor: wait; }
.tiny {
  font-family: var(--mono);
  font-size: 0.75rem;
  color: var(--muted);
  margin: 0;
}
.easel {
  position: relative;
  margin-top: 2.8rem;
}
.carrier {
  background: #0c0b09;
  border: 1px solid var(--line-2);
  padding: 0.9rem 0.95rem 1.15rem;
  box-shadow: 0 28px 70px rgba(0,0,0,.42);
  transform: rotate(-1.1deg);
  transition: transform .2s ease;
}
.carrier:hover { transform: rotate(0deg); }
.carrier > p {
  font-family: var(--mono);
  font-size: 0.62rem;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--muted);
  margin: 0 0 0.75rem;
}
.print {
  background: var(--card);
  border: 1px solid var(--line);
  padding: 1.05rem 1.1rem 1.15rem;
}
.print header {
  display: flex;
  justify-content: space-between;
  gap: 0.8rem;
  font-family: var(--mono);
  font-size: 0.64rem;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--muted);
  margin-bottom: 0.75rem;
}
.tag {
  color: var(--amber);
}
.kv {
  display: grid;
  grid-template-columns: 6.4rem 1fr;
  gap: 0.35rem 0.7rem;
  font-family: var(--mono);
  font-size: 0.74rem;
  line-height: 1.5;
  margin: 0;
}
.kv dt { color: var(--muted); }
.kv dd { margin: 0; color: var(--paper); overflow-wrap: break-word; word-break: normal; }
.band {
  border-top: 1px solid var(--line);
  padding: 2.8rem 0;
}
.band-head {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: baseline;
  margin-bottom: 1.6rem;
}
.band-head h2 {
  margin: 0;
  font-size: clamp(1.8rem, 3vw, 2.4rem);
  font-weight: 500;
  letter-spacing: -0.035em;
  line-height: 1.1;
}
.steps {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1.2rem;
  margin: 0;
  padding: 0;
  list-style: none;
  counter-reset: step;
}
.steps li {
  border-top: 1px solid var(--line-2);
  padding-top: 1rem;
  counter-increment: step;
}
.steps li::before {
  content: counter(step, decimal-leading-zero);
  display: block;
  font-family: var(--mono);
  font-size: 0.72rem;
  letter-spacing: 0.16em;
  color: var(--amber);
  margin-bottom: 0.55rem;
}
.steps h3 {
  margin: 0 0 0.4rem;
  font-size: 1.2rem;
  font-weight: 500;
  letter-spacing: -0.02em;
}
.steps p { margin: 0; color: var(--muted); font-size: 1rem; }
.packs {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.75rem;
}
.pack {
  background: var(--card);
  border: 1px solid var(--line);
  padding: 1.3rem 1.35rem 1.4rem;
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
}
.pack.featured { border-color: #5c4524; box-shadow: inset 0 0 0 1px rgba(224,155,61,.16); }
.pack .who {
  font-family: var(--mono);
  font-size: 0.68rem;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--muted);
}
.pack strong {
  font-size: 2.6rem;
  font-weight: 500;
  letter-spacing: -0.04em;
  line-height: 1;
}
.pack p { margin: 0 0 0.5rem; color: var(--muted); font-size: 0.98rem; }
.pack button, .pack .btn { align-self: flex-start; margin-top: auto; }
.library {
  display: grid;
  grid-template-columns: 1.1fr 0.9fr;
  gap: 2.4rem;
  align-items: end;
}
.big {
  font-size: clamp(4.2rem, 12vw, 8rem);
  font-weight: 500;
  letter-spacing: -0.06em;
  line-height: 0.85;
  margin: 0 0 0.6rem;
  font-variant-numeric: lining-nums;
  font-variation-settings: "SOFT" 30, "WONK" 1;
}
.meter {
  height: 3px;
  background: var(--line);
  margin: 1.1rem 0 0.7rem;
}
.meter > span {
  display: block;
  height: 100%;
  background: var(--amber);
}
.meta-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem 1.4rem;
  margin: 0;
}
.meta-grid div {
  border-top: 1px solid var(--line);
  padding-top: 0.7rem;
}
.meta-grid dt {
  font-family: var(--mono);
  font-size: 0.66rem;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--muted);
}
.meta-grid dd { margin: 0.25rem 0 0; font-size: 1.15rem; }
.term {
  border: 1px solid var(--line-2);
  background: #0e0c09;
  overflow: hidden;
}
.term-bar {
  display: flex;
  align-items: center;
  gap: 0.8rem;
  padding: 0.55rem 0.7rem;
  border-bottom: 1px solid var(--line);
  background: #14110d;
}
.dots {
  width: 10px; height: 10px; border-radius: 50%;
  background: var(--amber);
  box-shadow: 16px 0 0 #5a4a32, 32px 0 0 #2c2820;
  margin-right: 2.2rem;
  flex: 0 0 10px;
}
.tabs { display: flex; flex-wrap: wrap; gap: 0.2rem; flex: 1; }
.tabs button {
  background: transparent;
  color: var(--muted);
  border: 0;
  padding: 0.4rem 0.65rem;
  font-size: 0.72rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
.tabs button.on {
  color: var(--amber);
  background: #1c1812;
}
.term-bar > button[data-copy] {
  background: transparent;
  color: var(--muted);
  border: 1px solid var(--line);
  padding: 0.35rem 0.6rem;
  font-size: 0.7rem;
}
.term pre {
  margin: 0;
  padding: 1rem 1.1rem 1.15rem;
  overflow-x: auto;
  font-family: var(--mono);
  font-size: 0.78rem;
  line-height: 1.5;
  color: #d8cbb3;
  display: none;
}
.term pre.on { display: block; }
.nav-links a[aria-current="page"] { color: var(--paper); }
.docs-hero { grid-template-columns: 1fr; padding-bottom: 1.4rem; }
.docs-hero .lead { max-width: 22ch; }
.spec { padding-top: 0.4rem; padding-bottom: 3.4rem; }
#keybox {
  margin: 1rem 0 0.4rem;
  padding: 1.05rem 1.1rem 1.15rem;
  border: 1px solid var(--amber);
  background: var(--card);
}
#keybox code, #saved-key {
  display: block;
  font-family: var(--mono);
  font-size: 0.85rem;
  word-break: break-all;
  margin: 0.5rem 0 0.9rem;
  color: var(--paper);
}
.warn { color: var(--amber); margin: 0; }
.paid {
  max-width: 38rem;
  padding: 14vh 0 4rem;
}
.paid .mark { font-size: clamp(2.6rem, 8vw, 5rem); }
.paid.bad .lead { color: var(--amber); }
footer.site {
  border-top: 1px solid var(--line);
  padding: 2.2rem 0 3rem;
  color: var(--muted);
  font-size: 0.98rem;
}
.foot-row {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 1rem;
  margin-top: 1.1rem;
  font-family: var(--mono);
  font-size: 0.72rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
.noscript { color: var(--muted); font-size: 0.95rem; }
@media (min-width: 960px) {
  .sprocket {
    display: block;
    position: fixed;
    top: 0; left: 0; bottom: 0;
    width: 2.15rem;
    z-index: 40;
    pointer-events: none;
    background:
      radial-gradient(circle, #2c261c 2.15px, transparent 2.4px) center 0 / 2.15rem 1.15rem,
      #120f0c;
    border-right: 1px solid var(--line);
  }
  body { padding-left: 2.15rem; }
}
@media (max-width: 900px) {
  .hero, .library { grid-template-columns: 1fr; }
  .easel { margin-top: 1.2rem; }
  .carrier { transform: none; }
}
@media (max-width: 640px) {
  .prices, .steps, .packs, .meta-grid { grid-template-columns: 1fr; }
  .nav { align-items: flex-start; }
  .hero { padding-top: 2.2rem; }
  .term pre { font-size: 0.7rem; }
  .dots { display: none; }
}
@media (prefers-reduced-motion: reduce) {
  .mark::before { animation: none; filter: none; }
  button, .btn, .carrier { transition: none; }
  .carrier:hover { transform: rotate(-1.1deg); }
}
"""

_SWAGGER_CSS = """
.swagger-ui { font-family: var(--serif); color: var(--paper); background: transparent; }
.swagger-ui .topbar, .swagger-ui .information-container { display: none; }
.swagger-ui .wrapper { padding: 0; max-width: none; }
.swagger-ui .scheme-container {
  background: var(--card);
  box-shadow: none;
  border: 1px solid var(--line);
  margin: 0 0 1.2rem;
  padding: 1rem 1.1rem;
}
.swagger-ui .filter-container { padding: 0 0 1rem; }
.swagger-ui .operation-filter-input {
  background: #0c0b09;
  color: var(--paper);
  border: 1px solid var(--line-2);
  border-radius: 0;
  font-family: var(--mono);
}
.swagger-ui .opblock-tag {
  color: var(--paper);
  border-bottom: 1px solid var(--line);
  font-family: var(--serif);
  font-size: 1.2rem;
  font-weight: 500;
}
.swagger-ui .opblock-tag small { color: var(--muted); font-family: var(--mono); }
.swagger-ui .opblock {
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 0;
  box-shadow: none;
  margin: 0 0 0.55rem;
}
.swagger-ui .opblock .opblock-summary { border: 0; padding: 0.5rem 0.65rem; }
.swagger-ui .opblock-summary-method {
  font-family: var(--mono);
  font-weight: 500;
  min-width: 4.4rem;
  border-radius: 0;
  font-size: 0.68rem;
  letter-spacing: 0.08em;
}
.swagger-ui .opblock-summary-path, .swagger-ui .opblock-summary-path__deprecated {
  color: var(--paper);
  font-family: var(--mono);
  font-size: 0.86rem;
}
.swagger-ui .opblock-summary-description { color: var(--muted); }
.swagger-ui .opblock-body { background: transparent; }
.swagger-ui .opblock-section-header {
  background: #14110d;
  box-shadow: none;
  border: 0;
  border-radius: 0;
}
.swagger-ui .opblock-section-header h4, .swagger-ui .opblock-title,
.swagger-ui .tab li, .swagger-ui .response-col_status,
.swagger-ui .response-col_links, .swagger-ui .parameter__name,
.swagger-ui table thead tr td, .swagger-ui table thead tr th,
.swagger-ui .response-col_description, .swagger-ui label,
.swagger-ui .model, .swagger-ui .model-title, .swagger-ui .prop-type {
  color: var(--paper);
}
.swagger-ui .parameter__type, .swagger-ui .parameter__in,
.swagger-ui .parameter__empty_value_toggle, .swagger-ui .opblock-description-wrapper p,
.swagger-ui .opblock-external-docs-wrapper, .swagger-ui .renderedMarkdown p {
  color: var(--muted);
}
.swagger-ui input[type=text], .swagger-ui input[type=password],
.swagger-ui input[type=search], .swagger-ui textarea, .swagger-ui select {
  background: #0c0b09;
  color: var(--paper);
  border: 1px solid var(--line-2);
  border-radius: 0;
  font-family: var(--mono);
  box-shadow: none;
}
.swagger-ui .model-box, .swagger-ui section.models {
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 0;
}
.swagger-ui section.models h4 { color: var(--paper); }
.swagger-ui .highlight-code, .swagger-ui .microlight,
.swagger-ui .opblock-body pre {
  background: #0e0c09 !important;
  color: #d8cbb3 !important;
  border-radius: 0;
  font-family: var(--mono);
}
.swagger-ui button {
  background: transparent;
  color: var(--paper);
  border: 1px solid var(--line-2);
  border-radius: 0;
  box-shadow: none;
  font-family: var(--mono);
  font-size: 0.78rem;
  padding: 0.4rem 0.7rem;
  filter: none;
  text-transform: none;
  letter-spacing: 0.04em;
}
.swagger-ui button:hover { filter: none; border-color: var(--amber); color: var(--amber); }
.swagger-ui .btn.execute, .swagger-ui .btn.authorize {
  background: var(--amber);
  color: var(--ink);
  border-color: var(--amber);
}
.swagger-ui .btn.execute:hover, .swagger-ui .btn.authorize:hover {
  color: var(--ink);
  filter: brightness(1.08);
}
.swagger-ui .authorization__btn, .swagger-ui .expand-operation,
.swagger-ui button.expand-methods {
  background: transparent;
  border: 0;
  padding: 0.15rem;
  color: var(--muted);
}
.swagger-ui .copy-to-clipboard { background: var(--card); border: 1px solid var(--line); }
.swagger-ui .dialog-ux { z-index: 60; }
.swagger-ui .dialog-ux .modal-ux {
  background: var(--card);
  border: 1px solid var(--line-2);
  border-radius: 0;
  color: var(--paper);
  box-shadow: 0 28px 70px rgba(0,0,0,.42);
}
.swagger-ui .dialog-ux .modal-ux-header { border-bottom: 1px solid var(--line); }
.swagger-ui .dialog-ux .modal-ux-header h3,
.swagger-ui .dialog-ux .modal-ux-content h4,
.swagger-ui .auth-container { color: var(--paper); }
.swagger-ui .auth-btn-wrapper .btn-done { background: var(--amber); color: var(--ink); border-color: var(--amber); }
.swagger-ui svg { fill: var(--paper); }
.swagger-ui .arrow { fill: var(--muted); }
.swagger-ui a { color: var(--amber); }
"""


def prefers_html(accept: str) -> bool:
    accept = (accept or "").lower()
    html_at = accept.find("text/html")
    if html_at < 0:
        return False
    json_at = accept.find("application/json")
    return json_at < 0 or html_at < json_at


def _as_int(value: object) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def freshness_pct(*, indexed: int, oldest_age_s: object, ttl_s: int) -> int:
    """Remaining life of the oldest copy, 0–100. Empty library is 0, not 0/cap."""
    age = _as_int(oldest_age_s)
    if indexed <= 0 or age is None or ttl_s <= 0:
        return 0
    return min(100, max(0, round(100 * (1 - age / ttl_s))))


def fresh_label(*, indexed: int, oldest_age_s: object, ttl_s: int, ttl_days: int) -> str:
    age = _as_int(oldest_age_s)
    if indexed <= 0 or age is None or ttl_s <= 0:
        return "empty"
    left = max(0.0, (ttl_s - age) / 86400)
    if left >= 10 or abs(left - round(left)) < 0.05:
        left_s = str(int(round(left)))
    else:
        left_s = f"{left:.1f}"
    return f"oldest has {left_s} of {ttl_days} days left"


def _fill(template: str, **values: str) -> str:
    html = template
    for key, value in values.items():
        html = html.replace("{{" + key + "}}", value)
    return html


def _head(*, title: str, description: str, base: str, path: str = "/", extra: str = "") -> str:
    url = f"{base}{path}"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <link rel="icon" href="{base}/icon.svg" type="image/svg+xml">
  <link rel="canonical" href="{url}">
  <meta name="description" content="{description}">
  <meta name="theme-color" content="#090807">
  <meta property="og:title" content="AfterImage">
  <meta property="og:description" content="{description}">
  <meta property="og:type" content="website">
  <meta property="og:url" content="{url}">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght,SOFT,WONK@9..144,400..600,0..100,0..1&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
  <style>{_CSS}</style>
  {extra}
</head>
"""


def landing_html(settings: Settings, stats: dict | None = None) -> str:
    base = escape(settings.public_url.rstrip("/"))
    stats = stats or {}
    indexed = int(stats.get("indexed") or 0)
    max_pages = settings.max_snapshots
    ttl_s = settings.snapshot_ttl_s
    ttl_days = settings.snapshot_ttl_days
    oldest_age_s = stats.get("oldest_age_s")
    fill = freshness_pct(indexed=indexed, oldest_age_s=oldest_age_s, ttl_s=ttl_s)
    oldest = escape(str(stats.get("oldest_fetched_at") or "—"))
    title = escape("AfterImage — fresh copies of the pages models get wrong")
    description = escape(
        "Fresh copies of the pages models get wrong: model catalogs, provider prices, "
        "dated protocol specs, changelogs, deprecations, and rate limits. "
        "Timestamp plus sha256. Humans buy credits; agents send a key."
    )
    return _fill(
        _LANDING,
        HEAD=_head(title=title, description=description, base=base),
        BASE=base,
        SEARCH=SEARCH_USDC,
        HIT=HIT_USDC,
        MISS=MISS_USDC,
        INDEXED=f"{indexed:,}",
        MAX_PAGES=f"{max_pages:,}",
        MAX_CHARS=f"{settings.max_text_chars:,}",
        TTL_DAYS=str(ttl_days),
        FILL=str(fill),
        FRESH_LABEL=escape(
            fresh_label(
                indexed=indexed,
                oldest_age_s=oldest_age_s,
                ttl_s=ttl_s,
                ttl_days=ttl_days,
            )
        ),
        OLDEST=oldest,
        REMOVAL=escape(settings.removal_email),
    )


def paid_html(settings: Settings, payload: dict, *, status: int) -> str:
    base = escape(settings.public_url.rstrip("/"))
    credited = bool(payload.get("credited"))
    description = escape("AfterImage credit status after Stripe checkout.")
    if credited:
        pack = escape(str(payload.get("pack") or "credits"))
        usd = payload.get("credits_usd")
        usd_s = f"${usd:g}" if isinstance(usd, (int, float)) else "credits"
        already = bool(payload.get("already"))
        title = "Already credited." if already else "Credits landed."
        lead = (
            f"The {pack} pack ({usd_s}) is on the API key you saved before paying. "
            "Stripe will not show that key again."
        )
    else:
        title = "Payment did not finish."
        reason = payload.get("error") or payload.get("reason") or "The session is not paid."
        lead = escape(str(reason))
    page_title = escape(f"AfterImage — {title}")
    return _fill(
        _PAID,
        HEAD=_head(title=page_title, description=description, base=base),
        BASE=base,
        TITLE=escape(title),
        LEAD=lead,
        STATE="ok" if status == 200 else "bad",
    )


def docs_html(settings: Settings, stats: dict | None = None) -> str:
    base = escape(settings.public_url.rstrip("/"))
    stats = stats or {}
    indexed = int(stats.get("indexed") or 0)
    title = escape("AfterImage — docs")
    description = escape(
        "HTTP, MCP, and x402 for AfterImage. Authorization Bearer ak_live_…. "
        "HTTP 402 is unpaid: missing_key, unknown_key, unfunded_key, or insufficient_credits."
    )
    extra = (
        '<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css">\n'
        f"  <style>{_SWAGGER_CSS}</style>"
    )
    return _fill(
        _DOCS,
        HEAD=_head(
            title=title,
            description=description,
            base=base,
            path="/docs",
            extra=extra,
        ),
        BASE=base,
        SEARCH=SEARCH_USDC,
        HIT=HIT_USDC,
        MISS=MISS_USDC,
        INDEXED=f"{indexed:,}",
        MAX_PAGES=f"{settings.max_snapshots:,}",
        MAX_CHARS=f"{settings.max_text_chars:,}",
        TTL_DAYS=str(settings.snapshot_ttl_days),
        REMOVAL=escape(settings.removal_email),
    )


_LANDING = """{{HEAD}}
<body>
  <div class="grain" aria-hidden="true"></div>
  <div class="sprocket" aria-hidden="true"></div>
  <div class="wrap">
    <header class="nav">
      <a class="brand" href="{{BASE}}/"><img src="{{BASE}}/icon.svg" alt="">AfterImage</a>
      <nav class="nav-links">
        <span class="pulse"><span data-indexed>{{INDEXED}}</span> in the library</span>
        <a href="{{BASE}}/llms.txt">llms.txt</a>
        <a href="{{BASE}}/docs">Docs</a>
        <a href="{{BASE}}/openapi.json">OpenAPI</a>
        <a href="{{BASE}}/mcp/server-card">MCP</a>
      </nav>
    </header>
    <main>
      <section class="hero">
        <div>
          <p class="kicker">Pages models get wrong</p>
          <h1 class="mark">AfterImage</h1>
          <p class="lead">Fresh copies of the pages models get wrong.</p>
          <p class="deck">Model catalogs, provider prices, dated protocol specs, changelogs, deprecations, rate limits, current package versions. If another agent already fetched a page, yours reuses that copy — timestamp plus sha256 of the raw bytes. Humans buy credits; agents send an API key.</p>
          <ul class="prices">
            <li><strong>${{SEARCH}}</strong><span>search stored pages</span></li>
            <li><strong>${{HIT}}</strong><span>reuse a fresh copy</span></li>
            <li><strong>${{MISS}}</strong><span>live fetch</span></li>
          </ul>
          <p class="muted">Starter is <strong>$5</strong>. Builder is <strong>$20</strong>. HTTP 402 is unpaid: missing_key, unknown_key, unfunded_key, or insufficient_credits.</p>
          <div class="actions">
            <button type="button" id="buy20" data-pack="builder">Buy $20 credits</button>
            <button type="button" class="secondary" id="buy" data-pack="starter">Buy $5</button>
            <a class="btn secondary" href="{{BASE}}/llms.txt">Agent brief (llms.txt)</a>
          </div>
          <noscript class="noscript">JavaScript is off. POST {{BASE}}/v1/billing/checkout from a terminal, then open checkout_url.</noscript>
          <p class="tiny">Or pay per call with x402 USDC on Base. Agents start at <a href="{{BASE}}/llms.txt">llms.txt</a>.</p>
        </div>
        <aside class="easel" aria-label="Example snapshot">
          <div class="carrier">
            <p>Specimen · a stored copy</p>
            <article class="print">
              <header><span>GET /v1/page</span><span class="tag">cache hit · ${{HIT}}</span></header>
              <dl class="kv">
                <dt>url</dt><dd>https://platform.openai.com/docs/pricing</dd>
                <dt>cache</dt><dd>hit</dd>
                <dt>hash</dt><dd>sha256:b7c19e0a9d44…c21f</dd>
                <dt>fetched_at</dt><dd>2026-08-29T11:02:14Z</dd>
                <dt>text</dt><dd>Input, cached input, and output are billed per 1M tokens. This is the live price table. Figures in training data lag.</dd>
              </dl>
            </article>
          </div>
        </aside>
      </section>

      <section class="band">
        <div class="band-head">
          <h2>How a copy gets reused</h2>
          <p class="tiny">Humans pay once. Agents send Authorization: Bearer ak_live_…</p>
        </div>
        <ol class="steps">
          <li>
            <h3>Buy a key</h3>
            <p>Starter is $5, builder is $20. You get the API key before Stripe — save it, then pay.</p>
          </li>
          <li>
            <h3>Search the library</h3>
            <p>GET /v1/search does not hit the live web. If indexed is 0, fetch a URL first.</p>
          </li>
          <li>
            <h3>Fetch or reuse</h3>
            <p>GET /v1/page returns readable text, not HTML, plus a sha256 and fetched_at. Hits are cheaper than a live fetch.</p>
          </li>
        </ol>
      </section>

      <section class="band">
        <div class="band-head">
          <h2>Credits</h2>
          <p class="tiny">Same key for HTTP, MCP, and balance checks.</p>
        </div>
        <div class="packs">
          <article class="pack">
            <span class="who">Starter</span>
            <strong>$5</strong>
            <p>About 1,000 searches, or 500 live fetches, or 2,500 cache hits.</p>
            <button type="button" class="secondary" data-pack="starter">Buy $5 credits</button>
          </article>
          <article class="pack featured">
            <span class="who">Builder</span>
            <strong>$20</strong>
            <p>About 4,000 searches, or 2,000 live fetches, or 10,000 cache hits.</p>
            <button type="button" data-pack="builder">Buy $20</button>
          </article>
        </div>
      </section>

      <section class="band">
        <div class="library">
          <div>
            <p class="kicker">Live library</p>
            <p class="big"><span data-indexed>{{INDEXED}}</span></p>
            <p class="muted">curated pages · cap {{MAX_PAGES}} · evicted after {{TTL_DAYS}} days.</p>
            <div class="meter" aria-hidden="true"><span id="fill" style="width:{{FILL}}%"></span></div>
            <p class="tiny"><span id="fresh-label">{{FRESH_LABEL}}</span></p>
          </div>
          <dl class="meta-grid">
            <div><dt>Per page</dt><dd>{{MAX_CHARS}} characters</dd></div>
            <div><dt>Oldest copy</dt><dd id="oldest">{{OLDEST}}</dd></div>
            <div><dt>Live size</dt><dd><a href="{{BASE}}/v1/stats">GET /v1/stats</a></dd></div>
            <div><dt>MCP</dt><dd>search_pages, get_page</dd></div>
          </dl>
        </div>
      </section>

      <section class="band">
        <div class="band-head">
          <h2>From a terminal</h2>
          <p class="tiny">Authorization header on every later call.</p>
        </div>
        <div class="term">
          <div class="term-bar">
            <span class="dots" aria-hidden="true"></span>
            <div class="tabs">
              <button type="button" class="on" data-tab="checkout">Checkout</button>
              <button type="button" data-tab="search">Search</button>
              <button type="button" data-tab="page">Page</button>
              <button type="button" data-tab="mcp">MCP</button>
            </div>
            <button type="button" data-copy>Copy</button>
          </div>
          <pre class="on" data-panel="checkout">curl -sS -X POST {{BASE}}/v1/billing/checkout \\
  -H 'content-type: application/json' \\
  -d '{"pack":"starter"}'</pre>
          <pre data-panel="search">curl -sS '{{BASE}}/v1/search?q=openai+pricing' \\
  -H "Authorization: Bearer ak_live_…"</pre>
          <pre data-panel="page">curl -sS '{{BASE}}/v1/page?url=https://platform.openai.com/docs/pricing&amp;max_age_s=900' \\
  -H "Authorization: Bearer ak_live_…"</pre>
          <pre data-panel="mcp">curl -sS -X POST {{BASE}}/mcp \\
  -H "Authorization: Bearer ak_live_…" \\
  -H 'content-type: application/json' \\
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"search_pages","arguments":{"q":"openai pricing"}}}'</pre>
        </div>
      </section>
    </main>
    <footer class="site">
      <p>Caps: {{MAX_PAGES}} pages, {{MAX_CHARS}} characters per page, evicted after {{TTL_DAYS}} days.
      Live size: GET {{BASE}}/v1/stats (free). Removal: {{REMOVAL}}.
      Agents start at <a href="{{BASE}}/llms.txt">{{BASE}}/llms.txt</a>.</p>
      <div class="foot-row">
        <span>AfterImage is a cache, not an archive.</span>
        <span>
          <a href="https://github.com/Lordkro/afterimage">GitHub</a>
          · <a href="{{BASE}}/.well-known/x402">x402</a>
          · <a href="{{BASE}}/health">health</a>
        </span>
      </div>
    </footer>
  </div>
  <script>
    async function buy(pack) {
      const buttons = document.querySelectorAll("[data-pack]");
      buttons.forEach((b) => { b.disabled = true; });
      try {
        const response = await fetch("/v1/billing/checkout", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ pack }),
        });
        const body = await response.json();
        if (!response.ok) {
          throw new Error(body.error || "checkout failed");
        }
        try { sessionStorage.setItem("afterimage_key", body.api_key); } catch (e) {}
        let box = document.getElementById("keybox");
        if (!box) {
          box = document.createElement("div");
          box.id = "keybox";
          box.setAttribute("role", "status");
          box.innerHTML = '<p class="warn">Save this key now. Stripe will not show it again.</p>'
            + '<code id="key"></code>'
            + '<div class="actions">'
            + '<button type="button" id="copy">Copy key</button>'
            + '<a class="btn" id="pay">Pay on Stripe</a>'
            + '</div>';
          const actions = document.querySelector(".actions");
          actions.after(box);
          document.getElementById("copy").addEventListener("click", async () => {
            const btn = document.getElementById("copy");
            await navigator.clipboard.writeText(document.getElementById("key").textContent);
            btn.textContent = "Copied";
            setTimeout(() => { btn.textContent = "Copy key"; }, 1600);
          });
        }
        document.getElementById("key").textContent = body.api_key;
        document.getElementById("pay").setAttribute("href", body.checkout_url);
        box.scrollIntoView({ behavior: "smooth", block: "nearest" });
      } catch (err) {
        alert(err.message || "Could not start checkout");
      } finally {
        buttons.forEach((b) => { b.disabled = false; });
      }
    }
    document.querySelectorAll("[data-pack]").forEach((btn) => {
      btn.addEventListener("click", () => buy(btn.getAttribute("data-pack")));
    });
    document.querySelectorAll("[data-tab]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const id = btn.getAttribute("data-tab");
        document.querySelectorAll("[data-tab]").forEach((b) => b.classList.toggle("on", b === btn));
        document.querySelectorAll("[data-panel]").forEach((p) => {
          p.classList.toggle("on", p.getAttribute("data-panel") === id);
        });
      });
    });
    const copyTerm = document.querySelector("[data-copy]");
    if (copyTerm) {
      copyTerm.addEventListener("click", async () => {
        const panel = document.querySelector("pre.on");
        if (!panel) return;
        await navigator.clipboard.writeText(panel.textContent);
        copyTerm.textContent = "Copied";
        setTimeout(() => { copyTerm.textContent = "Copy"; }, 1600);
      });
    }
    (async () => {
      try {
        const s = await fetch("/v1/stats").then((r) => r.json());
        const n = Number(s.indexed || 0);
        document.querySelectorAll("[data-indexed]").forEach((el) => {
          el.textContent = n.toLocaleString("en-US");
        });
        const ttl = Number(s.snapshot_ttl_s || 0);
        const age = s.oldest_age_s;
        const fill = document.getElementById("fill");
        if (fill && ttl) {
          if (age == null || n === 0) fill.style.width = "0%";
          else fill.style.width = Math.min(100, Math.max(0, 100 * (1 - Number(age) / ttl))) + "%";
        }
        const fresh = document.getElementById("fresh-label");
        if (fresh && ttl) {
          if (age == null || n === 0) {
            fresh.textContent = "empty";
          } else {
            const days = Math.max(0, (ttl - Number(age)) / 86400);
            const ttlDays = Math.max(1, Math.round(ttl / 86400));
            const left = (days >= 10 || Math.abs(days - Math.round(days)) < 0.05)
              ? String(Math.round(days))
              : days.toFixed(1);
            fresh.textContent = "oldest has " + left + " of " + ttlDays + " days left";
          }
        }
        const oldest = document.getElementById("oldest");
        if (oldest && s.oldest_fetched_at) oldest.textContent = s.oldest_fetched_at;
      } catch (e) {}
    })();
  </script>
</body>
</html>
"""

_PAID = """{{HEAD}}
<body>
  <div class="grain" aria-hidden="true"></div>
  <div class="sprocket" aria-hidden="true"></div>
  <div class="wrap">
    <header class="nav">
      <a class="brand" href="{{BASE}}/"><img src="{{BASE}}/icon.svg" alt="">AfterImage</a>
      <nav class="nav-links">
        <a href="{{BASE}}/llms.txt">llms.txt</a>
        <a href="{{BASE}}/">Home</a>
      </nav>
    </header>
    <main class="paid {{STATE}}">
      <p class="kicker">Stripe checkout</p>
      <h1 class="mark">AfterImage</h1>
      <p class="lead">{{TITLE}}</p>
      <p class="deck">{{LEAD}}</p>
      <div id="saved" hidden>
        <p class="warn">This browser still has the key from checkout. Copy it again if you need to.</p>
        <code id="saved-key"></code>
        <div class="actions">
          <button type="button" id="copy-saved">Copy key</button>
        </div>
      </div>
      <div class="actions">
        <a class="btn" href="{{BASE}}/">Back to AfterImage</a>
        <a class="btn secondary" href="{{BASE}}/llms.txt">Agent brief (llms.txt)</a>
      </div>
    </main>
  </div>
  <script>
    try {
      const key = sessionStorage.getItem("afterimage_key");
      if (key) {
        const box = document.getElementById("saved");
        const code = document.getElementById("saved-key");
        box.hidden = false;
        code.textContent = key;
        document.getElementById("copy-saved").addEventListener("click", async () => {
          await navigator.clipboard.writeText(key);
          const btn = document.getElementById("copy-saved");
          btn.textContent = "Copied";
          setTimeout(() => { btn.textContent = "Copy key"; }, 1600);
        });
      }
    } catch (e) {}
  </script>
</body>
</html>
"""

_DOCS = """{{HEAD}}
<body>
  <div class="grain" aria-hidden="true"></div>
  <div class="sprocket" aria-hidden="true"></div>
  <div class="wrap">
    <header class="nav">
      <a class="brand" href="{{BASE}}/"><img src="{{BASE}}/icon.svg" alt="">AfterImage</a>
      <nav class="nav-links">
        <span class="pulse"><span data-indexed>{{INDEXED}}</span> in the library</span>
        <a href="{{BASE}}/llms.txt">llms.txt</a>
        <a href="{{BASE}}/docs" aria-current="page">Docs</a>
        <a href="{{BASE}}/openapi.json">OpenAPI</a>
        <a href="{{BASE}}/mcp/server-card">MCP</a>
      </nav>
    </header>
    <main>
      <section class="hero docs-hero">
        <div>
          <p class="kicker">HTTP, MCP, x402</p>
          <h1 class="mark">AfterImage</h1>
          <p class="lead">The HTTP surface.</p>
          <p class="deck">Authorization: Bearer ak_live_…. HTTP 402 is unpaid: missing_key, unknown_key, unfunded_key, or insufficient_credits. Agents start at <a href="{{BASE}}/llms.txt">llms.txt</a>.</p>
          <ul class="prices">
            <li><strong>${{SEARCH}}</strong><span>search stored pages</span></li>
            <li><strong>${{HIT}}</strong><span>reuse a fresh copy</span></li>
            <li><strong>${{MISS}}</strong><span>live fetch</span></li>
          </ul>
          <div class="actions">
            <a class="btn" href="{{BASE}}/openapi.json">OpenAPI JSON</a>
            <a class="btn secondary" href="{{BASE}}/llms.txt">Agent brief (llms.txt)</a>
          </div>
        </div>
      </section>
      <section class="band spec">
        <noscript class="noscript">JavaScript is off. The spec is GET {{BASE}}/openapi.json.</noscript>
        <div id="swagger-ui"></div>
      </section>
    </main>
    <footer class="site">
      <p>Caps: {{MAX_PAGES}} pages, {{MAX_CHARS}} characters per page, evicted after {{TTL_DAYS}} days.
      Live size: GET {{BASE}}/v1/stats (free). Removal: {{REMOVAL}}.
      Agents start at <a href="{{BASE}}/llms.txt">{{BASE}}/llms.txt</a>.</p>
      <div class="foot-row">
        <span>AfterImage is a cache, not an archive.</span>
        <span>
          <a href="https://github.com/Lordkro/afterimage">GitHub</a>
          · <a href="{{BASE}}/.well-known/x402">x402</a>
          · <a href="{{BASE}}/health">health</a>
        </span>
      </div>
    </footer>
  </div>
  <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
  <script>
    window.ui = SwaggerUIBundle({
      url: "/openapi.json",
      dom_id: "#swagger-ui",
      deepLinking: true,
      persistAuthorization: true,
      displayRequestDuration: true,
      docExpansion: "list",
      defaultModelsExpandDepth: 0,
      filter: true,
      tryItOutEnabled: true,
      layout: "BaseLayout",
      presets: [SwaggerUIBundle.presets.apis]
    });
    (async () => {
      try {
        const s = await fetch("/v1/stats").then((r) => r.json());
        const n = Number(s.indexed || 0);
        document.querySelectorAll("[data-indexed]").forEach((el) => {
          el.textContent = n.toLocaleString("en-US");
        });
      } catch (e) {}
    })();
  </script>
</body>
</html>
"""
