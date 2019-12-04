import os

from django.contrib.staticfiles.management.commands.runserver import Command as RunServerCommand
import explorer.parts.main

class Command(RunServerCommand):
   
    def run(self, **options):
        if os.environ.get('RUN_MAIN', False): # https://code.djangoproject.com/ticket/8085
            explorer.parts.main.load_corpora()
        super().run(**options)