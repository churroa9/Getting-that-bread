"""Reseller profit calculator.

Tells you whether a flip is worth it after marketplace fees, payment
processing, shipping and your cost, and what to list at to hit a target
profit.

Fee presets are approximations and platforms change them often. Check the
current fee page for your category and override with --fee-pct/--fee-fixed.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Fees:
    pct: float     # percentage of sale price (incl. shipping where the platform does), 0-1
    fixed: float   # fixed per-order fee


# Approximate, editable presets. Verify against each platform's current fee page.
PLATFORMS: dict[str, Fees] = {
    "ebay": Fees(pct=0.1325, fixed=0.40),
    "etsy": Fees(pct=0.065 + 0.03, fixed=0.20 + 0.25),   # transaction + processing, listing fee
    "mercari": Fees(pct=0.10 + 0.029, fixed=0.50),
    "poshmark": Fees(pct=0.20, fixed=0.0),               # for sales over $15
    "depop": Fees(pct=0.033, fixed=0.45),
    "facebook": Fees(pct=0.0, fixed=0.0),                # local pickup, cash
    "custom": Fees(pct=0.0, fixed=0.0),
}


@dataclass
class FlipResult:
    platform: str
    sale_price: float
    fees: float
    shipping: float
    cost: float
    profit: float
    margin: float   # profit / sale price
    roi: float      # profit / cost


def profit(
    sale_price: float,
    cost: float,
    shipping: float = 0.0,
    platform: str = "ebay",
    fees: Fees | None = None,
) -> FlipResult:
    f = fees or PLATFORMS[platform]
    fee_total = sale_price * f.pct + f.fixed
    p = sale_price - fee_total - shipping - cost
    return FlipResult(
        platform=platform,
        sale_price=round(sale_price, 2),
        fees=round(fee_total, 2),
        shipping=round(shipping, 2),
        cost=round(cost, 2),
        profit=round(p, 2),
        margin=round(p / sale_price, 4) if sale_price else 0.0,
        roi=round(p / cost, 4) if cost else float("inf"),
    )


def list_price_for(
    target_profit: float,
    cost: float,
    shipping: float = 0.0,
    platform: str = "ebay",
    fees: Fees | None = None,
) -> float:
    """Minimum list price to clear target_profit after fees, shipping and cost."""
    f = fees or PLATFORMS[platform]
    if f.pct >= 1:
        raise ValueError("fee percentage must be below 100%")
    price = (target_profit + cost + shipping + f.fixed) / (1 - f.pct)
    return round(price + 0.004, 2)  # round up to the cent


def max_buy_price(
    sale_price: float,
    target_profit: float,
    shipping: float = 0.0,
    platform: str = "ebay",
    fees: Fees | None = None,
) -> float:
    """The most you should pay for an item you expect to sell at sale_price."""
    f = fees or PLATFORMS[platform]
    return round(sale_price * (1 - f.pct) - f.fixed - shipping - target_profit, 2)


def compare(sale_price: float, cost: float, shipping: float = 0.0) -> list[FlipResult]:
    """Profit on every preset platform, best first."""
    results = [profit(sale_price, cost, shipping, name) for name in PLATFORMS if name != "custom"]
    return sorted(results, key=lambda r: r.profit, reverse=True)
