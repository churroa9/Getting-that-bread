"""Invoice generator and tracker.

Turns a JSON description of a job into a clean, printable HTML invoice
(print to PDF from any browser) and keeps a ledger of what's paid and
what's overdue, so you actually collect the money you've earned.
"""

from __future__ import annotations

import html
import json
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path


@dataclass
class LineItem:
    description: str
    quantity: float
    unit_price: float

    @property
    def total(self) -> float:
        return round(self.quantity * self.unit_price, 2)


@dataclass
class Invoice:
    number: str
    client: str
    items: list[LineItem]
    issued: date = field(default_factory=date.today)
    due_days: int = 14
    tax_rate: float = 0.0
    discount: float = 0.0
    currency: str = "$"
    from_name: str = ""
    from_details: str = ""
    client_details: str = ""
    notes: str = ""
    payment_instructions: str = ""
    paid: bool = False

    @property
    def due(self) -> date:
        return self.issued + timedelta(days=self.due_days)

    @property
    def subtotal(self) -> float:
        return round(sum(i.total for i in self.items), 2)

    @property
    def tax(self) -> float:
        return round((self.subtotal - self.discount) * self.tax_rate, 2)

    @property
    def total(self) -> float:
        return round(self.subtotal - self.discount + self.tax, 2)

    def status(self, today: date | None = None) -> str:
        if self.paid:
            return "paid"
        return "overdue" if (today or date.today()) > self.due else "open"

    @classmethod
    def from_dict(cls, d: dict) -> "Invoice":
        d = dict(d)
        d["items"] = [LineItem(**i) for i in d["items"]]
        if isinstance(d.get("issued"), str):
            d["issued"] = date.fromisoformat(d["issued"])
        return cls(**d)

    def to_dict(self) -> dict:
        return {
            "number": self.number, "client": self.client,
            "items": [vars(i) for i in self.items],
            "issued": self.issued.isoformat(), "due_days": self.due_days,
            "tax_rate": self.tax_rate, "discount": self.discount,
            "currency": self.currency, "from_name": self.from_name,
            "from_details": self.from_details, "client_details": self.client_details,
            "notes": self.notes, "payment_instructions": self.payment_instructions,
            "paid": self.paid,
        }


def _money(cur: str, v: float) -> str:
    return f"{cur}{v:,.2f}"


def _lines(s: str) -> str:
    return "<br>".join(html.escape(x) for x in s.splitlines())


def render_html(inv: Invoice) -> str:
    e = html.escape
    m = lambda v: _money(inv.currency, v)  # noqa: E731
    rows = "\n".join(
        f"<tr><td>{e(i.description)}</td><td class=n>{i.quantity:g}</td>"
        f"<td class=n>{m(i.unit_price)}</td><td class=n>{m(i.total)}</td></tr>"
        for i in inv.items
    )
    extra = ""
    if inv.discount:
        extra += f"<tr><td colspan=3>Discount</td><td class=n>-{m(inv.discount)}</td></tr>"
    if inv.tax_rate:
        extra += f"<tr><td colspan=3>Tax ({inv.tax_rate:.2%})</td><td class=n>{m(inv.tax)}</td></tr>"
    stamp = '<div class=stamp>PAID</div>' if inv.paid else ""
    return f"""<!doctype html>
<html><head><meta charset=utf-8><title>Invoice {e(inv.number)}</title>
<style>
body{{font:15px/1.5 system-ui,sans-serif;color:#1a1a1a;max-width:780px;margin:40px auto;padding:0 24px;position:relative}}
h1{{font-size:32px;margin:0;letter-spacing:.04em}}
.top{{display:flex;justify-content:space-between;gap:24px;margin-bottom:32px}}
.muted{{color:#666}} .r{{text-align:right}}
.parties{{display:flex;justify-content:space-between;gap:24px;margin-bottom:28px}}
table{{width:100%;border-collapse:collapse}}
th{{text-align:left;border-bottom:2px solid #1a1a1a;padding:8px 6px;font-size:13px;text-transform:uppercase;letter-spacing:.05em}}
td{{padding:8px 6px;border-bottom:1px solid #e5e5e5}} .n{{text-align:right;font-variant-numeric:tabular-nums}}
tfoot td{{border:0}} tfoot tr.total td{{font-size:20px;font-weight:700;border-top:2px solid #1a1a1a}}
.box{{margin-top:28px;padding:14px 16px;background:#f6f6f6;border-radius:6px}}
.stamp{{position:absolute;top:60px;right:40%;transform:rotate(-15deg);border:4px solid #1a8a3a;color:#1a8a3a;font-size:42px;font-weight:800;padding:4px 18px;border-radius:8px;opacity:.75}}
@media print{{body{{margin:0}}}}
</style></head><body>
{stamp}
<div class=top>
  <div><h1>INVOICE</h1><div class=muted>#{e(inv.number)}</div></div>
  <div class=r><div><b>Issued:</b> {inv.issued:%b %d, %Y}</div><div><b>Due:</b> {inv.due:%b %d, %Y}</div></div>
</div>
<div class=parties>
  <div><div class=muted>From</div><b>{e(inv.from_name)}</b><br>{_lines(inv.from_details)}</div>
  <div class=r><div class=muted>Bill to</div><b>{e(inv.client)}</b><br>{_lines(inv.client_details)}</div>
</div>
<table>
<thead><tr><th>Description</th><th class=n>Qty</th><th class=n>Rate</th><th class=n>Amount</th></tr></thead>
<tbody>
{rows}
</tbody>
<tfoot>
<tr><td colspan=3>Subtotal</td><td class=n>{m(inv.subtotal)}</td></tr>
{extra}
<tr class=total><td colspan=3>Total due</td><td class=n>{m(inv.total)}</td></tr>
</tfoot>
</table>
{f'<div class=box><b>How to pay</b><br>{_lines(inv.payment_instructions)}</div>' if inv.payment_instructions else ''}
{f'<div class=box>{_lines(inv.notes)}</div>' if inv.notes else ''}
</body></html>
"""


class Ledger:
    """A JSON file of invoices, so you can see who still owes you."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.invoices: list[Invoice] = []
        if self.path.exists():
            self.invoices = [Invoice.from_dict(d) for d in json.loads(self.path.read_text())]

    def save(self) -> None:
        self.path.write_text(json.dumps([i.to_dict() for i in self.invoices], indent=2))

    def add(self, inv: Invoice) -> None:
        if any(i.number == inv.number for i in self.invoices):
            raise ValueError(f"invoice {inv.number} already exists")
        self.invoices.append(inv)

    def get(self, number: str) -> Invoice:
        for i in self.invoices:
            if i.number == number:
                return i
        raise KeyError(number)

    def next_number(self, prefix: str = "INV-") -> str:
        nums = [int(i.number[len(prefix):]) for i in self.invoices
                if i.number.startswith(prefix) and i.number[len(prefix):].isdigit()]
        return f"{prefix}{(max(nums) + 1) if nums else 1:04d}"

    def summary(self, today: date | None = None) -> dict[str, float]:
        out = {"paid": 0.0, "open": 0.0, "overdue": 0.0}
        for i in self.invoices:
            out[i.status(today)] += i.total
        return {k: round(v, 2) for k, v in out.items()}
