class AutoStrMixin:
    def __repr__(self):
        class_name = self.__class__.__name__

        field_names = [f.name for f in self._meta.fields]

        fields = ", ".join(f"{name}={getattr(self, name)!r}" for name in field_names)

        return f"{class_name}({fields})"
