import datetime
from django.utils import timezone
from datetime import timedelta
import secrets
import ssl
import threading
import stripe
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.transaction import atomic
from django.utils.translation import gettext_lazy as _

from mail_sender import send_mail_from_mailjet
from .managers import CustomUserManager, UserPersonManager, OwnerPersonManager, RiderPersonManager, Roles, OrderManager


class Person(AbstractUser):
    username = None
    email = models.EmailField(_("email address"), unique=True)
    role = models.CharField(max_length=100, choices=Roles.choices, default=Roles.NONE)
    phone = models.CharField(max_length=25, blank=True, default='')

    is_available_for_ride = models.BooleanField(default=False)
    ride_count = models.IntegerField(default=0)
    profile_picture = models.ImageField(upload_to="profile_pics/", blank=True, null=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    class Meta:
        indexes = [
            models.Index(fields=['role']),
        ]

    def __str__(self):
        return self.email

    @property
    def is_restaurant_owner(self):
        return self.role == Roles.RESTAURANT_OWNER

    @property
    def is_rider(self):
        return self.role == Roles.RIDER

    @property
    def is_user(self):
        return self.role == Roles.USER

    def get_location(self):
        location: Location = Location.objects.filter(entity=self).last()
        if location and location.location_in_string:
            return location.location_in_string
        else:
            return ''

    def get_latitude(self):
        location: Location = Location.objects.filter(entity=self).last()
        if location and location.latitude:
            return location.latitude
        else:
            return ''

    def get_longitude(self):
        location: Location = Location.objects.filter(entity=self).last()
        if location and location.longitude:
            return location.longitude
        else:
            return ''

    def get_location_object(self):
        location: Location = Location.objects.get_or_create(entity=self)[0]
        return location

    def get_reset_url(self):
        token_object = PasswordReset.objects.get_or_create(person=self)[0]
        token_object.reset_token = secrets.token_urlsafe(128)
        token_object.save()

        return settings.SERVER_DOMAIN + f'reset/{token_object.reset_token}'

    def send_password_reset_email(self):
        def send_mail_func():
            print(f'sending email to {self.email}...')
            body = f'''\
Thank You for Your Request. Please Goto this link to reset your password:{self.get_reset_url()}
'''
            try:
                send_mail_from_mailjet(
                    to_addr=self.email,
                    to_name=self.first_name,
                    subject="Password Reset Email",
                    content=body,
                )

            except Exception as e:
                print(f"Error: {e}")

        email_sending_thread = threading.Thread(target=send_mail_func, )
        email_sending_thread.start()


class User(Person):
    class Meta:
        proxy = True

    objects = UserPersonManager()

    def save(self, *args, **kwargs):
        self.role = Roles.USER

        super(User, self).save(*args, **kwargs)

    def okay_for_first_order(self):
        if self.phone == '':
            return False

        if self.get_location() == '':
            return False

        return True


class Owner(Person):
    class Meta:
        proxy = True

    objects = OwnerPersonManager()

    def save(self, *args, **kwargs):
        self.role = Roles.RESTAURANT_OWNER
        super(Owner, self).save(*args, **kwargs)


class Rider(Person):
    class Meta:
        proxy = True

    objects = RiderPersonManager()

    def save(self, *args, **kwargs):
        self.role = Roles.RIDER
        super(Rider, self).save(*args, **kwargs)

    def __str__(self):
        return self.email + " " + str(self.ride_count)


class Restaurant(models.Model):
    owner = models.OneToOneField(Owner, on_delete=models.CASCADE)
    name = models.CharField(max_length=100, blank=True, default='')
    opens_at = models.TimeField(default='00:00:00')
    closes_at = models.TimeField(default='00:00:00')
    phone = models.CharField(max_length=20, blank=True, default='')
    phone2 = models.CharField(max_length=20, blank=True, default='')
    total_rating = models.IntegerField(default=0)
    total_rating_population = models.IntegerField(default=0)
    average_rating = models.FloatField(default=0)
    restaurant_image = models.ImageField(upload_to='restaurant_images/', null=True, blank=True)
    is_published = models.BooleanField(default=False)
    minimum_order_amount = models.PositiveIntegerField(default=0)

    class Meta:
        indexes = [
            models.Index(fields=['owner']),
        ]

    def __str__(self):
        return self.name + " owned by " + self.owner.email

    def is_out_of_service(self):
        current_time = datetime.datetime.now().time()

        if self.opens_at < self.closes_at:
            if current_time < self.opens_at or current_time > self.closes_at:
                return True
        else:
            # Service is open overnight
            if self.opens_at > current_time > self.closes_at:
                return True
        return False

    def is_publishable(self):
        if self.name and \
                self.phone and \
                self.phone2 and \
                self.restaurant_image:
            return True
        return False

    def get_location(self):
        return self.owner.get_location()

    def get_latitude(self):
        return self.owner.get_latitude()

    def get_longitude(self):
        return self.owner.get_longitude()

    def get_location_object(self):
        return self.owner.get_location_object()

    def get_delivery_zones(self):
        return DeliveryZone.objects.filter(restaurant=self)

    def get_delivery_fee(self, user_lat, user_lng):
        import math
        zones = list(self.get_delivery_zones())
        if not zones:
            return 50
        def haversine(lat1, lng1, lat2, lng2):
            R = 6371
            d_lat = math.radians(float(lat2) - float(lat1))
            d_lng = math.radians(float(lng2) - float(lng1))
            a = (math.sin(d_lat/2)**2 +
                 math.cos(math.radians(float(lat1))) *
                 math.cos(math.radians(float(lat2))) *
                 math.sin(d_lng/2)**2)
            return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        nearest = min(zones, key=lambda z: haversine(user_lat, user_lng, z.latitude, z.longitude))
        return nearest.delivery_fee
    
    def set_rating(self, rating: int):
        self.total_rating += rating
        self.total_rating_population += 1
        self.save()

        if self.total_rating and self.total_rating_population:
            self.avg_rating = round(self.total_rating / self.total_rating_population, 1)
            self.save()


class DeliveryZone(models.Model):
    latitude = models.DecimalField(max_digits=9, decimal_places=6, default=0)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, default=0)
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE)
    location_in_string = models.CharField(max_length=500, blank=True, default='')
    delivery_fee = models.PositiveIntegerField(default=50)

    class Meta:
        indexes = [
            models.Index(fields=['restaurant'])
        ]

    def __str__(self):
        return str(self.restaurant.name) + ' -> ' + self.location_in_string + f'[{self.latitude}, {self.longitude}]'


