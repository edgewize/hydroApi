from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("screenshot/", views.screenshots, name="screenshots"),
    path("screenshot/<str:timestamp>", views.screenshot, name="screenshot"),
    path("load/", views.load, name="load")
]