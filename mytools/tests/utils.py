from datetime import datetime, timezone


def ts(date_str: str) -> int:
    """
    Convert YYYY-MM-DD → unix timestamp (UTC)
    """
    return int(
        datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp()
    )


def yahoo_dividends(*entries):
    """
    entries = [
        {"date": "2024-12-15", "amount": 1.23, "payDate": "2024-12-20"},
        ...
    ]
    """
    return {
        "chart": {
            "result": [
                {
                    "events": {
                        "dividends": {
                            str(i): {
                                "date": ts(e["date"]),
                                "amount": e.get("amount", 0),
                                **(
                                    {"payDate": ts(e["payDate"])}
                                    if e.get("payDate")
                                    else {}
                                ),
                            }
                            for i, e in enumerate(entries)
                        }
                    }
                }
            ]
        }
    }
