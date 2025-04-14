from django.db import models


class Book(models.Model):
    name = models.CharField(max_length=200)
    author = models.CharField(max_length=200)
    rating = models.IntegerField(null=True, blank=True)
    published = models.BooleanField(default=True)

    def __unicode__(self):
        return f"Book [{self.name}]"
