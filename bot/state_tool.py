"""Helpers for Claude's practice account, stored in the paper-trader artifact's database.

The account lives in one document: collection "bot", doc "state", field "json" (a JSON string)
in the same shape the page uses for its own accounts, plus a few extra fields:

  cash, startCash, stocks{}, options{key: {...position, book, stop, target, exitBy, why}},
  orders[], history[{t, kind, side, label, qty, price, amount, book, why}],
  books{picks|short: {realized, closed, wins}}, equity[{t, value}], lastRun, notes

Usage (the scheduled runs call these with python3 from the repo root):
  python3 bot/state_tool.py new  OUT.json                       # fresh $100k account
  python3 bot/state_tool.py fill STATE.json OUT.json FILLS.json  # apply buys/sells
  python3 bot/state_tool.py show STATE.json                      # print a summary
FILLS.json is a list of fills, for example:
  {"side": "buy", "book": "short", "key": "<instrument id>", "sym": "SPY", "exp": "2026-11-17",
   "type": "call", "strike": 735, "qty": 2, "price": 1.53, "t": "2026-11-17T17:31:22Z",
   "stop": 0.92, "target": 2.30, "exitBy": "2026-11-17T20:45:00Z", "why": "..."}
  {"side": "sell", "book": "short", "key": "<instrument id>", "qty": 2, "price": 2.31,
   "t": "...", "why": "target hit"}
  {"side": "expire", "key": "<instrument id>", "price": 0.00, "t": "...", "why": "expired"}
"""
import json, sys
from datetime import datetime, timezone

START = 100000.0


def ms(t):
    return int(datetime.fromisoformat(t.replace("Z", "+00:00")).timestamp() * 1000)


def new():
    return {"cash": START, "startCash": START, "stocks": {}, "options": {}, "orders": [], "history": [],
            "simPrices": {}, "books": {"picks": {"realized": 0, "closed": 0, "wins": 0},
                                       "short": {"realized": 0, "closed": 0, "wins": 0}},
            "equity": [], "lastRun": None, "notes": ""}


def label(o):
    d = datetime.fromisoformat(o["exp"]).strftime("%b %-d")
    return f'{o["sym"]} {o["strike"]:g} {"Call" if o["type"] == "call" else "Put"} {d}'


def apply(state, f):
    t = ms(f["t"])
    if f["side"] == "buy":
        cost = round(f["qty"] * f["price"] * 100, 2)
        if cost > state["cash"] + 1e-9:
            raise SystemExit(f"not enough cash for {f}")
        p = state["options"].get(f["key"]) or {k: f[k] for k in ("key", "sym", "exp", "type", "strike")} | {"mult": 100, "qty": 0, "avg": 0}
        p["avg"] = (p["avg"] * p["qty"] + f["price"] * f["qty"]) / (p["qty"] + f["qty"])
        p["qty"] += f["qty"]
        for k in ("book", "stop", "target", "exitBy", "why"):
            if k in f: p[k] = f[k]
        state["options"][f["key"]] = p
        state["cash"] = round(state["cash"] - cost, 2)
        state["history"].insert(0, {"t": t, "kind": "opt", "side": "buy", "label": "Bought " + label(p), "qty": f["qty"],
                                    "price": f["price"], "amount": -cost, "book": p["book"], "why": f.get("why", "")})
    else:  # sell or expire
        p = state["options"][f["key"]]
        qty = f.get("qty", p["qty"])
        if qty > p["qty"]:
            raise SystemExit(f"selling more than held: {f}")
        amt = round(qty * f["price"] * 100, 2)
        pnl = round(amt - qty * p["avg"] * 100, 2)
        b = state["books"][p["book"]]
        b["realized"] = round(b["realized"] + pnl, 2); b["closed"] += 1; b["wins"] += pnl > 0
        state["cash"] = round(state["cash"] + amt, 2)
        verb = "Sold" if f["side"] == "sell" else ("Exercised" if f["price"] > 0 else "Expired worthless")
        state["history"].insert(0, {"t": t, "kind": "opt", "side": "sell" if f["side"] == "sell" else "exp",
                                    "label": f"{verb} {label(p)}", "qty": qty, "price": f["price"], "amount": amt,
                                    "book": p["book"], "why": f.get("why", ""), "pnl": pnl})
        p["qty"] -= qty
        if p["qty"] == 0:
            del state["options"][f["key"]]
    state["history"] = state["history"][:400]


def load(path):
    d = json.load(open(path))
    return json.loads(d["json"]) if "json" in d else d


def save(state, path):
    state["lastRun"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
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
            print(f'  {p["book"]:5} {label(p):28} x{p["qty"]} avg {p["avg"]:.2f} stop {p.get("stop")} target {p.get("target")} exitBy {p.get("exitBy")}')
    else:
        raise SystemExit(__doc__)
