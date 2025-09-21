from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.home, name="home"),
    path('get_records',views.get_records, name='get_records'),
    path('add_edit_record/', views.add_edit_record, name="add_edit_record"),
    path('delete_record', views.delete_record, name="delete_record"),
]