class Location(models.Model):
    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    entity = models.ForeignKey(Person, on_delete=models.CASCADE)
    location_in_string = models.CharField(max_length=500, blank=True, null=True, default='')  # ← added null=True

    class Meta:
        indexes = [
            models.Index(fields=['entity']),
        ]

    def __str__(self):
        return str(self.entity.email) + " -> " + str(self.latitude) + " " + str(self.longitude)


class Wallet(models.Model):
    entity = models.OneToOneField(Person, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True, default=0)

    class Meta:
        indexes = [
            models.Index(fields=['entity']),
        ]

    def __str__(self):
        return self.entity.email + " -> " + str(self.amount)


class OrderStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    PREPARING = 'PREPARING', 'Preparing'
    RIDER_ASSIGNED = 'RIDER_ASSIGNED', 'Rider Assigned'
    RIDER_ON_WAY = 'RIDER_ON_WAY', 'Rider On Way'
    DELIVERED = 'DELIVERED', 'Delivered'
    CANCELLED = 'CANCELLED', 'Cancelled'


class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="User")
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, null=True, blank=True)
    rider = models.ForeignKey(Rider, on_delete=models.SET_NULL, related_name="Rider", null=True, blank=True)
    status = models.CharField(max_length=100, choices=OrderStatus.choices, default=OrderStatus.PREPARING)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    is_rated = models.BooleanField(default=False)

    rider_otp = models.IntegerField(blank=True, null=True)
    user_otp = models.IntegerField(blank=True, null=True)
    assigned_at = models.DateTimeField(blank=True, null=True)
    rider_rejected_at = models.DateTimeField(blank=True, null=True)
    last_rejected_rider = models.ForeignKey('Rider', on_delete=models.SET_NULL, null=True, blank=True, related_name='rejected_orders')
    cancellation_reason = models.CharField(max_length=255, blank=True, default='')
    rider_assignment_attempts = models.PositiveIntegerField(default=0)

    _total_amount = None
    objects = OrderManager()

    def is_rider_chat_open(self):
        if self.status in (OrderStatus.PREPARING, OrderStatus.RIDER_ASSIGNED, OrderStatus.RIDER_ON_WAY):
            return True
        return False

    def get_status(self):
        return OrderStatus(self.status).label

    def mark_as_accepted(self):
        self.status = OrderStatus.PREPARING
        self.save()
    
    def mark_as_rider_on_way(self):
        self.status = OrderStatus.RIDER_ON_WAY
        self.save()
    def assign_rider(self, rider):
        self.rider = rider
        self.status = OrderStatus.RIDER_ASSIGNED
        self.assigned_at = timezone.now()
        self.rider_assignment_attempts += 1
        self.save()

    def accept_by_rider(self):
        self.status = OrderStatus.RIDER_ON_WAY
        self.assigned_at = None
        self.save()

    def reject_by_rider(self):
        self.last_rejected_rider = self.rider
        self.rider = None
        self.status = OrderStatus.PREPARING
        self.assigned_at = None
        self.rider_rejected_at = timezone.now()
        self.save()
    
    def check_and_escalate_timeout(self):
        if self.status in (OrderStatus.DELIVERED, OrderStatus.CANCELLED):
            return None

        now = timezone.now()

        if self.status == OrderStatus.PENDING:
            if self.created_at and (now - self.created_at) > timedelta(minutes=5):
                self.mark_as_cancelled(reason="The restaurant did not respond in time.")
                return 'auto_cancelled'

        if self.status == OrderStatus.RIDER_ASSIGNED:
            if self.assigned_at and (now - self.assigned_at) > timedelta(minutes=2):
                rejecting_rider = self.rider
                self.reject_by_rider()
                if self.rider_assignment_attempts < 3:
                    reassigned = assign_nearest_rider(self, exclude_rider=rejecting_rider)
                    if reassigned is None:
                        self.cancellation_reason = ""
                        self.save()
                    return 'rider_timeout_reassigned' if reassigned else 'no_rider_available'
                else:
                    self.mark_as_cancelled(reason="No riders are currently available in your area. We tried multiple times but couldn't find a rider.")
                    return 'auto_cancelled_max_attempts'

        if self.status == OrderStatus.PREPARING and not self.rider:
            if self.rider_rejected_at:
                if (now - self.rider_rejected_at) > timedelta(seconds=30):
                    if self.rider_assignment_attempts < 3:
                        reassigned = assign_nearest_rider(self, exclude_rider=self.last_rejected_rider)
                        if reassigned:
                            self.rider_rejected_at = None
                            self.save()
                            return 'reassigned_after_rejection'
                        else:
                            self.mark_as_cancelled(reason="No riders are currently available in your area. We tried multiple times but couldn't find a rider.")
                            return 'auto_cancelled_no_rider'
                    else:
                        self.mark_as_cancelled(reason="No riders are currently available in your area. We tried multiple times but couldn't find a rider.")
                        return 'auto_cancelled_no_rider'
            else:
                # No rider ever assigned and no rejection — stuck in PREPARING
                # Cancel after 15 minutes if no rider found
                if self.created_at and (now - self.created_at) > timedelta(minutes=15):
                    self.mark_as_cancelled(reason="No riders were available in your area at this time. Please try ordering again.")
                    return 'auto_cancelled_no_rider_available'

        return None

    def mark_as_rejected(self):
        with atomic():
            transaction = Transaction.objects.get(order=self)
            transaction.status = TransactionStatus.REJECTED
            transaction.save()
            self.status = OrderStatus.CANCELLED
            self.cancellation_reason = "The restaurant rejected your order."
            self.save()

    def mark_as_stripe_payment_succeeded(self):
        with atomic():
            transaction = Transaction.objects.get(order=self)
            transaction.status = TransactionStatus.ACCEPTED
            transaction.save()

    def mark_as_delivered(self):
        with atomic():
            transaction = Transaction.objects.get(order=self)
            transaction.status = TransactionStatus.ACCEPTED
            transaction.save()
            self.status = OrderStatus.DELIVERED
            self.save()
            if self.rider:
                self.rider.ride_count += 1
                self.rider.save()

    def mark_as_cancelled(self, reason=''):
        with atomic():
            transaction = Transaction.objects.get(order=self)
            transaction.status = TransactionStatus.REJECTED
            transaction.save()
            self.status = OrderStatus.CANCELLED
            self.cancellation_reason = reason
            self.save()

    def get_ordered_items(self):
        items = OrderedItem.objects.filter(order=self)
        return items

    def rate_items(self, rating: int):
        if self.is_rated:
            return False

        items = self.get_ordered_items()
        self.is_rated = True
        self.save()
        for ordered_item in items:
            ordered_item.item.save_rating(rating)

    def handle_stripe_dependency(self):
        items = self.get_ordered_items()
        for item in items:
            item.item.get_stripe_price_id()

    def get_status_color(self):
        if self.status == OrderStatus.RIDER_ASSIGNED:
            return 'info'
        if self.status == OrderStatus.PREPARING:
            return 'primary'

        if self.status == OrderStatus.RIDER_ON_WAY:
            return 'warning'

        if self.status == OrderStatus.DELIVERED:
            return 'success'

        if self.status == OrderStatus.CANCELLED:
            return 'danger'

    def send_email_to_user_notifying_of_order(self, payment_url='Cash On Delivery'):
        def send_mail_func():
            print(f'sending email to {self.user.email}...')
            body = f'''\
Congratulations on placing your order with FreshBite! Your order ID is {self.id}. We're \
thrilled to have you as a customer and can't wait for you to enjoy your meal. Our team is dedicated to \
delivering fresh, delicious food right to your door. Thank you for choosing FreshBite, and bon appétit!
Your STRIPE PAYMENT URL: {payment_url}
'''

            try:
                send_mail_from_mailjet(
                    to_addr=self.user.email,
                    to_name=self.user.first_name,
                    subject="Successfully Placed Order",
                    content=body,
                )

            except Exception as e:
                print(f"Error: {e}")

        email_sending_thread = threading.Thread(target=send_mail_func, )
        email_sending_thread.start()

    def total_amount(self):
        if self._total_amount is None:
            items = OrderedItem.objects.filter(order=self)
            amount = 0

            for item in items:
                amount += item.item.price * item.quantity

            self._total_amount = amount

        return self._total_amount

    def __str__(self):
        return (
                str(self.restaurant.owner.email) + " -> "
                + (self.rider.email if self.rider else "Unassigned") + " -> "
                + str(self.user.email) + " -> "
                + str(self.status)
        )

