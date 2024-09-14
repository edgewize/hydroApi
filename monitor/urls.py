from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("screenshot/<str:timestamp>", views.screenshot, name="screenshot"),
    path("screenshot/<str:timestamp>/<str:name>", views.detection, name="detection"),
    path("detector/<str:name>", views.detector, name="detector"),
    path("screenshot_wave/", views.screenshot_wave, name="screenshot_wave"),
    path("batch_detect/", views.batch_detect, name="batch_detect"),
    path("load/", views.load, name="load")
]