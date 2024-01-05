from django.urls import path

from . import api

urlpatterns = [
    path("screenshot/<str:url_timestamp>", api.screenshot, name="screenshot"),
    path("detection/<str:model>/<str:url_timestamp>", api.detection, name="detection"),
    path("detector/<str:name>", api.detector, name="detector"),
    path("flow", api.flow, name="flow")
]