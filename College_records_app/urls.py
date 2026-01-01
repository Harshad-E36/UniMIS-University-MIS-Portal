from django.urls import path, include
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', views.user_login, name="login"),
    path('home/', views.home, name="home"),
    path('login/', views.user_login, name="login"),
    path('signup/', views.signup, name="signup"),
    path('logout/', views.user_logout, name="logout"),
    path('user_status/', views.user_status, name="user_status"),
    path('college_master/', views.college_master, name='college_master'),
    path('student_master/', views.student_master, name='student_master'),
    path('staff_master/', views.staff_master, name='staff_master'),
    path('add_edit_record/', views.add_edit_record, name="add_edit_record"),
    path('delete_record/', views.delete_record, name="delete_record"),
    path('get_dashboard_data/', views.get_dashboard_data, name="get_dashboard_data"),
    path('apply_filters/', views.apply_filters, name="apply_filters"),
    path('get_talukas/', views.get_talukas, name='get_talukas'),
    path('get_programs/', views.get_programs_for_discipline, name='get_programs'),
    path("get-college-data/", views.get_college_data_for_student_and_staff_modal, name="get_college_data"),
    path("add_student/", views.add_student_aggregate, name="add_student_aggregate"),
    path("edit_student/", views.update_student_aggregate , name="update_student_aggregate"),
    path("get_student_records/", views.get_student_records, name="get_student_records"),
    path("delete-student-record/", views.delete_student_record, name="delete_student_record"),
    path('get-college-records/', views.get_college_records, name='get_college_records'),
    path("export-colleges-excel/", views.export_colleges_excel, name="export_colleges_excel"),
    path("export-student-excel/", views.export_student_excel, name="export_student_excel"),
    path('export_filtered_excel/', views.export_dashboard_excel, name="export_filtered_excel"),
    path("get_staff_records/", views.get_staff_records, name="get_staff_records"),
    path("add_staff/", views.add_staff_aggregate, name="add_staff"),
    path("edit_staff/", views.update_staff_aggregate, name="edit_staff"),
    path("delete-staff-record/", views.delete_staff_record, name="delete_staff_record"),
    path("export-staff-excel/", views.export_staff_excel, name="export_staff_excel"),

    path('users/unassigned-json/', views.unassigned_users_json, name='unassigned_users_json'),
    path('change-password/', views.change_password, name='change_password'),

    path("api/academic-years/", views.get_academic_years, name="get_academic_years"),
    path("api/toggle-academic-year/", views.toggle_academic_year, name="toggle_academic_year"),

    # 🔐 Password reset (custom UI, same secure Django flow)
    path(
        "password-reset/",
        auth_views.PasswordResetView.as_view(
            template_name="auth/password_reset.html",
            email_template_name="auth/password_reset_email.txt",
            subject_template_name="auth/password_reset_subject.txt",
            success_url="/password-reset/done/"
        ),
        name="password_reset"
    ),

    path(
        "password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="auth/password_reset_done.html"
        ),
        name="password_reset_done"
    ),

    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="auth/password_reset_confirm.html",
            success_url="/reset/done/"
        ),
        name="password_reset_confirm"
    ),

    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="auth/password_reset_complete.html"
        ),
        name="password_reset_complete"
    ),

   
]