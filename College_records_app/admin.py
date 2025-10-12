from django.contrib import admin
from .models import College, CollegeProgram, Discipline, Programs, District, Taluka

# Register your models here.

@admin.register(College)
class CollegeAdmin(admin.ModelAdmin):
    # Show these fields in the admin list view (table)
    list_display = ('College_Code', 'College_Name', 'created_at', 'updated_at')

    search_fields = ('College_Code', 'College_Name', 'city','District',)


@admin.register(District)
class DistrictAdmin(admin.ModelAdmin):
    list_display = ('id','DistrictName',)
    search_fields = ('DistrictName',)   
    
@admin.register(Taluka)
class TalukaAdmin(admin.ModelAdmin):    
    list_display = ('TalukaName', 'District')

@admin.register(Discipline)
class DisciplineAdmin(admin.ModelAdmin):
    list_display = ('id','DisciplineName')  

@admin.register(Programs)
class ProgramsAdmin(admin.ModelAdmin):  
    list_display = ('ProgramName', 'Discipline')


@admin.register(CollegeProgram)
class CollegeProgramAdmin(admin.ModelAdmin):
    list_display = ('College', 'Discipline', 'ProgramName')