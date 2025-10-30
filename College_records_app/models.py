from django.db import models
from django.utils import timezone
# Create your models here.


# static tables for college details (district and taluka)
class District(models.Model):
    DistrictName = models.CharField(max_length=50) 

    def __str__(self):
        return self.DistrictName
    
    

class Taluka(models.Model):
    District = models.ForeignKey(District, on_delete=models.CASCADE, related_name='talukas') # by adding District in parathesis of Taluka model to the primary key of the District model — which by default is an auto-generated integer field named id
    TalukaName = models.CharField(max_length=50)

    class Meta:
        unique_together = ('District', 'TalukaName')

    def __str__(self):
        return f"{self.TalukaName} ({self.District.DistrictName})"
    

# static tables for college details (discipline and programs)

class Discipline(models.Model):
    DisciplineName = models.CharField(max_length=50)

    def __str__(self):
        return self.DisciplineName

class Programs(models.Model):
    Discipline = models.ForeignKey(Discipline, on_delete=models.CASCADE, related_name='programs') # by adding Discipline in parathesis of Programs model to the primary key of the Discipline model — which by default is an auto-generated integer field named id
    ProgramName = models.CharField(max_length=150)

    class Meta:
        unique_together = ('Discipline', 'ProgramName')

    def __str__(self):
        return f"{self.ProgramName} ({self.Discipline.DisciplineName})"

class CollegeType(models.Model):
    CollegeTypeName = models.CharField(max_length=50)

    def __str__(self):
        return self.CollegeTypeName

class BelongsTo(models.Model):
    BelongsToName = models.CharField(max_length=50)

    def __str__(self):
        return self.BelongsToName


# College master table
class College(models.Model):
    College_Code = models.CharField(max_length=10)
    College_Name = models.CharField(max_length=80)
    address = models.TextField()
    country = models.CharField(max_length=20)
    state = models.CharField(max_length=20)
    District = models.CharField(max_length=20)
    taluka = models.CharField(max_length=20)
    city = models.CharField(max_length=20)
    pincode = models.CharField(max_length=10)
    college_type = models.CharField(max_length=50)
    belongs_to = models.CharField(max_length=40)
    affiliated = models.CharField(max_length=50)
    # discipline = models.CharField(max_length=50)
    created_by = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.GenericIPAddressField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return self.College_Code
    
# This Discipline and Programs table is for mapping the many to many relationship between College and Discipline and Programs

class CollegeProgram(models.Model):
    College = models.ForeignKey(College, on_delete=models.CASCADE, related_name='college_programs') # by adding College in parathesis of discipline_programs model to the primary key of the College model — which by default is an auto-generated integer field named id
    Discipline = models.CharField(max_length=50)
    ProgramName = models.CharField(max_length=50)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        unique_together = ('College','Discipline', 'ProgramName')

    def __str__(self):
        return f"({self.Discipline}) {self.ProgramName}"
    