def assign_nearest_rider(order: 'Order', exclude_rider=None):
    import math
    from django.utils import timezone
    from datetime import timedelta
    from django.db import transaction as db_transaction

    with db_transaction.atomic():
        # Lock order row to prevent double assignment
        try:
            locked_order = Order.objects.select_for_update().get(pk=order.pk)
        except Order.DoesNotExist:
            return None

        # Don't assign if already assigned or delivered
        if locked_order.status in (OrderStatus.RIDER_ASSIGNED, OrderStatus.RIDER_ON_WAY,
                                    OrderStatus.DELIVERED, OrderStatus.CANCELLED):
            return None

        # Exclude busy riders (active in last 2 hours)
        busy_rider_ids = Order.objects.filter(
            status__in=[OrderStatus.RIDER_ASSIGNED, OrderStatus.RIDER_ON_WAY],
            assigned_at__gte=timezone.now() - timedelta(hours=2)
        ).exclude(rider=None).values_list('rider_id', flat=True)

        available_riders = Rider.objects.filter(
            is_available_for_ride=True
        ).exclude(pk__in=busy_rider_ids)

        if exclude_rider:
            available_riders = available_riders.exclude(pk=exclude_rider.pk)

        if locked_order.last_rejected_rider:
            available_riders = available_riders.exclude(pk=locked_order.last_rejected_rider.pk)

        if not available_riders.exists():
            print(f"[assign_nearest_rider] No available riders for Order #{order.pk}")
            return None

        restaurant_lat = order.restaurant.get_latitude()
        restaurant_lng = order.restaurant.get_longitude()
        delivery_zones = list(DeliveryZone.objects.filter(restaurant=order.restaurant))

        print(f"[assign_nearest_rider] Restaurant: {order.restaurant.name}")
        print(f"[assign_nearest_rider] Zones: {len(delivery_zones)}")

        def haversine(lat1, lng1, lat2, lng2):
            R = 6371
            d_lat = math.radians(float(lat2) - float(lat1))
            d_lng = math.radians(float(lng2) - float(lng1))
            a = (math.sin(d_lat/2)**2 +
                 math.cos(math.radians(float(lat1))) *
                 math.cos(math.radians(float(lat2))) *
                 math.sin(d_lng/2)**2)
            return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

        def rider_in_zone(rider):
            r_lat = rider.get_latitude()
            r_lng = rider.get_longitude()
            if not r_lat or not r_lng:
                print(f"  [zone] {rider.email} — no location")
                return False
            if not delivery_zones:
                if not restaurant_lat or not restaurant_lng:
                    return True
                dist = haversine(r_lat, r_lng, restaurant_lat, restaurant_lng)
                result = dist <= 15
                print(f"  [zone] {rider.email} — {dist:.1f}km from restaurant, allowed: {result}")
                return result
            for zone in delivery_zones:
                if not zone.latitude or not zone.longitude:
                    continue
                dist = haversine(r_lat, r_lng, zone.latitude, zone.longitude)
                print(f"  [zone] {rider.email} — {dist:.1f}km from zone {zone.location_in_string}")
                if dist <= 15:
                    return True
            return False

        zone_riders = [r for r in available_riders if rider_in_zone(r)]
        print(f"[assign_nearest_rider] Zone riders: {[r.email for r in zone_riders]}")

        if not zone_riders:
            print(f"[assign_nearest_rider] No zone riders — Order #{order.pk} cannot be assigned")
            return None

        if not restaurant_lat or not restaurant_lng:
            order.assign_rider(zone_riders[0])
            return zone_riders[0]

        best_rider = None
        best_distance = None

        for rider in zone_riders:
            r_lat = rider.get_latitude()
            r_lng = rider.get_longitude()
            if not r_lat or not r_lng:
                continue
            dist = haversine(r_lat, r_lng, restaurant_lat, restaurant_lng)
            if best_distance is None or dist < best_distance:
                best_distance = dist
                best_rider = rider

        if best_rider is None:
            best_rider = zone_riders[0]

        print(f"[assign_nearest_rider] Assigning {best_rider.email} to Order #{order.pk}")
        order.assign_rider(best_rider)
        return best_rider



