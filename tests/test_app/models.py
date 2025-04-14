from django.db import models


class Book(models.Model):
    """A book model."""

    name = models.CharField(max_length=200)
    author = models.CharField(max_length=200)
    rating = models.IntegerField(null=True, blank=True)
    published = models.BooleanField(default=True)

    def __str__(self):
        """Visual representation of instances."""
        return f"Book [{self.name}]"
