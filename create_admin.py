import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()
email = os.environ.get("DJANGO_SUPERUSER_EMAIL")
password = os.environ.get("DJANGO_SUPERUSER_PASSWORD")
username = os.environ.get("DJANGO_SUPERUSER_USERNAME")


if username and not User.objects.filter(username=username).exists():
    User.objects.create_superuser(
        email=email,
        password=password,
        username=username,

    )
    print("Superuser created")
else:
    print("Superuser already exists")