# Embedding the $CHILL Shareholder Report on a website

Everything here updates automatically once a day (a GitHub Action regenerates it
and commits to `main`). Your site pulls straight from the repo via the jsDelivr
CDN — **no backend, no API key, CORS-enabled.** Pick whichever level of effort
you want.

> Note on freshness: jsDelivr caches `@main` for up to ~12h, which is fine for a
> once-a-day report. If you ever need it instant, swap `@main` for a commit hash,
> or hit the GitHub raw URL instead (`https://raw.githubusercontent.com/mavrkofficial/nflx-n-chill/main/daily-holder-report/...`).

---

## Option A — just show the card (1 line, easiest)

The pre-rendered image, always the latest:

```html
<img src="https://cdn.jsdelivr.net/gh/mavrkofficial/nflx-n-chill@main/daily-holder-report/shareholder-card.png"
     alt="$CHILL Daily Shareholder Report" style="max-width:100%;border-radius:12px" />
```

---

## Option B — live JSON feed (build your own styled widget)

Machine-readable data at:

```
https://cdn.jsdelivr.net/gh/mavrkofficial/nflx-n-chill@main/daily-holder-report/latest.json
```

Shape (numbers, not strings):

```json
{
  "updated": "2026-07-21 20:50 UTC",
  "nflx_controlled": 63.43,
  "nflx_in_lp": 56.85,
  "reflections_nflx": 6.57,
  "usd_controlled": 4347.12,
  "goal_nflx": 2120000000,
  "progress_pct_to_majority": 0.0000030,
  "stake_pct_of_netflix": 0.0000015,
  "remaining_nflx": 2119999936.57,
  "holders": 96,
  "market_cap_usd": 23828,
  "chill_price_usd": 0.00002383,
  "nflx_price_usd": 68.53,
  "volume_24h_usd": 8447,
  "price_change_24h_pct": 1.4,
  "card_png": "https://cdn.jsdelivr.net/gh/.../shareholder-card.png",
  "disclaimer": "Parody token. Not affiliated with or endorsed by Netflix, Inc. Not financial advice."
}
```

Fetch and render however you like:

```js
const data = await fetch(
  "https://cdn.jsdelivr.net/gh/mavrkofficial/nflx-n-chill@main/daily-holder-report/latest.json"
).then(r => r.json());

document.querySelector("#nflx-controlled").textContent =
  data.nflx_controlled.toLocaleString() + " NFLX";
document.querySelector("#progress-bar").style.width =
  Math.max(data.progress_pct_to_majority, 0.4) + "%";
```

---

## Option C — drop-in live widget (self-contained, on-brand)

Paste this anywhere in the page. It fetches the JSON and renders a branded
"takeover tracker." Restyle freely.

```html
<div id="chill-tracker" style="max-width:640px;margin:auto;background:#000;color:#fff;
     border:1px solid #1e1e1e;border-radius:16px;padding:26px 28px;
     font-family:'Bebas Neue',Oswald,Arial,sans-serif">
  <div style="display:flex;justify-content:space-between;align-items:baseline">
    <span style="color:#CF020A;font-weight:700;letter-spacing:.04em">$CHILL</span>
    <span style="color:#888;font-size:13px" id="ct-updated"></span>
  </div>
  <div style="font-size:52px;font-weight:700;margin:8px 0 2px" id="ct-controlled">—</div>
  <div style="color:#aaa;font-size:15px" id="ct-sub">NFLX controlled</div>
  <div style="height:14px;background:#1c1c1c;border-radius:8px;margin:18px 0 8px;overflow:hidden">
    <div id="ct-bar" style="height:100%;width:0.4%;background:#CF020A;border-radius:8px"></div>
  </div>
  <div style="display:flex;justify-content:space-between;color:#bbb;font-size:13px">
    <span>Goal: 2,120,000,000 NFLX (majority of Netflix)</span>
    <span id="ct-pct" style="color:#CF020A"></span>
  </div>
  <div style="color:#666;font-size:11px;margin-top:14px">
    Parody token — not affiliated with or endorsed by Netflix, Inc. Not financial advice.
  </div>
</div>
<script>
fetch("https://cdn.jsdelivr.net/gh/mavrkofficial/nflx-n-chill@main/daily-holder-report/latest.json")
  .then(r => r.json()).then(d => {
    ct_controlled.textContent = d.nflx_controlled.toLocaleString(undefined,{maximumFractionDigits:1}) + " NFLX";
    ct_sub.textContent = "NFLX controlled · ~$" + d.usd_controlled.toLocaleString() +
                         " · " + d.stake_pct_of_netflix.toFixed(7) + "% of Netflix";
    ct_bar.style.width = Math.max(d.progress_pct_to_majority, 0.4) + "%";
    ct_pct.textContent = d.progress_pct_to_majority.toFixed(6) + "%";
    ct_updated.textContent = d.updated;
  });
</script>
```

---

## Option D — history chart

`history.csv` gets one row appended per day (columns: `date, controlled_nflx,
treasury_nflx, dividends_nflx, stake_pct, progress_pct, holders, market_cap_usd,
nflx_price_usd, chill_price_usd, vol24_usd`). Feed it to Chart.js / Recharts /
Datawrapper for a "progress over time" graph:

```
https://cdn.jsdelivr.net/gh/mavrkofficial/nflx-n-chill@main/daily-holder-report/history.csv
```

---

**tl;dr for your dev:** Option A is a one-line `<img>`. Option C is a paste-and-go
live widget. Everything refreshes daily on its own.
