from django.db import models


class License(models.Model):
    board = models.TextField()
    occupation = models.TextField()
    licensee = models.TextField()
    doing_business_as = models.TextField()
    cls = models.TextField()
    line1 = models.TextField()
    line2 = models.TextField()
    line3 = models.TextField()
    city = models.TextField()
    state = models.TextField()
    zipcode = models.TextField()
    county = models.TextField()
    license_number = models.TextField()
    primary_status = models.TextField()
    secondary_status = models.TextField()
    date_licensed = models.TextField()
    effective_date = models.TextField()
    expiration_date = models.TextField()
    military = models.TextField()
    alternate_license_number = models.TextField()

    class Meta:
            managed = True
            db_table = 'license'
