from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("screenshot/", views.screenshots, name="screenshots"),
    path("screenshot/<str:timestamp>", views.screenshot, name="screenshot"),
    path("screenshot/<str:timestamp>/<str:name>", views.detection, name="detection"),
    path("detector/<str:name>", views.detector, name="detector"),
    path("load/", views.load, name="load")
]