from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.user_login, name="login"),   #default page = login
    path('home/', views.home, name="home"),     #actual homepage
    path('login/', views.user_login, name="login"),
    path('signup/', views.signup, name="signup"),
    path('logout/', views.user_logout, name="logout"),
    path('add_edit_record/', views.add_edit_record, name="add_edit_record"),
    path('delete_record/', views.delete_record, name="delete_record"),
    path('user_status/', views.user_status, name="user_status"),
    path('get_dashboard_data/', views.get_dashboard_data, name="get_dashboard_data"),
    path('college_master/', views.college_master, name='college_master'),
    path('student_master/', views.student_master, name='student_master'),
    path('apply_filters/', views.apply_filters, name="apply_filters"),
    path('get_talukas/', views.get_talukas, name='get_talukas'),
    path('get_programs/', views.get_programs_for_discipline, name='get_programs'),
    path("get-college-data/", views.get_college_data_for_student_modal, name="get_college_data"),
    path("add_student/", views.add_student_aggregate, name="add_student_aggregate"),
    path("edit_student/", views.update_student_aggregate , name="update_student_aggregate"),
    path("get_student_records/", views.get_student_records, name="get_student_records"),
    path("delete-student-record/", views.delete_student_record, name="delete_student_record"),
    path('get-college-records/', views.get_college_records, name='get_college_records'),
    path("export-colleges-excel/", views.export_colleges_excel, name="export_colleges_excel"),
    path("export-student-excel/", views.export_student_excel, name="export_student_excel"),
    path('export_filtered_excel/', views.export_filtered_excel, name="export_filtered_excel"),

]