"""
$CHILL — Daily Shareholder Report generator.

Frames on-chain $CHILL activity as a mock corporate shareholder report, tracking
our progress toward acquiring a controlling interest in NFLX (2.12B of 4.22B
outstanding shares) via NFLX held in protocol liquidity + reflections paid to
shareholders.

Writes into OUTPUT_DIR (argv[1], default = ./out):
  README.md            the shareholder report (renders on GitHub)
  shareholder-card.png the visual summary card
  history.csv          one row per day (appended)

Deps: Pillow.  (stdlib urllib for HTTP.)
"""
import os, sys, csv, json, urllib.request
from datetime import datetime, timezone

SUBGRAPH = "https://api.goldsky.com/api/public/project_cmm7vh5xwsa8m01qmdr7w7u62/subgraphs/sentry-robinhood/1.2.0/gn"
BLOCKSCOUT = "https://robinhoodchain.blockscout.com/api/v2/tokens/{}/counters"
CHILL = "0xf699aea8a333202a7dc610abc664c213c9dc4111"
CHILL_CS = "0xF699AEA8a333202A7Dc610aBc664c213c9dc4111"
NFLX  = "0xe0444ef8bf4ed74f74fd73686e2ddf4c1c5591e8"

GOAL = 2_120_000_000              # NFLX for controlling interest (>50%)
SHARES_OUTSTANDING_NFLX = 4_220_000_000
CHILL_SUPPLY = 1_000_000_000     # fixed
UA = {"User-Agent": "chill-shareholder-report/1.0"}

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "out")
FONT_DIRS = [os.path.join(HERE, "fonts"), "C:/Windows/Fonts"]

def find_asset(*rel):
    for c in (os.path.join(HERE, "..", "branding-kit", *rel),
              os.path.join(HERE, "..", *rel),
              os.path.join(HERE, *rel)):
        if os.path.exists(c):
            return c
    return None

def http_json(url, data=None):
    req = urllib.request.Request(url, data=(json.dumps(data).encode() if data else None),
                                 headers={**UA, **({"Content-Type": "application/json"} if data else {})})
    return json.load(urllib.request.urlopen(req, timeout=40))

def gql(q):
    return http_json(SUBGRAPH, {"query": q})["data"]

def fetch():
    swaps, skip = [], 0
    while True:
        page = gql(f'{{ swaps(first:1000, skip:{skip}, orderBy:timestamp, '
                   f'where:{{token:"{CHILL}"}}) {{ isBuy amountWETH amountToken timestamp origin }} }}')["swaps"]
        swaps += page
        if len(page) < 1000:
            break
        skip += 1000
    d = gql(f'{{ token(id:"{CHILL}") {{ volumeWETH volumeToken swapCount buyCount sellCount '
            f'lastPriceUsd lastPriceWETH createdAt }} nflx: assetUsd(id:"{NFLX}") {{ usdPrice }} '
            f'days: tokenDayDatas(first:14, orderBy:date, orderDirection:desc, where:{{token:"{CHILL}"}}) '
            f'{{ date closePriceUsd volumeWETH }} _meta {{ block {{ number timestamp }} }} }}')
    try:
        holders = int(http_json(BLOCKSCOUT.format(CHILL_CS)).get("token_holders_count", 0))
        transfers = int(http_json(BLOCKSCOUT.format(CHILL_CS)).get("transfers_count", 0))
    except Exception:
        holders = transfers = None
    return swaps, d, holders, transfers

