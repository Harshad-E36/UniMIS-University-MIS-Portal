from django.db import models

# Create your models here.

class Colleges(models.Model):
    College_Code = models.CharField(max_length=10)
    College_Name = models.CharField(max_length=80)
    address = models.TextField()
    country = models.CharField(max_length=20)
    state = models.CharField(max_length=20)
    District = models.CharField(max_length=20)
    taluka = models.CharField(max_length=20)
    city = models.CharField(max_length=20)
    college_type = models.CharField(max_length=50)
    belongs_to = models.CharField(max_length=40)
    affiliated = models.CharField(max_length=50)
    discipline = models.CharField(max_length=50)
    created_by = models.GenericIPAddressField(null=True, blank=True)
    updated_by = models.GenericIPAddressField(null=True, blank=True)

    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return self.College_Code
