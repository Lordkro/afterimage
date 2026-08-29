from __future__ import annotations

from html import escape

from afterimage.pricing import HIT_USDC, MISS_USDC, SEARCH_USDC
from afterimage.settings import Settings


def landing_html(settings: Settings) -> str:
    base = escape(settings.public_url.rstrip("/"))
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AfterImage — shared copies of the public web for AI agents</title>
  <meta name="description" content="If another agent already fetched a page, reuse that copy instead of scraping again. Timestamp plus sha256. Humans buy credits; agents send a key.">
  <style>
    :root {{
      --bg: #0e0d0b;
      --paper: #efe6d6;
      --muted: #b5a88f;
      --amber: #d89a4a;
      --line: #2c2820;
      --card: #16140f;
      --sans: "Iowan Old Style", "Palatino Linotype", Palatino, "Times New Roman", serif;
      --mono: ui-monospace, "Cascadia Code", "SF Mono", Menlo, Consolas, monospace;
    }}
    * {{ box-sizing: border-box; }}
    html, body {{ margin: 0; padding: 0; background: var(--bg); color: var(--paper); }}
    body {{
      font-family: var(--sans);
      font-size: 1.125rem;
      line-height: 1.5;
      min-height: 100vh;
    }}
    main {{
      max-width: 40rem;
      margin: 0 auto;
      padding: 12vh 1.5rem 4rem;
    }}
    .mark {{
      position: relative;
      margin: 0 0 1.25rem;
      font-size: clamp(2.75rem, 9vw, 5.25rem);
      font-weight: 500;
      letter-spacing: -0.045em;
      line-height: 0.92;
    }}
    .mark::before {{
      content: "AfterImage";
      position: absolute;
      left: 0.14em;
      top: 0.07em;
      color: var(--amber);
      opacity: 0.32;
      filter: blur(0.4px);
      pointer-events: none;
    }}
    p.lead {{ font-size: 1.2rem; margin: 0 0 1.5rem; }}
    p {{ margin: 0 0 1rem; color: var(--paper); }}
    .muted {{ color: var(--muted); }}
    a {{ color: var(--amber); }}
    a:hover {{ color: var(--paper); }}
    .prices {{
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 0.6rem;
      margin: 1.5rem 0;
      padding: 0;
      list-style: none;
    }}
    .prices li {{
      background: var(--card);
      border: 1px solid var(--line);
      padding: 0.85rem 0.9rem;
    }}
    .prices strong {{ display: block; font-size: 1.15rem; }}
    .prices span {{ color: var(--muted); font-size: 0.85rem; }}
    .actions {{
      display: flex;
      flex-wrap: wrap;
      gap: 0.75rem;
      margin: 1.5rem 0;
    }}
    button, .btn {{
      appearance: none;
      border: 0;
      background: var(--amber);
      color: #1a140c;
      font-family: inherit;
      font-size: 1rem;
      padding: 0.7rem 1.1rem;
      cursor: pointer;
      text-decoration: none;
      display: inline-block;
    }}
    button.secondary, .btn.secondary {{
      background: transparent;
      color: var(--paper);
      border: 1px solid var(--line);
    }}
    button:hover, .btn:hover {{ filter: brightness(1.08); }}
    button:disabled {{ opacity: 0.6; cursor: wait; }}
    pre {{
      background: var(--card);
      border: 1px solid var(--line);
      padding: 0.9rem 1rem;
      overflow-x: auto;
      font-family: var(--mono);
      font-size: 0.78rem;
      line-height: 1.45;
      color: #d8cbb3;
    }}
    #keybox {{
      margin: 1rem 0 1.5rem;
      padding: 1rem;
      border: 1px solid var(--amber);
      background: var(--card);
    }}
    #keybox code {{
      display: block;
      font-family: var(--mono);
      font-size: 0.85rem;
      word-break: break-all;
      margin: 0.5rem 0 0.9rem;
    }}
    .warn {{ color: var(--amber); }}
    footer {{
      margin-top: 2.5rem;
      color: var(--muted);
      font-size: 0.95rem;
    }}
    @media (max-width: 640px) {{
      main {{ padding-top: 8vh; }}
      .prices {{ grid-template-columns: 1fr; }}
      pre {{ font-size: 0.7rem; }}
    }}
    @media (prefers-reduced-motion: reduce) {{
      .mark::before {{ filter: none; }}
    }}
  </style>
</head>
<body>
  <main>
    <h1 class="mark">AfterImage</h1>
    <p class="lead">A shared copy of the public web for AI agents.</p>
    <p>If another agent already fetched a page, yours can reuse that copy — timestamp plus sha256 of the raw bytes — instead of scraping again. Search the copies. Humans buy credits; agents send an API key.</p>
    <ul class="prices">
      <li><strong>${SEARCH_USDC}</strong><span>search stored pages</span></li>
      <li><strong>${HIT_USDC}</strong><span>reuse a fresh copy</span></li>
      <li><strong>${MISS_USDC}</strong><span>live fetch</span></li>
    </ul>
    <p class="muted">Starter is <strong>$5</strong>. Builder is <strong>$20</strong>. HTTP 402 means the key is missing or empty.</p>
    <div class="actions">
      <button type="button" id="buy" data-pack="starter">Buy $5 credits</button>
      <button type="button" class="secondary" id="buy20" data-pack="builder">Buy $20</button>
      <a class="btn secondary" href="/llms.txt">Agent brief (llms.txt)</a>
    </div>
    <p class="muted">Or from a terminal:</p>
    <pre>curl -sS -X POST {base}/v1/billing/checkout \\
  -H 'content-type: application/json' \\
  -d '{{"pack":"starter"}}'

curl -sS '{base}/v1/search?q=fastapi+background+tasks' \\
  -H "Authorization: Bearer ak_live_…"

curl -sS '{base}/v1/page?url=https://example.com/&amp;max_age_s=900' \\
  -H "Authorization: Bearer ak_live_…"</pre>
    <footer>
      Caps: {settings.max_snapshots:,} pages, {settings.max_text_chars:,} characters per page, evicted after {settings.snapshot_ttl_days} days.
      Live size: GET {base}/v1/stats (free). Removal: {escape(settings.removal_email)}.
      Agents start at <a href="{base}/llms.txt">{base}/llms.txt</a>.
    </footer>
  </main>
  <script>
    async function buy(pack) {{
      const buttons = document.querySelectorAll("[data-pack]");
      buttons.forEach((b) => {{ b.disabled = true; }});
      try {{
        const response = await fetch("/v1/billing/checkout", {{
          method: "POST",
          headers: {{ "content-type": "application/json" }},
          body: JSON.stringify({{ pack }}),
        }});
        const body = await response.json();
        if (!response.ok) {{
          throw new Error(body.error || "checkout failed");
        }}
        let box = document.getElementById("keybox");
        if (!box) {{
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
          document.getElementById("copy").addEventListener("click", async () => {{
            await navigator.clipboard.writeText(document.getElementById("key").textContent);
          }});
        }}
        document.getElementById("key").textContent = body.api_key;
        document.getElementById("pay").setAttribute("href", body.checkout_url);
        box.scrollIntoView({{ behavior: "smooth", block: "nearest" }});
      }} catch (err) {{
        alert(err.message || "Could not start checkout");
      }} finally {{
        buttons.forEach((b) => {{ b.disabled = false; }});
      }}
    }}
    document.getElementById("buy").addEventListener("click", () => buy("starter"));
    document.getElementById("buy20").addEventListener("click", () => buy("builder"));
  </script>
</body>
</html>
"""
