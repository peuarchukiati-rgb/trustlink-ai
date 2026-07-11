"""Canonical enums. String values match Volume 7 (Data Architecture) field vocabularies."""
from __future__ import annotations

from enum import Enum


class TransactionType(str, Enum):
    INCOME = "income"
    EXPENSE = "expense"
    TRANSFER = "transfer"
    PAYMENT = "payment"


class Category(str, Enum):
    PAYROLL = "payroll"
    UTILITY = "utility"
    INSURANCE = "insurance"
    RENT = "rent"
    FOOD = "food"
    TRANSPORT = "transport"
    SHOPPING = "shopping"
    OTHER = "other"


class TrustTier(str, Enum):
    STRONG = "Strong"
    MODERATE = "Moderate"
    WEAK = "Weak"


class FraudLevel(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"

    @property
    def rank(self) -> int:
        return {"Low": 0, "Medium": 1, "High": 2}[self.value]


# Essential vs discretionary spending, used by the Lifestyle Stability dimension.
ESSENTIAL_CATEGORIES = {
    Category.RENT,
    Category.UTILITY,
    Category.INSURANCE,
    Category.TRANSPORT,
    Category.FOOD,
}
DISCRETIONARY_CATEGORIES = {Category.SHOPPING, Category.OTHER}

# Recurring bill categories used by Payment Discipline.
RECURRING_CATEGORIES = {Category.UTILITY, Category.INSURANCE, Category.RENT}
