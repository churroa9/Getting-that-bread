# Getting That Bread 🍞

Small, dependency-free Python tools (stdlib only, Python 3.10+) for making and keeping money.

| Tool | What it does | How it makes money |
|---|---|---|
| `rate` | Works backwards from your target income to the hourly, daily or project rate you need to charge | Stops you undercharging for freelance work |
| `flip` | Profit calculator for reselling on eBay, Etsy, Mercari, Poshmark, Depop or Facebook | Tells you the most to pay and the least to list at |
| `invoice` | Makes printable HTML invoices and keeps a ledger of what's paid, open or overdue | Helps you actually collect what you're owed |
| `web/paper-trader.html` | Practice trading account with $100k of pretend money: stocks, options chains, market and limit orders | Lets you practise day trading before risking real money |
| `printables` | Generates print-ready planners, habit trackers, budget sheets and calendars in 5 colour themes | Digital products to sell on Etsy, Gumroad or Payhip |

## Quick start

```bash
python -m bread rate 75000 --expenses 4000 --project-hours 30
# Charge at least: $103.25/hr · $536.92/day · $2,684.61/week
# Project quote (30h + 20% buffer): $3,717.00

python -m bread flip --sell 45 --cost 8 --shipping 6 --target 10
python -m bread flip --sell 45 --cost 8 --shipping 6 --compare   # every platform, best first

python -m bread invoice new examples/invoice.json   # writes INV-0001.html, open it and print to PDF
python -m bread invoice list                          # paid / open / overdue totals
python -m bread invoice paid INV-0001

python -m bread printables --out printables_out --year 2027
# 75 pages: 3 products + 12 calendar months × 5 themes (minimal, sage, blush, ocean, sand)
```

Run `python -m bread <command> --help` to see every option.

## Selling the printables

1. Generate a bundle: `python -m bread printables --page letter --year 2027`, then again with `--page a4` for buyers outside the US.
2. Open each SVG in a browser and print to PDF. Zip each theme's pages into its own folder.
3. List each theme as its own product, such as "Sage 2027 Planner Bundle". Mockup photos sell better than flat scans.
4. To make more designs, add new `Theme` entries in `bread/printables.py` or change `title=` to target a niche, such as "Workout Tracker" or "Reading Log".

## Paper trader

`web/paper-trader.html` is a practice trading account with $100,000 of pretend money. When the Robinhood connector is available it uses live quotes from it, through read-only tools only. Otherwise it runs a built-in simulated market. Orders are never sent to a broker. Open the file in a browser to run it in simulated mode.

## Notes

- **Fee presets in `flip` are estimates.** Platforms change their fees often. Check the current fee page for your category and override with `--fee-pct` and `--fee-fixed`.
- `rate` uses an effective tax rate you provide. Self-employment tax varies by country and state, so ask an accountant.

## Tests

```bash
python -m unittest
```
