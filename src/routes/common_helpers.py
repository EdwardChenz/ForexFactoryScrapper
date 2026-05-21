import logging

logger = logging.getLogger(__name__)


def _resolve_helpers(site_module_path):
    """Return (get_records, get_url) functions resolved in this order:
    1) src.app module attributes (if callable)
    2) top-level main module attributes (if callable) -- tests may patch this
    3) site-specific scraper module (imported dynamically)

    Raises ImportError if site module cannot be imported when needed.
    """
    get_records_fn = None
    get_url_fn = None

    # 1) src.app
    try:
        import src.app as src_app

        if callable(getattr(src_app, "get_records", None)):
            get_records_fn = getattr(src_app, "get_records")
        if callable(getattr(src_app, "get_url", None)):
            get_url_fn = getattr(src_app, "get_url")
    except Exception:
        pass

    # 2) main module (tests sometimes monkeypatch main)
    try:
        import importlib

        main_mod = importlib.import_module("main")
        if get_records_fn is None and callable(getattr(main_mod, "get_records", None)):
            get_records_fn = getattr(main_mod, "get_records")
        if get_url_fn is None and callable(getattr(main_mod, "get_url", None)):
            get_url_fn = getattr(main_mod, "get_url")
    except Exception:
        pass

    # 3) fallback to site-specific scraper for missing functions
    if get_records_fn is None or get_url_fn is None:
        module = __import__(site_module_path, fromlist=["*"])
        if get_records_fn is None and hasattr(module, "get_records"):
            get_records_fn = getattr(module, "get_records")
        if get_url_fn is None and hasattr(module, "get_url"):
            get_url_fn = getattr(module, "get_url")

    return get_records_fn, get_url_fn


# Shared validation helpers
def _validate_date_params(day, month, year):
    """Validate and parse day/month/year. Returns tuple:
    (error_message_or_None, day_i, month_i, year_i)
    """
    if not (day and month and year):
        return (
            "Missing one or more required parameters: day, month, year",
            None,
            None,
            None,
        )

    try:
        day_i = int(day)
        month_i = int(month)
        year_i = int(year)
    except ValueError:
        return "Parameters day, month and year must be integers", None, None, None

    if not (1 <= day_i <= 31 and 1 <= month_i <= 12 and 1900 <= year_i <= 2100):
        return "Parameters out of reasonable range", None, None, None

    return None, day_i, month_i, year_i


def _validate_paging_params(limit_param, offset_param):
    """Validate limit/offset query params. Returns (limit, offset, error)
    On success: (limit_int_or_None, offset_int, None)
    On error: (None, None, error_message)
    """
    limit = None
    offset = 0

    if limit_param is not None:
        try:
            limit = int(limit_param)
        except ValueError:
            return None, None, "Parameter 'limit' must be an integer"
        if limit < 0:
            return None, None, "Parameter 'limit' must be >= 0"

    if offset_param is not None:
        try:
            offset = int(offset_param)
        except ValueError:
            return None, None, "Parameter 'offset' must be an integer"
        if offset < 0:
            return None, None, "Parameter 'offset' must be >= 0"

    return limit, offset, None


def _validate_date_range_params(start_date_str, end_date_str):
    """Validate optional ISO start_date and end_date strings.

    Returns tuple: (error_or_None, start_date_or_None, end_date_or_None)
    Dates are returned as datetime.date objects.
    """
    if not start_date_str and not end_date_str:
        return None, None, None

    from datetime import date

    def _parse(s):
        try:
            # Accept YYYY-MM-DD or full ISO datetime
            from datetime import datetime

            try:
                return datetime.fromisoformat(s).date()
            except Exception:
                return date.fromisoformat(s[:10])
        except Exception:
            return None

    start_date = None
    end_date = None

    if start_date_str:
        start_date = _parse(start_date_str)
        if start_date is None:
            return "Parameter 'start_date' must be ISO format YYYY-MM-DD", None, None

    if end_date_str:
        end_date = _parse(end_date_str)
        if end_date is None:
            return "Parameter 'end_date' must be ISO format YYYY-MM-DD", None, None

    if start_date and end_date and start_date > end_date:
        return "Parameter 'start_date' must be <= 'end_date'", None, None

    return None, start_date, end_date
