# utils/formatter.py

def format_currency(amount):
    """Return a formatted currency string."""
    return "${:,.2f}".format(amount)


def format_date(date_str):
    """Format a date string as needed. For now, it returns the string unchanged."""
    return date_str
