from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^issue/', views.issue, name='issue'),
]
