
from django.db import models
from django.contrib.auth.models import User


class Newsletter(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    subscribe = models.BooleanField(default=False)

    class Meta:
        managed = True
        db_table = 'newsletter'


class WholeSale(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    license = models.TextField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'wholesale'


class SocialProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    full_name = models.TextField()
    username = models.TextField()
    userid = models.TextField()
    network = models.TextField()

    class Meta:
        managed = True
        db_table = 'social_profile'


class CreditCard(models.Model):
    user = models.BigIntegerField(null=False)
    card = models.TextField()
    type = models.TextField()
    holder = models.TextField()
    salt = models.BinaryField()

    class Meta:
        managed = True
        db_table = 'credit_card'

