from django.db import models


class Device(models.Model):
    status = models.JSONField(default=dict)

    def __str__(self):
        return str(self.pk)
