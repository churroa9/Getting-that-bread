import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

from bread import flip, invoice, printables, rate
from bread.cli import main


class RateTests(unittest.TestCase):
    def test_hourly_covers_target(self):
        inp = rate.RateInputs(target_take_home=70000, annual_expenses=5000)
        r = rate.calculate(inp)
        # Gross revenue minus margin, expenses and tax gets back to the target.
        net = (r.gross_revenue_needed * (1 - inp.profit_margin) - inp.annual_expenses) * (1 - inp.tax_rate)
        self.assertAlmostEqual(net, 70000, delta=1)
        self.assertAlmostEqual(r.hourly * r.billable_hours_per_year, r.gross_revenue_needed, delta=5)

    def test_invalid(self):
        with self.assertRaises(ValueError):
            rate.calculate(rate.RateInputs(50000, tax_rate=1.2))

    def test_quote(self):
        self.assertEqual(rate.quote_project(100, 10), 1200.0)


class FlipTests(unittest.TestCase):
    def test_list_price_round_trip(self):
        price = flip.list_price_for(20, cost=10, shipping=5, platform="ebay")
        self.assertGreaterEqual(flip.profit(price, 10, 5, "ebay").profit, 20)

    def test_max_buy_round_trip(self):
        buy = flip.max_buy_price(60, 15, shipping=6, platform="mercari")
        self.assertAlmostEqual(flip.profit(60, buy, 6, "mercari").profit, 15, delta=0.01)

    def test_compare_sorted(self):
        res = flip.compare(50, 10)
        self.assertEqual(res[0].platform, "facebook")
        self.assertEqual([r.profit for r in res], sorted((r.profit for r in res), reverse=True))


class InvoiceTests(unittest.TestCase):
    def make(self, **kw):
        return invoice.Invoice(number="INV-0001", client="Client & Co",
                               items=[invoice.LineItem("Work <b>", 10, 50)],
                               issued=date(2026, 1, 1), **kw)

    def test_totals(self):
        inv = self.make(tax_rate=0.1, discount=50)
        self.assertEqual(inv.subtotal, 500)
        self.assertEqual(inv.tax, 45)
        self.assertEqual(inv.total, 495)

    def test_status(self):
        inv = self.make()
        self.assertEqual(inv.status(date(2026, 1, 10)), "open")
        self.assertEqual(inv.status(date(2026, 2, 1)), "overdue")
        inv.paid = True
        self.assertEqual(inv.status(date(2026, 2, 1)), "paid")

    def test_html_escapes(self):
        out = invoice.render_html(self.make())
        self.assertIn("Client &amp; Co", out)
        self.assertIn("Work &lt;b&gt;", out)

    def test_ledger(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "l.json"
            led = invoice.Ledger(path)
            led.add(self.make())
            self.assertEqual(led.next_number(), "INV-0002")
            led.save()
            led2 = invoice.Ledger(path)
            self.assertEqual(led2.get("INV-0001").total, 500)
            with self.assertRaises(ValueError):
                led2.add(self.make())


class PrintableTests(unittest.TestCase):
    def test_all_valid_svg(self):
        for theme in printables.THEMES.values():
            for page in printables.PAGES:
                for fn in printables.PRODUCTS.values():
                    ET.fromstring(fn(theme, page=page))
                ET.fromstring(printables.monthly_calendar(theme, 2027, 2, page=page))

    def test_bundle(self):
        with tempfile.TemporaryDirectory() as d:
            files = printables.build_bundle(d, ["sage"], year=2027)
            self.assertEqual(len(files), 3 + 12)


class CliTests(unittest.TestCase):
    def test_invoice_flow(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "job.json"
            src.write_text(json.dumps({"client": "X", "items": [
                {"description": "a", "quantity": 1, "unit_price": 100}]}))
            led = str(Path(d) / "ledger.json")
            out = str(Path(d) / "inv.html")
            self.assertEqual(main(["invoice", "new", str(src), "--ledger", led, "--out", out]), 0)
            self.assertTrue(Path(out).exists())
            self.assertEqual(main(["invoice", "paid", "INV-0001", "--ledger", led]), 0)
            self.assertTrue(invoice.Ledger(led).get("INV-0001").paid)
            self.assertEqual(main(["invoice", "paid", "INV-9999", "--ledger", led]), 1)


if __name__ == "__main__":
    unittest.main()
