# Throwaway copy ONLY: a fake demo buyer for the video, and a session for the demo baker (whose password is unusable).
import json
import secrets

from core.safety import assert_throwaway

assert_throwaway()  # its own database AND its own media folder, or refuse

from django.contrib.auth import BACKEND_SESSION_KEY, HASH_SESSION_KEY, SESSION_KEY  # noqa: E402
from django.contrib.sessions.backends.db import SessionStore  # noqa: E402

from accounts.models import Address, User  # noqa: E402
from catalog.models import Seller  # noqa: E402

pw = "Video-" + secrets.token_urlsafe(12)
buyer, created = User.objects.get_or_create(email="video-asha@example.test", defaults={"name": "Asha Demo"})
buyer.set_password(pw)
buyer.save()
if not buyer.addresses.exists():
    Address.objects.create(user=buyer, name="Asha Demo", phone="9800000001", line1="12 Demo Lane, Koramangala",
                           city="Bengaluru", pincode="560034")


def session_for(user):
    s = SessionStore()
    s[SESSION_KEY] = str(user.pk)
    s[BACKEND_SESSION_KEY] = "django.contrib.auth.backends.ModelBackend"
    s[HASH_SESSION_KEY] = user.get_session_auth_hash()
    s.create()
    return s.session_key


baker = Seller.objects.get(slug="lakshmis-kitchen").owner
out = {"buyer": {"email": buyer.email, "password": pw}, "baker_session": session_for(baker)}
# Never derive paths from __file__ here: inside manage.py shell it is Django's own shell.py.
open(r"C:/Users/rasmi/AppData/Local/Temp/claude/C--Users-rasmi-homehaat/36531e30-b328-44a7-9d80-4ec86169daa7/scratchpad/video_logins.json", "w").write(json.dumps(out))
print("ready")