class Menu(models.Model):
    name = models.CharField(max_length=100, blank=True, null=True)
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, null=True)

    class Meta:
        indexes = [
            models.Index(fields=['restaurant']),
        ]

    def __str__(self):
        return self.name


class MenuItem(models.Model):
    name = models.CharField(max_length=100, blank=True, null=True)
    menu = models.ForeignKey(Menu, on_delete=models.CASCADE)
    price = models.IntegerField(default=0)
    image = models.ImageField(upload_to='menu_items/', blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    stripe_price = models.CharField(max_length=100, default='', blank=True)
    total_rating = models.IntegerField(default=0)
    total_rating_population = models.IntegerField(default=0)
    average_rating = models.FloatField(default=0)
    is_available = models.BooleanField(default=True)

    class Meta:
        indexes = [
            models.Index(fields=['menu', 'name']),
        ]

    def __str__(self):
        return str(self.menu) + " -> " + self.name + " " + str(self.price)

    def get_stripe_price_id(self):
        if self.stripe_price == '':
            try:
                stripe.api_key = settings.STRIPE_SECRET_KEY
                response = stripe.Price.create(
                    currency="pkr",
                    unit_amount=self.price * 100,
                    product_data={"name": self.name},
                )

                self.stripe_price = response['id']
                self.save()

                # print(json.dumps(response, indent=4))

            except Exception as e:
                print("could not create stripe price")
                print(e)

        return self.stripe_price

    def save_rating(self, new_rating: int):
        self.total_rating += new_rating
        self.total_rating_population += 1
        self.save()
        if new_rating:
            self.average_rating = round(self.total_rating / self.total_rating_population, 1)
        self.save()

class ItemVariant(models.Model):
    item = models.ForeignKey(MenuItem, on_delete=models.CASCADE, related_name='variants')
    name = models.CharField(max_length=100)
    extra_price = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.item.name} - {self.name} (+Rs.{self.extra_price})"


