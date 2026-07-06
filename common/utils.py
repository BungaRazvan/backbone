import datetime


def get_api_key(request):
    """Retrieve API key from django request"""

    header_keys = ["X-API-KEY", "x-api-key", "HTTP_X_API_KEY"]

    for key in header_keys:
        value = request.headers.get(key)

        if value:
            return value

        value = request.META.get(key)

        if value:
            return value

    return None


def parse_uk_date_to_object(date_str):
    """Converts varying UK date text string formats into a Python datetime object."""

    if not date_str:
        return None

    clean_str = date_str.strip().replace(".", "")

    try:
        return datetime.datetime.strptime(clean_str, "%d %B %Y").date()
    except ValueError:
        pass

    try:
        return datetime.datetime.strptime(clean_str, "%d %b %Y").date()
    except ValueError:
        return None
