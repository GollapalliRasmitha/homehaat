"""
DATABASE_URL -> Django's DATABASES entry (production: Neon). Written here with the standard library, so no extra
package is needed. Locally DATABASE_URL is empty and settings.py keeps the Docker Postgres on port 5433.

Example: postgresql://user:p%40ss@ep-cool-name-123.ap-southeast-1.aws.neon.tech/neondb?sslmode=require
"""

from urllib.parse import parse_qsl, unquote, urlsplit

LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}
STRONG_SSL = {"require", "verify-ca", "verify-full"}


def database_from_url(url: str) -> dict:
    parts = urlsplit(url.strip())
    if parts.scheme not in ("postgres", "postgresql"):
        raise RuntimeError("DATABASE_URL must start with postgresql:// (copy it from Neon's Connect button).")
    host = parts.hostname or ""
    options = dict(parse_qsl(parts.query))
    # Neon needs encrypted connections. Default to "require", and never allow less for a database on the internet.
    if options.get("sslmode") not in STRONG_SSL and host not in LOCAL_HOSTS:
        options["sslmode"] = "require"
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": unquote(parts.path.lstrip("/")),
        "USER": unquote(parts.username or ""),
        "PASSWORD": unquote(parts.password or ""),
        "HOST": host,
        "PORT": str(parts.port or 5432),
        "OPTIONS": options,
        # Reuse a connection for a minute instead of opening one per request (Neon is a few ms away), and check it
        # still works first: Neon's free database sleeps after 5 idle minutes, which closes old connections.
        "CONN_MAX_AGE": 60,
        "CONN_HEALTH_CHECKS": True,
        # Neon's "-pooler" address goes through PgBouncer, which can't keep server-side cursors between queries.
        "DISABLE_SERVER_SIDE_CURSORS": "-pooler" in host,
    }
