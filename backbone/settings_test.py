# backbone/settings_test.py
from .settings import *

# Loop through the databases defined in your base settings
# and force them all to run lightning-fast in RAM
for db_config in DATABASES.values():
    db_config["ENGINE"] = "django.db.backends.sqlite3"
    db_config["NAME"] = ":memory:"


# Your other test overrides remain the same
DEBUG = False
TESTING = True
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