class ItemAddon(models.Model):
    item = models.ForeignKey(MenuItem, on_delete=models.CASCADE, related_name='addons')
    name = models.CharField(max_length=100)
    extra_price = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.item.name} - {self.name} (+Rs.{self.extra_price})"


class CartItemVariant(models.Model):
    cart_item = models.OneToOneField('CartItem', on_delete=models.CASCADE, related_name='selected_variant')
    variant = models.ForeignKey(ItemVariant, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.cart_item} - {self.variant}"


class CartItemAddon(models.Model):
    cart_item = models.ForeignKey('CartItem', on_delete=models.CASCADE, related_name='selected_addons')
    addon = models.ForeignKey(ItemAddon, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.cart_item} - {self.addon}"

class OrderedItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    item = models.ForeignKey(MenuItem, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    variant_name = models.CharField(max_length=100, blank=True, default='')
    variant_extra = models.PositiveIntegerField(default=0)
    addon_summary = models.CharField(max_length=500, blank=True, default='')

    class Meta:
        indexes = [
            models.Index(fields=['order'])
        ]

    def get_item_total(self):
        return self.quantity * self.item.price

    def __str__(self):
        return str(self.item.name) + " -> " + str(self.quantity)


class Weekdays(models.TextChoices):
    SATURDAY = 'SATURDAY', 'Saturday'
    SUNDAY = 'SUNDAY', 'Sunday'
    MONDAY = 'MONDAY', 'Monday'
    TUESDAY = 'TUESDAY', 'Tuesday'
    WEDNESDAY = 'WEDNESDAY', 'Wednesday'
    THURSDAY = 'THURSDAY', 'Thursday'
    FRIDAY = 'FRIDAY', 'Friday'


class WeeklyHoliday(models.Model):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE)
    weekday = models.PositiveIntegerField(choices=Weekdays.choices)

    class Meta:
        indexes = [
            models.Index(fields=['restaurant']),
        ]


