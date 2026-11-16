"""Stock valuation for a tiny shop."""


def line_value(item):
    return item["price"]


def total_value(items):
    return sum(line_value(i) for i in items)
