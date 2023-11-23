from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("screenshot/", views.screenshots, name="screenshots"),
    path("screenshot/<str:timestamp>", views.screenshot, name="screenshot"),
    path("screenshot/<str:timestamp>/<str:model>", views.detection, name="detection"),
    path("load/", views.load, name="load")
]