import json

from django.db import connections


def print_db_queries():
    queries = []

    for conn in connections.all():
        queries = queries + conn.queries

    print(json.dumps(queries, indent=4))