class ReviewTypes(models.TextChoices):
    RIDER = 'RIDER', 'Rider'
    FOOD = 'FOOD', 'Food'
    PLATFORM = 'PLATFORM', 'Platform'
    RESTAURANT = 'RESTAURANT', 'Restaurant'


class Review(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    review_type = models.CharField(max_length=100, choices=ReviewTypes.choices)
    message = models.TextField()
    rating = models.PositiveIntegerField(default=0)

    class Meta:
        indexes = [
            models.Index(fields=['order', 'review_type']),

        ]

    def __str__(self):
        return str(self.order) + " -> " + str(self.review_type)


class QNA(models.Model):
    question = models.TextField()
    answer = models.TextField()


class Feedback(models.Model):
    email = models.EmailField()
    message = models.TextField()


class TransactionStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    ACCEPTED = 'ACCEPTED', 'Accepted'
    REJECTED = 'REJECTED', 'Rejected'


class PaymentTypes(models.TextChoices):
    CASH_ON_DELIVERY = 'CASH_ON_DELIVERY', 'Cash on Delivery'
    STRIPE = 'STRIPE', 'Stripe'


class Transaction(models.Model):
    amount = models.IntegerField(default=0)
    status = models.CharField(max_length=100, choices=TransactionStatus.choices, default=TransactionStatus.PENDING)
    order = models.OneToOneField(Order, on_delete=models.CASCADE)
    payment_type = models.CharField(max_length=100, choices=PaymentTypes.choices)

    class Meta:
        indexes = [
            models.Index(fields=['order']),
        ]

    def __str__(self):
        return str(self.id) + " -> " + str(self.amount) + " -> " + str(self.status)

    def get_status(self):
        return TransactionStatus(self.status).label


class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE)
    payment_type = models.CharField(max_length=100, choices=PaymentTypes.choices, default=PaymentTypes.CASH_ON_DELIVERY)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'restaurant'])
        ]
        unique_together = ('user', 'restaurant')


    def get_cart_total(self):
        cart_items = CartItem.objects.filter(cart=self)


        total = 0


        for cart_item in cart_items:
            total += cart_item.get_item_total()


        return total


    def meets_minimum_order(self):
        minimum = self.restaurant.minimum_order_amount
        if minimum == 0:
            return True
        return self.get_cart_total() >= minimum


    def minimum_order_remaining(self):
        remaining = self.restaurant.minimum_order_amount - self.get_cart_total()
        return max(0, remaining)


    def __str__(self):
        return self.user.email + ' ' + self.payment_type + ' ' + str(self.get_cart_total())



