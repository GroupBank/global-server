from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^issue/', views.issue, name='issue'),
    url(r'^confirm/', views.confirm, name='confirm'),
    url(r'^cancel/', views.cancel, name='cancel'),
    url(r'^get-pending/', views.get_pending, name='get-pending'),
    url(r'^accept/', views.accept, name='accept'),
    url(r'^get-totals/', views.get_totals, name='get-totals'),
]
