import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    pass


class Category(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=64)

class Auction(models.Model):
    id = models.IntegerField
    title = models.CharField(max_length=64)
    description = models.TextField(max_length=255)
    starting_bid = models.DecimalField(max_digits=6, decimal_places=2)
    photo_url = models.URLField(max_length=255)
    category = models.ForeignKey(
        'Category',
        on_delete=models.SET_NULL, 
        null=True
    )
    user = models.ForeignKey(
        'User',
        on_delete=models.CASCADE
    )
    created_at = models.DateTimeField(auto_now_add=True)