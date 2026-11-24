import json

from django.core.serializers.json import DjangoJSONEncoder
from django.utils.html import format_html


class PrettyJsonAdmin:
    def format_json(self, obj, attr: str, indent: int = 4):
        payload = getattr(obj, attr)

        if not payload:
            return "-"

        pretty_str = json.dumps(payload, indent=indent, cls=DjangoJSONEncoder)

        return format_html(
            '<pre style="background: #1e1e1e; color: #dcdcdc; padding: 12px; border-radius: 6px; font-family: monospace; font-size: 13px; overflow-x: auto;">{}</pre>',
            pretty_str,
        )
