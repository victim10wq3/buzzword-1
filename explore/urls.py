from django.urls import path

from buzzword.utils import management_handling


app_name = "explore"

if management_handling():
    urlpatterns = []
else:
    from . import views
    urlpatterns = [
        path("", views.explore, name="explore"),
        path("<str:slug>/", views.explore, name="explore"),
        path("upload", views.upload, name="upload"),
]
