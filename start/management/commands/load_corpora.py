import os

import explorer.main
from django.contrib.staticfiles.management.commands.runserver import (
    Command as RunServerCommand,
)


class Command(RunServerCommand):
    def run(self, **options):
        # https://code.djangoproject.com/ticket/8085
        explorer.main.load_corpora()