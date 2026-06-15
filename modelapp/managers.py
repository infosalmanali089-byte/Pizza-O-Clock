import random
import re

from django.contrib.auth.base_user import BaseUserManager
from django.db import models, IntegrityError
from django.utils.translation import gettext_lazy as _


class Roles(models.TextChoices):
    USER = "user", "User"
    RIDER = "rider", "Rider"
    RESTAURANT_OWNER = "restaurant_owner", "Restaurant Owner"
    NONE = "none", "None"


class CustomUserManager(BaseUserManager):
    """
    Custom user model manager where email is the unique identifiers
    for authentication instead of usernames.
    """

    def create_user(self, email, password, **extra_fields):
        """
        Create and save a user with the given email and password.
        """

        email_regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b'
        if not email:
            raise ValueError(_("The Email must be set"))
        if not re.fullmatch(email_regex, email):
            raise ValueError(_("The Email must be in correct format"))
        try:
            email = BaseUserManager.normalize_email(email)
            user = self.model(email=email, **extra_fields)
            user.set_password(password)
            user.save()
        except IntegrityError:
            raise ValueError(_("Email already registered"))
        return user

    def create_superuser(self, email, password, **extra_fields):
        """
        Create and save a SuperUser with the given email and password.
        """
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError(_("Superuser must have is_staff=True."))
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(_("Superuser must have is_superuser=True."))
        return self.create_user(email, password, **extra_fields)


class UserPersonManager(CustomUserManager):
    def get_queryset(self):
        return super().get_queryset().filter(role=Roles.USER)


class OwnerPersonManager(CustomUserManager):
    def get_queryset(self):
        return super().get_queryset().filter(role=Roles.RESTAURANT_OWNER)


class RiderPersonManager(CustomUserManager):
    def get_queryset(self):
        return super().get_queryset().filter(role=Roles.RIDER)

    def get_rider(self):
        # Deprecated — use assign_nearest_rider() from modelapp.models instead
        riders = self.get_queryset().filter(is_available_for_ride=True).order_by('ride_count')
        if riders.exists():
            return riders[0]
        return None


class OrderManager(models.Manager):
    def create_order(self, user, restaurant, rider):
        order = self.model(
            user=user,
            restaurant=restaurant,
            rider=rider,
            rider_otp=random.randint(1000, 9999),
            user_otp=random.randint(1000, 9999),
        )
        order.save()
        return order
