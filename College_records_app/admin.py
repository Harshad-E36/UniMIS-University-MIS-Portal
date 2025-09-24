from django.contrib import admin
from .models import Colleges

# Register your models here.

@admin.register(Colleges)
class CollegesAdmin(admin.ModelAdmin):
    # Show these fields in the admin list view (table)
    list_display = ('College_Code', 'College_Name', 'created_at', 'updated_at')

    search_fields = ('College_Code', 'College_Name', 'city','District',)