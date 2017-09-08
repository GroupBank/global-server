from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^issue/', views.issue, name='issue'),
    url(r'^confirm/', views.confirm, name='confirm'),
]
