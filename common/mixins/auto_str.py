class AutoStrMixin:
    def __repr__(self):
        class_name = self.__class__.__name__

        fields_list = []
        for f in self._meta.fields:
            # f.attname safely grabs the raw ID without hitting the DB
            # or triggering RelatedObjectDoesNotExist exceptions.
            val = getattr(self, f.attname)
            fields_list.append(f"{f.name}={val!r}")

        fields = ", ".join(fields_list)

        return f"{class_name}({fields})"
