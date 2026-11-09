"""Freelance rate calculator.

Works backwards from the income you want to take home to the hourly,
daily and project rates you need to charge, accounting for taxes,
business expenses, time off and non-billable hours.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RateInputs:
    target_take_home: float          # yearly money you want after tax and expenses
    annual_expenses: float = 0.0     # software, hardware, insurance, etc.
    tax_rate: float = 0.30           # effective tax rate, 0-1
    weeks_off: float = 6.0           # vacation, holidays, sick days
    hours_per_week: float = 40.0     # total working hours
    billable_ratio: float = 0.65     # share of working hours you can bill
    profit_margin: float = 0.10      # buffer for slow months, 0-1


@dataclass
class RateResult:
    gross_revenue_needed: float
    billable_hours_per_year: float
    hourly: float
    daily: float
    weekly: float


def calculate(inp: RateInputs) -> RateResult:
    if not 0 <= inp.tax_rate < 1:
        raise ValueError("tax_rate must be between 0 and 1")
    if not 0 < inp.billable_ratio <= 1:
        raise ValueError("billable_ratio must be between 0 and 1")
    if not 0 <= inp.profit_margin < 1:
        raise ValueError("profit_margin must be between 0 and 1")
    working_weeks = 52 - inp.weeks_off
    if working_weeks <= 0 or inp.hours_per_week <= 0:
        raise ValueError("you need some working time to earn money")

    pre_tax = inp.target_take_home / (1 - inp.tax_rate)
    gross = (pre_tax + inp.annual_expenses) / (1 - inp.profit_margin)
    billable_hours = working_weeks * inp.hours_per_week * inp.billable_ratio
    hourly = gross / billable_hours
    billable_per_day = inp.hours_per_week * inp.billable_ratio / 5
    return RateResult(
        gross_revenue_needed=round(gross, 2),
        billable_hours_per_year=round(billable_hours, 1),
        hourly=round(hourly, 2),
        daily=round(hourly * billable_per_day, 2),
        weekly=round(hourly * billable_per_day * 5, 2),
    )


def quote_project(hourly: float, estimated_hours: float, risk_buffer: float = 0.2) -> float:
    """Fixed-price quote: estimate plus a buffer, because estimates are always low."""
    if estimated_hours <= 0:
        raise ValueError("estimated_hours must be positive")
    return round(hourly * estimated_hours * (1 + risk_buffer), 2)
