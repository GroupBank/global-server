from django.conf.urls import url

from . import views

app_name = 'group-servers'
urlpatterns = [
    url(r'^echo/', views.echo_group),
    url(r'^register-group/', views.register_group, name='register-group')
]
