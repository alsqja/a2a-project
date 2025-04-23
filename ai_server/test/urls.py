from django.urls import path

from test.views import TestView

urlpatterns = [
    path('', TestView.as_view(), name="hello"),
]