class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE)
    item = models.ForeignKey(MenuItem, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)


    def increment(self):
        self.quantity += 1
        self.save()
        return self.quantity


    def decrement(self):
        if self.quantity > 1:
            self.quantity -= 1
            self.save()
        else:
            self.delete()
    
    def get_item_total(self):
        base = self.item.price
        try:
            variant_extra = self.selected_variant.variant.extra_price if self.selected_variant.variant else 0
        except CartItemVariant.DoesNotExist:
            variant_extra = 0
        addon_extra = sum(ca.addon.extra_price for ca in self.selected_addons.all())
        return self.quantity * (base + variant_extra + addon_extra)


    def add_to_order(self, order):
        ordered_item = OrderedItem.objects.create(
            order=order,
            item=self.item,
            quantity=self.quantity,
        )
        # Preserve variant name on the ordered item if selected
        try:
            if self.selected_variant and self.selected_variant.variant:
                ordered_item.variant_name = self.selected_variant.variant.name
                ordered_item.variant_extra = self.selected_variant.variant.extra_price
        except CartItemVariant.DoesNotExist:
            pass
        # Preserve addon names
        addon_names = []
        for ca in self.selected_addons.all():
            addon_names.append(f"{ca.addon.name} (+Rs.{ca.addon.extra_price})")
        ordered_item.addon_summary = ', '.join(addon_names)
        ordered_item.save()
        self.delete()

    class Meta:
        indexes = [
            models.Index(fields=['cart', 'item']),
            models.Index(fields=['cart'])
        ]

    def __str__(self):
        return str(self.item.name) + " -> " + str(self.quantity)


class StripeSuccessfulPaymentIntent(models.Model):
    payment_intent = models.CharField(max_length=200)

    class Meta:
        indexes = [
            models.Index(fields=['payment_intent']),
        ]

    def mark_as_paid_if_possible(self):
        stripe_checkout_session = StripeCheckoutSession.objects.filter(payment_intent=self.payment_intent).last()
        if stripe_checkout_session:
            order = stripe_checkout_session.order
            order.mark_as_stripe_payment_succeeded()

    def __str__(self):
        return str(self.payment_intent)


class StripeCheckoutSession(models.Model):
    payment_intent = models.CharField(max_length=200)
    order = models.OneToOneField(Order, on_delete=models.CASCADE, null=True)

    class Meta:
        indexes = [
            models.Index(fields=['payment_intent']),
            models.Index(fields=['order'])
        ]

    def mark_as_paid_if_possible(self):
        stripe_successful_payment_intent = StripeSuccessfulPaymentIntent.objects.filter(
            payment_intent=self.payment_intent).last()

        if stripe_successful_payment_intent:
            self.order.mark_as_stripe_payment_succeeded()

    def __str__(self):
        return str(self.payment_intent) + " -> " + str(self.order_id)


class ChatHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    query = models.TextField()
    reply = models.TextField()

    class Meta:
        indexes = [
            models.Index(fields=['user']),
        ]

    def __str__(self):
        return str(self.user) + " -> " + str(self.query) + " -> " + str(self.reply)


class Message(models.Model):
    sender = models.ForeignKey(Person, on_delete=models.CASCADE, related_name='sender')
    receiver = models.ForeignKey(Person, on_delete=models.CASCADE, related_name='receiver')
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    message_sent_at = models.DateTimeField(auto_now_add=True)
    text = models.TextField()

    class Meta:
        indexes = [
            models.Index(fields=['order']),
        ]

    def __str__(self):
        return str(self.sender) + " -> " + str(self.message_sent_at) + " -> " + str(self.text)


class PasswordReset(models.Model):
    person = models.ForeignKey(Person, on_delete=models.CASCADE)
    reset_token = models.CharField(max_length=300, default='34fasdfq43asdtq43afsasrjytu')
    last_update = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['created_at', 'reset_token']),
        ]

    def __str__(self):
        return str(self.person) + " -> " + str(self.last_update) + " -> " + str(self.reset_token)
