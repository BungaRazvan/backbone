class BaseRouter:
    """A router to control all database operations on models in the
    auth and contenttypes applications."""

    route_app_labels = set()
    db_name = None

    def db_for_read(self, model, **hints):
        """Attempts to read auth and contenttypes models go to auth_db."""

        if model._meta.app_label in self.route_app_labels:
            return self.db_name

        return None

    def db_for_write(self, model, **hints):
        """Attempts to write auth and contenttypes models go to auth_db."""

        if model._meta.app_label in self.route_app_labels:
            return self.db_name

        return None

    def allow_relation(self, obj1, obj2, **hints):
        if (
            obj1._meta.app_label in self.route_app_labels
            or obj2._meta.app_label in self.route_app_labels
        ):
            return True

        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label in self.route_app_labels:
            return db == self.db_name

        return None
