from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.home, name="home"),
    path('get_records/',views.get_records, name='get_records'),
    path('add_edit_record/', views.add_edit_record, name="add_edit_record"),
    path('delete_record/', views.delete_record, name="delete_record"),
    path('signup/', views.signup, name="signup"),
    path('login/', views.user_login, name="login"),
    path('logout/', views.user_logout, name="logout"),
    path('user_status/', views.user_status, name="user_status"),
    path('college_master/', views.college_master, name='college_master'),
    path('apply_filters/', views.apply_filters, name="apply_filters"),
    path("clear_filters/", views.clear_filters, name="clear_filters"),

]