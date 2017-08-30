from django.conf.urls import include, url

from .groups import views

app_name = 'rest'
urlpatterns = [
    url(r'^group/', include('rest_app.groups.urls', namespace='group'))
]
