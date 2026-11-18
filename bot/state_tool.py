"""Helpers for Claude's practice account, stored in the paper-trader artifact's database.

The account lives in one document: collection "bot", doc "state", field "json" (a JSON string)
in the same shape the page uses for its own accounts, plus a few extra fields:

  cash, startCash, stocks{}, options{key: {...position, book, stop, target, exitBy, why, spread}},
  orders[], history[{t, kind, side, label, qty, price, amount, book, why, pnl}],
  books{picks|short|sell: {realized, closed, wins}}, equity[{t, value}], lastRun, notes

Option positions carry a signed qty: positive = long (bought), negative = short (sold to open).
Value = mark x qty x 100 and P&L = (mark - avg) x qty x 100 work for both signs.

Usage (from the repo root):
  python3 bot/state_tool.py new  OUT.json                       # fresh $100k account
  python3 bot/state_tool.py fill STATE.json OUT.json FILLS.json  # apply fills
  python3 bot/state_tool.py show STATE.json                      # print a summary

FILLS.json is a list of fills. "side" is one of:
  buy     buy contracts (opens a long, or closes a short)
  sell    sell contracts (closes a long, or opens a short)
  expire  settle the whole position at "price" (intrinsic value, 0 if out of the money)
  score   {"side": "score", "book": "sell", "pnl": total} after both legs of a spread are closed
Opening fills also carry: book, sym, exp ("YYYY-MM-DD"), type ("call"/"put"), strike, and optionally
stop, target, exitBy, why, spread (an id shared by both legs of a spread). Every fill needs key, qty, price, t.
Example credit spread (bull put): [{"side":"sell", "key":"<short put id>", ...}, {"side":"buy", "key":"<long put id>", ...}]
"""
import json, sys
from datetime import datetime, timezone

START = 100000.0
BOOKS = ("picks", "short", "sell")


def ms(t):
    return int(datetime.fromisoformat(t.replace("Z", "+00:00")).timestamp() * 1000)


def new():
    return {"cash": START, "startCash": START, "stocks": {}, "options": {}, "orders": [], "history": [],
            "simPrices": {}, "books": {b: {"realized": 0, "closed": 0, "wins": 0} for b in BOOKS},
            "equity": [], "lastRun": None, "notes": ""}


def label(o):
    d = datetime.fromisoformat(o["exp"]).strftime("%b %-d")
    return f'{o["sym"]} {o["strike"]:g} {"Call" if o["type"] == "call" else "Put"} {d}'


def apply(state, f):
    for b in BOOKS:
        state["books"].setdefault(b, {"realized": 0, "closed": 0, "wins": 0})
    if f["side"] == "score":  # {"side": "score", "book": "sell", "pnl": 62.0}: count a closed spread as one trade
        score_spread(state, f["book"], f["pnl"])
        return
    t = ms(f["t"])
    key, price = f["key"], f["price"]
    p = state["options"].get(key)
    if f["side"] == "expire":
        if not p:
            raise SystemExit(f"nothing to expire: {f}")
        delta = -p["qty"]
    else:
        q = int(f["qty"])
        if q <= 0:
            raise SystemExit(f"qty must be positive: {f}")
        delta = q if f["side"] == "buy" else -q
    if p is None:
        p = {k: f[k] for k in ("key", "sym", "exp", "type", "strike")} | {"mult": 100, "qty": 0, "avg": 0.0, "book": f["book"]}
    cash_change = round(-delta * price * 100, 2)
    if cash_change < 0 and -cash_change > state["cash"] + 1e-9:
        raise SystemExit(f"not enough cash for {f}")
    old = p["qty"]
    closing = old != 0 and (old > 0) != (delta > 0)
    closed_qty = min(abs(delta), abs(old)) if closing else 0
    pnl = None
    if closed_qty:
        sign = 1 if old > 0 else -1
        pnl = round((price - p["avg"]) * closed_qty * sign * 100, 2)
        b = state["books"][p["book"]]
        b["realized"] = round(b["realized"] + pnl, 2)
        if not p.get("spread"):  # spreads are scored once, by the caller, as one trade (see note below)
            b["closed"] += 1; b["wins"] += pnl > 0
    opened = abs(delta) - closed_qty
    new_qty = old + delta
    if opened:
        if closing or old == 0:
            p["avg"] = price
        else:
            p["avg"] = (p["avg"] * abs(old) + price * opened) / (abs(old) + opened)
        for k in ("book", "stop", "target", "exitBy", "why", "spread"):
            if k in f: p[k] = f[k]
    p["qty"] = new_qty
    state["cash"] = round(state["cash"] + cash_change, 2)
    if f["side"] == "expire":
        verb = "Expired worthless" if price == 0 else "Settled at expiration"
    elif closed_qty:
        verb = "Bought to close" if delta > 0 else "Sold"
    else:
        verb = "Bought" if delta > 0 else "Sold to open"
    h = {"t": t, "kind": "opt", "side": "exp" if f["side"] == "expire" else ("buy" if delta > 0 else "sell"),
         "label": f"{verb} {label(p)}", "qty": abs(delta), "price": price, "amount": cash_change,
         "book": p["book"], "why": f.get("why", "")}
    if pnl is not None:
        h["pnl"] = pnl
    state["history"].insert(0, h)
    state["history"] = state["history"][:400]
    if new_qty == 0:
        state["options"].pop(key, None)
    else:
        state["options"][key] = p


def score_spread(state, book, pnl):
    """Count a closed spread as one trade (its legs don't count separately)."""
    b = state["books"][book]
    b["closed"] += 1; b["wins"] += pnl > 0


def load(path):
    d = json.load(open(path))
    return json.loads(d["json"]) if "json" in d else d


def save(state, path, when=None):
    state["lastRun"] = when or datetime.now(timezone.utc).isoformat(timespec="seconds")
    json.dump({"json": json.dumps(state), "updatedAt": state["lastRun"]}, open(path, "w"))


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "new":
        save(new(), sys.argv[2])
    elif cmd == "fill":
        s = load(sys.argv[2])
        for f in json.load(open(sys.argv[4])):
            apply(s, f)
        save(s, sys.argv[3])
    elif cmd == "show":
        s = load(sys.argv[2])
        print("cash", s["cash"], "books", s["books"])
        for p in s["options"].values():
            print(f'  {p["book"]:5} {label(p):28} x{p["qty"]} avg {p["avg"]:.2f} stop {p.get("stop")} target {p.get("target")} exitBy {p.get("exitBy")} spread {p.get("spread")}')
    else:
        raise SystemExit(__doc__)
