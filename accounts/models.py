from django.db import models

class Store(models.Model):

    code = models.CharField(
        max_length=4,
        unique=True
    )

    password = models.CharField(
        max_length=100
    )

    def __str__(self):
        return self.code