"""Command line entry point: `python -m bread <command> ...`"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import flip, invoice, printables, rate


def _cmd_rate(a):
    r = rate.calculate(rate.RateInputs(
        target_take_home=a.take_home, annual_expenses=a.expenses, tax_rate=a.tax,
        weeks_off=a.weeks_off, hours_per_week=a.hours, billable_ratio=a.billable,
        profit_margin=a.margin))
    print(f"Gross revenue needed: ${r.gross_revenue_needed:,.2f}/yr")
    print(f"Billable hours:       {r.billable_hours_per_year:,.0f}/yr")
    print(f"Charge at least:      ${r.hourly:,.2f}/hr  ·  ${r.daily:,.2f}/day  ·  ${r.weekly:,.2f}/week")
    if a.project_hours:
        print(f"Project quote ({a.project_hours:g}h + 20% buffer): "
              f"${rate.quote_project(r.hourly, a.project_hours):,.2f}")


def _fees(a):
    if a.fee_pct is not None or a.fee_fixed is not None:
        base = flip.PLATFORMS[a.platform]
        return flip.Fees(pct=a.fee_pct / 100 if a.fee_pct is not None else base.pct,
                         fixed=a.fee_fixed if a.fee_fixed is not None else base.fixed)
    return None


def _cmd_flip(a):
    if a.compare:
        print(f"{'platform':<10} {'fees':>8} {'profit':>9} {'margin':>8} {'ROI':>8}")
        for r in flip.compare(a.sell, a.cost, a.shipping):
            print(f"{r.platform:<10} {r.fees:>8.2f} {r.profit:>9.2f} {r.margin:>8.1%} {r.roi:>8.1%}")
        return
    fees = _fees(a)
    r = flip.profit(a.sell, a.cost, a.shipping, a.platform, fees)
    verdict = "FLIP IT" if r.profit >= a.target else "PASS"
    print(f"{r.platform}: sell ${r.sale_price:.2f} − fees ${r.fees:.2f} − ship ${r.shipping:.2f} "
          f"− cost ${r.cost:.2f} = ${r.profit:.2f} profit "
          f"({r.margin:.1%} margin, {r.roi:.0%} ROI) → {verdict}")
    print(f"Max buy price for ${a.target:.2f} profit: "
          f"${flip.max_buy_price(a.sell, a.target, a.shipping, a.platform, fees):.2f}")
    print(f"List price for ${a.target:.2f} profit at this cost: "
          f"${flip.list_price_for(a.target, a.cost, a.shipping, a.platform, fees):.2f}")


def _cmd_invoice(a):
    ledger = invoice.Ledger(a.ledger)
    if a.action == "new":
        data = json.loads(Path(a.file).read_text())
        data.setdefault("number", ledger.next_number())
        inv = invoice.Invoice.from_dict(data)
        ledger.add(inv)
        ledger.save()
        out = Path(a.out or f"{inv.number}.html")
        out.write_text(invoice.render_html(inv))
        print(f"Created {inv.number} for {inv.client}: {inv.currency}{inv.total:,.2f}, "
              f"due {inv.due:%Y-%m-%d} → {out}")
    elif a.action == "paid":
        inv = ledger.get(a.number)
        inv.paid = True
        ledger.save()
        if a.out:
            Path(a.out).write_text(invoice.render_html(inv))
        print(f"{inv.number} marked paid.")
    elif a.action == "render":
        inv = ledger.get(a.number)
        out = Path(a.out or f"{inv.number}.html")
        out.write_text(invoice.render_html(inv))
        print(f"Wrote {out}")
    elif a.action == "list":
        for inv in ledger.invoices:
            print(f"{inv.number:<10} {inv.client:<24} {inv.currency}{inv.total:>10,.2f}  "
                  f"due {inv.due:%Y-%m-%d}  {inv.status().upper()}")
        s = ledger.summary()
        print(f"\nPaid ${s['paid']:,.2f} · Open ${s['open']:,.2f} · Overdue ${s['overdue']:,.2f}")


def _cmd_printables(a):
    files = printables.build_bundle(a.out, a.themes or None, a.page, a.year)
    print(f"Wrote {len(files)} printable pages to {a.out}/")


def main(argv=None):
    p = argparse.ArgumentParser(prog="bread", description="Tools for getting that bread.")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("rate", help="what hourly rate to charge as a freelancer")
    r.add_argument("take_home", type=float, help="yearly take-home income you want")
    r.add_argument("--expenses", type=float, default=0)
    r.add_argument("--tax", type=float, default=0.30, help="effective tax rate, e.g. 0.3")
    r.add_argument("--weeks-off", type=float, default=6)
    r.add_argument("--hours", type=float, default=40, help="working hours per week")
    r.add_argument("--billable", type=float, default=0.65, help="share of hours you can bill")
    r.add_argument("--margin", type=float, default=0.10, help="safety buffer, e.g. 0.1")
    r.add_argument("--project-hours", type=float, help="also quote a fixed-price project")
    r.set_defaults(fn=_cmd_rate)

    f = sub.add_parser("flip", help="is this resale flip worth it?")
    f.add_argument("--sell", type=float, required=True, help="expected sale price")
    f.add_argument("--cost", type=float, default=0, help="what you paid / will pay")
    f.add_argument("--shipping", type=float, default=0, help="shipping you pay")
    f.add_argument("--platform", choices=list(flip.PLATFORMS), default="ebay")
    f.add_argument("--target", type=float, default=10, help="minimum profit you want")
    f.add_argument("--fee-pct", type=float, help="override fee percent, e.g. 13.25")
    f.add_argument("--fee-fixed", type=float, help="override fixed fee per order")
    f.add_argument("--compare", action="store_true", help="compare every platform")
    f.set_defaults(fn=_cmd_flip)

    i = sub.add_parser("invoice", help="create and track invoices")
    i.add_argument("action", choices=["new", "paid", "render", "list"])
    i.add_argument("target", nargs="?", help="JSON file (new) or invoice number (paid/render)")
    i.add_argument("--ledger", default="invoices.json")
    i.add_argument("--out", help="HTML output path")
    i.set_defaults(fn=_cmd_invoice)

    pr = sub.add_parser("printables", help="generate sellable printable planners")
    pr.add_argument("--out", default="printables_out")
    pr.add_argument("--themes", nargs="*", choices=list(printables.THEMES))
    pr.add_argument("--page", choices=list(printables.PAGES), default="letter")
    pr.add_argument("--year", type=int, help="also build a 12-month calendar")
    pr.set_defaults(fn=_cmd_printables)

    a = p.parse_args(argv)
    if a.cmd == "invoice":
        a.file = a.number = a.target
        if a.action != "list" and not a.target:
            p.error(f"invoice {a.action} needs a {'JSON file' if a.action == 'new' else 'invoice number'}")
    try:
        a.fn(a)
    except (ValueError, KeyError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    return 0