def compute():
    swaps, d, holders, transfers = fetch()
    now = int(d["_meta"]["block"]["timestamp"])
    day_ago = now - 86400

    def sums(seq):
        bi = sum(float(s["amountWETH"]) for s in seq if s["isBuy"])
        so = sum(float(s["amountWETH"]) for s in seq if not s["isBuy"])
        return bi, so

    buy_in, sell_out = sums(swaps)
    net_lp = buy_in - sell_out
    vol = float(d["token"]["volumeWETH"])
    reflections = vol * 0.01
    nflx_usd = float(d["nflx"]["usdPrice"])
    chill_usd = float(d["token"]["lastPriceUsd"])
    controlled = net_lp + reflections

    # 24h window
    w = [s for s in swaps if int(s["timestamp"]) >= day_ago]
    bi24, so24 = sums(w)
    vol24 = bi24 + so24
    net24 = bi24 - so24
    refl24 = vol24 * 0.01
    buys24 = sum(1 for s in w if s["isBuy"])
    sells24 = len(w) - buys24

    # price change 24h from day data
    days = d["days"]
    chg = None
    if len(days) >= 2 and float(days[1]["closePriceUsd"]) > 0:
        chg = (float(days[0]["closePriceUsd"]) - float(days[1]["closePriceUsd"])) / float(days[1]["closePriceUsd"]) * 100

    traders = len({s["origin"] for s in swaps})
    mcap = chill_usd * CHILL_SUPPLY

    return {
        "controlled": controlled, "net_lp": net_lp, "reflections": reflections,
        "usd_controlled": controlled * nflx_usd, "usd_treasury": net_lp * nflx_usd,
        "usd_dividends": reflections * nflx_usd,
        "stake_pct": controlled / SHARES_OUTSTANDING_NFLX * 100,
        "progress": controlled / GOAL * 100, "remaining": GOAL - controlled,
        "vol": vol, "usd_vol": vol * nflx_usd, "nflx_usd": nflx_usd, "chill_usd": chill_usd,
        "mcap": mcap, "swaps": int(d["token"]["swapCount"]),
        "buys": int(d["token"]["buyCount"]), "sells": int(d["token"]["sellCount"]),
        "traders": traders, "holders": holders, "transfers": transfers,
        "nflx_per_m": controlled / (CHILL_SUPPLY / 1_000_000),
        "div_per_m": reflections / (CHILL_SUPPLY / 1_000_000),
        "vol24": vol24, "usd_vol24": vol24 * nflx_usd, "net24": net24, "refl24": refl24,
        "swaps24": len(w), "buys24": buys24, "sells24": sells24, "chg24": chg,
        "block": int(d["_meta"]["block"]["number"]),
        "date": datetime.fromtimestamp(now, timezone.utc).strftime("%Y-%m-%d"),
        "ts": datetime.fromtimestamp(now, timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "days_live": max(1, (now - int(d["token"]["createdAt"])) // 86400),
    }

def fmt(n, d=2): return f"{n:,.{d}f}"

def markdown(m):
    chg = m["chg24"]
    chg_s = "n/a" if chg is None else (f"+{chg:.1f}%" if chg >= 0 else f"{chg:.1f}%")
    return f"""# $CHILL — Daily Shareholder Report

### Netflix and Chill · Report to Shareholders · {m['date']}

> **Corporate objective:** acquire a controlling interest in Netflix (NFLX).
> Netflix has **{SHARES_OUTSTANDING_NFLX:,}** shares outstanding; a majority
> stake requires **{GOAL:,} NFLX**. $CHILL accumulates NFLX two ways — NFLX held
> in protocol-owned liquidity, and reflections distributed to shareholders.

![Shareholder report card](shareholder-card.png)

## Ownership position

| Metric | Value |
|---|---|
| **NFLX under $CHILL control** | **{fmt(m['controlled'])} NFLX** (~${fmt(m['usd_controlled'],0)}) |
| Stake in Netflix | {m['stake_pct']:.9f}% of shares outstanding |
| Progress to controlling interest | {m['progress']:.7f}% of {GOAL:,} |
| Shares remaining to majority | {fmt(m['remaining'],0)} NFLX |

## Balance sheet — NFLX holdings

| Holding | NFLX | USD |
|---|---|---|
| Treasury (protocol-owned liquidity) | {fmt(m['net_lp'])} | ${fmt(m['usd_treasury'],0)} |
| Dividends distributed to shareholders | {fmt(m['reflections'])} | ${fmt(m['usd_dividends'],0)} |
| **Total NFLX controlled** | **{fmt(m['controlled'])}** | **${fmt(m['usd_controlled'],0)}** |

## Last 24 hours

| Metric | Value |
|---|---|
| Trading volume | {fmt(m['vol24'])} NFLX (~${fmt(m['usd_vol24'],0)}) |
| Net NFLX accumulated | {fmt(m['net24'])} NFLX |
| Dividends generated | {fmt(m['refl24'],4)} NFLX |
| Transactions | {m['swaps24']} ({m['buys24']} buys / {m['sells24']} sells) |
| $CHILL price change | {chg_s} |

## Shareholder & market data

| Metric | Value |
|---|---|
| Shareholders of record | {m['holders'] if m['holders'] is not None else 'n/a'} |
| Lifetime unique participants | {m['traders']} |
| Shares outstanding ($CHILL) | {CHILL_SUPPLY:,} |
| Market capitalization | ${fmt(m['mcap'],0)} |
| $CHILL price | ${m['chill_usd']:.8f} |
| NFLX price | ${fmt(m['nflx_usd'])} |
| Lifetime volume | {fmt(m['vol'])} NFLX (~${fmt(m['usd_vol'],0)}) |
| Lifetime transactions | {m['swaps']:,} ({m['buys']:,} buys / {m['sells']:,} sells) |
| Days since IPO (launch) | {m['days_live']} |

## Per-share metrics

| Metric | Value |
|---|---|
| NFLX backing per 1M $CHILL | {m['nflx_per_m']:.6f} NFLX |
| Dividends per 1M $CHILL | {m['div_per_m']:.6f} NFLX |

---

*Report generated {m['ts']} · block {m['block']:,} · data via the Sentry-Robinhood
subgraph and Robinhood Chain explorer.*

**Disclaimer:** $CHILL is an independent, community-driven **parody** token. It is
**not affiliated with, endorsed by, sponsored by, or connected to Netflix, Inc.**
in any way. This "shareholder report" is satire. $CHILL is not a security, equity,
or claim on Netflix; it does not represent real ownership of Netflix and confers no
shareholder rights. For entertainment only — not financial advice. DYOR.
"""

def card(m):
    from PIL import Image, ImageDraw, ImageFont
    W, H = 1200, 760
    RED = (207, 2, 10)
    img = Image.new("RGB", (W, H), (0, 0, 0))
    d = ImageDraw.Draw(img)
    def font(sz, bold=True):
        for base in FONT_DIRS:            # bundled variable Oswald first
            p = os.path.join(base, "Oswald.ttf")
            if os.path.exists(p):
                try:
                    f = ImageFont.truetype(p, sz)
                    f.set_variation_by_name("SemiBold" if bold else "Light")
                    return f
                except Exception: pass
        for base in FONT_DIRS:            # system fallback
            for n in (["bahnschrift.ttf"] if bold else ["arial.ttf"]):
                p = os.path.join(base, n)
                if os.path.exists(p):
                    try: return ImageFont.truetype(p, sz)
                    except Exception: pass
        return ImageFont.load_default()
    wmp = find_asset("logos", "primary", "wordmark-red.png")
    if wmp:
        try:
            wm = Image.open(wmp).convert("RGBA")
            wm.thumbnail((260, 78)); img.paste(wm, (60, 46), wm)
        except Exception: pass
    d.text((W - 60, 56), "DAILY SHAREHOLDER REPORT", font=font(26), fill=(150, 150, 150), anchor="ra")
    d.text((W - 60, 90), m["date"], font=font(24, False), fill=(110, 110, 110), anchor="ra")
    d.text((60, 150), f"{fmt(m['controlled'],1)}", font=font(104), fill=(255, 255, 255))
    d.text((62, 272), f"NFLX controlled  ·  ~${fmt(m['usd_controlled'],0)}  ·  {m['stake_pct']:.7f}% of Netflix",
           font=font(28, False), fill=(180, 180, 180))
    # progress bar
    bx, by, bw, bh = 60, 350, W - 120, 38
    d.rounded_rectangle([bx, by, bx + bw, by + bh], radius=19, fill=(30, 30, 30))
    frac = max(m["controlled"] / GOAL, 0.004)
    d.rounded_rectangle([bx, by, bx + int(bw * frac), by + bh], radius=19, fill=RED)
    d.text((bx, by + 50), f"Path to controlling interest — goal {GOAL:,} NFLX", font=font(24, False), fill=(200, 200, 200))
    d.text((bx + bw, by + 48), f"{m['progress']:.6f}%", font=font(28), fill=RED, anchor="ra")
    # metric grid (2 rows x 3)
    cells = [("TREASURY (LP)", f"{fmt(m['net_lp'])} NFLX"),
             ("DIVIDENDS PAID", f"{fmt(m['reflections'])} NFLX"),
             ("SHAREHOLDERS", str(m['holders']) if m['holders'] is not None else "n/a"),
             ("MARKET CAP", f"${fmt(m['mcap'],0)}"),
             ("24H VOLUME", f"${fmt(m['usd_vol24'],0)}"),
             ("NFLX PRICE", f"${fmt(m['nflx_usd'])}")]
    for i, (lab, val) in enumerate(cells):
        x = 60 + (i % 3) * 380
        y = 470 + (i // 3) * 105
        d.text((x, y), lab, font=font(22), fill=RED)
        d.text((x, y + 30), val, font=font(36), fill=(255, 255, 255))
    d.text((60, H - 38), f"{m['ts']}  ·  parody · not affiliated with Netflix, Inc. · not financial advice",
           font=font(18, False), fill=(105, 105, 105))
    p = os.path.join(OUT, "shareholder-card.png")
    img.save(p); return p

def append_history(m):
    fp = os.path.join(OUT, "history.csv")
    cols = ["date", "controlled_nflx", "treasury_nflx", "dividends_nflx", "stake_pct",
            "progress_pct", "holders", "market_cap_usd", "nflx_price_usd", "chill_price_usd", "vol24_usd"]
    rows = []
    if os.path.exists(fp):
        with open(fp, newline="") as f:
            rows = [r for r in csv.DictReader(f) if r.get("date") != m["date"]]
    rows.append({"date": m["date"], "controlled_nflx": f"{m['controlled']:.4f}",
                 "treasury_nflx": f"{m['net_lp']:.4f}", "dividends_nflx": f"{m['reflections']:.4f}",
                 "stake_pct": f"{m['stake_pct']:.9f}", "progress_pct": f"{m['progress']:.7f}",
                 "holders": m["holders"] if m["holders"] is not None else "",
                 "market_cap_usd": f"{m['mcap']:.0f}", "nflx_price_usd": f"{m['nflx_usd']:.4f}",
                 "chill_price_usd": f"{m['chill_usd']:.10f}", "vol24_usd": f"{m['usd_vol24']:.0f}"})
    rows.sort(key=lambda r: r["date"])
    with open(fp, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(rows)

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    m = compute()
    open(os.path.join(OUT, "README.md"), "w", encoding="utf-8").write(markdown(m))
    append_history(m)
    try:
        card(m); print("card ok")
    except Exception as e:
        print("card skipped:", e)
    print(f"report -> {OUT}  |  controlled={m['controlled']:.2f} NFLX  holders={m['holders']}  progress={m['progress']:.7f}%")
