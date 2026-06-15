import json
from modelapp.models import Rider
from django.conf import settings
from django.contrib.auth import login, authenticate, logout
from django.db.transaction import atomic
from django.http import HttpRequest
from django.shortcuts import render, redirect, resolve_url
from django.views import View
from modelapp.models import Owner, Restaurant, Menu, MenuItem, Order, OrderedItem, Location, DeliveryZone, assign_nearest_rider, OrderStatus
from restaurant.decorators import owner_required
from restaurant.forms import RestaurantForm, UpdateMenuItemForm


class LoginView(View):
    def get(self, request):
        logout(request)
        return render(request, 'restaurant/login.html')

    def post(self, request):
        email = request.POST.get('email')
        password = request.POST.get('password')

        owner = authenticate(email=email, password=password)

        if owner and owner.is_restaurant_owner:
            login(request, owner)
            return redirect('landingapp:landing_page')

        return render(request, 'restaurant/login.html', {'error': 'Invalid Credentials'})


class RegisterView(View):
    def get(self, request):
        return render(request, 'restaurant/register.html')

    def post(self, request):
        email = request.POST.get('email')
        password = request.POST.get('password')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')

        try:
            owner = Owner.objects.create_user(
                email=email, password=password,
                first_name=first_name, last_name=last_name
            )
            restaurant = Restaurant.objects.create(owner=owner)
            return redirect('restaurant:login')

        except Exception as e:
            print(e)
            return render(request, 'restaurant/register.html', {'error': str(e)})


@owner_required
def edit_restaurant(request: HttpRequest):
    owner = Owner.objects.get(pk=request.user.id)
    restaurant: Restaurant = Restaurant.objects.get(owner=owner)

    if request.method == 'POST':
        restaurant_form = RestaurantForm(request.POST, request.FILES, instance=restaurant)
        if restaurant_form.is_valid():
            restaurant = restaurant_form.save()

    context = {
        'restaurant': restaurant,
        'name': restaurant.name,
        'opens_at': restaurant.opens_at.strftime('%H:%M:%S'),
        'closes_at': restaurant.closes_at.strftime('%H:%M:%S'),
        'phone': restaurant.phone,
        'phone2': restaurant.phone2,
        'image_src': restaurant.restaurant_image.url if restaurant.restaurant_image else None,
    }

    return render(request, 'restaurant/edit-restaurant.html', context)


@owner_required
def change_restaurant_location(request: HttpRequest):
    if request.method == 'POST':
        latitude = request.POST.get('latitude')
        longitude = request.POST.get('longitude')
        location_in_string = request.POST.get('location_in_string')
        owner = Owner.objects.get(pk=request.user.id)

        # ✅ FIX: Save location against the OWNER (person) so the
        # nearby_restaurants SQL join (ON p.id = l.entity_id) finds it correctly.
        # Also store restaurant's latitude/longitude directly on the restaurant
        # so the raw query can use it without ambiguity.
        restaurant = Restaurant.objects.get(owner=owner)

        # Save to Location table linked to owner (for the raw SQL join)
        restaurant_location = Location.objects.get_or_create(entity=owner)[0]
        restaurant_location.latitude = latitude
        restaurant_location.longitude = longitude
        restaurant_location.location_in_string = location_in_string
        restaurant_location.save()

        # ✅ Also save lat/lng directly on the restaurant model if fields exist
        if hasattr(restaurant, 'latitude') and hasattr(restaurant, 'longitude'):
            restaurant.latitude = latitude
            restaurant.longitude = longitude
            restaurant.save()

    return redirect('restaurant:edit_restaurant')


@owner_required
def menus(request: HttpRequest):
    restaurant = Restaurant.objects.get_or_create(owner__pk=request.user.id)[0]
    menu_created = request.GET.get('menu_created')

    menu_objects: list[Menu] = Menu.objects.filter(restaurant=restaurant)

    menu_list = []

    for menu_object in menu_objects:
        menu = {
            'name': menu_object.name,
            'pk': menu_object.pk,
            'items': [
                item for item in MenuItem.objects.filter(menu=menu_object)
            ],
            'base': settings.MEDIA_URL
        }
        menu_list.append(menu)

    context = {
        'menu_list': menu_list,
        'show_menu_created_notification': menu_created,
        'restaurant': restaurant,
    }

    return render(request, 'restaurant/menu-list.html', context)


@owner_required
def add_menu(request: HttpRequest):
    if request.method == 'POST':
        name = request.POST.get('name')
        restaurant = Restaurant.objects.get_or_create(owner__pk=request.user.id)[0]

        menu = Menu.objects.create(
            restaurant=restaurant,
            name=name
        )

        return redirect(resolve_url('restaurant:menus') + '?menu_created=' + menu.name)

    return render(request, 'restaurant/add-menu.html')


@owner_required
def edit_menu(request: HttpRequest, pk: int):
    menu: Menu = Menu.objects.filter(pk=pk).last()

    if menu is None or menu.restaurant.owner.pk != request.user.pk:
        return redirect('restaurant:menus')

    if request.method == 'POST':
        item_pk = request.POST.get('item_pk')
        item = None
        if item_pk:
            item = MenuItem.objects.get(pk=item_pk)
            menu_item_form = UpdateMenuItemForm(request.POST, request.FILES, instance=item)
            print(request.FILES)
            if menu_item_form.is_valid():
                menu_item_form.save()
            else:
                print(menu_item_form.errors)
        else:
            item = MenuItem.objects.create(
                menu_id=pk,
                description=request.POST.get('description'),
                name=request.POST.get('name'),
                price=request.POST.get('price'),
                image=request.FILES.get('image'),
            )
        return render(request, 'restaurant/menu-item-view.html',
                      {'item': item, 'menu_pk': pk})

    context = {
        'name': menu.name,
        'menu_pk': menu.pk,
        'items': [
            item for item in MenuItem.objects.filter(menu=menu)
        ],
    }

    return render(request, 'restaurant/edit-menu.html', context)


@owner_required
def delete_menu(request: HttpRequest):
    if request.method == 'POST':
        pk = request.POST.get('pk')
        menu: Menu = Menu.objects.get(pk=pk)

        if menu.restaurant.owner.pk == request.user.pk:
            menu.delete()

    return redirect('restaurant:menus')


@owner_required
def delete_item(request: HttpRequest):
    if request.method == 'POST':
        pk = request.POST.get('pk')
        item: MenuItem = MenuItem.objects.get(pk=pk)

        if item.menu.restaurant.owner.pk == request.user.pk:
            item.delete()

    return redirect('restaurant:menus')

@owner_required
def check_new_orders(request: HttpRequest):
    from django.http import JsonResponse
    restaurant = Restaurant.objects.get_or_create(owner=request.user)[0]
    count = Order.objects.filter(restaurant=restaurant, status=OrderStatus.PENDING).count()
    return JsonResponse({'count': count})

@owner_required
def track_orders(request: HttpRequest):
    from modelapp.models import OrderStatus
    restaurant = Restaurant.objects.get_or_create(owner=request.user)[0]

    if request.method == 'POST':
        order_pk = request.POST.get('order_pk')
        action = request.POST.get('action')
        order = Order.objects.get(pk=order_pk, restaurant=restaurant)

        if action == 'accept':
            order.mark_as_accepted()
            assign_nearest_rider(order)
        elif action == 'reject':
            order.mark_as_rejected()
        elif action == 'retry_rider':
            assign_nearest_rider(order)

    for order in Order.objects.filter(restaurant=restaurant):
        if order.status not in (
            OrderStatus.RIDER_ON_WAY,
            OrderStatus.RIDER_ASSIGNED,
            OrderStatus.DELIVERED,
            OrderStatus.CANCELLED
        ):
            order.check_and_escalate_timeout()

    order_list = []
    orders = Order.objects.filter(restaurant=restaurant).order_by('-pk')

    for order in orders:
        order_list.append({
            'order': order,
            'items': OrderedItem.objects.filter(order=order),
        })

    context = {
        'order_list': order_list,
        'restaurant': restaurant,
        'empty_list': len(order_list) == 0,
        'order_status': OrderStatus,
    }

    return render(request, 'restaurant/track-orders.html', context)


@owner_required
def add_delivery_zone(request: HttpRequest):
    restaurant = Restaurant.objects.get(owner_id=request.user.id)

    if request.method == 'POST':
        latitude = request.POST.get('latitude2')
        longitude = request.POST.get('longitude2')
        location_in_string = request.POST.get('location_in_string2')

        DeliveryZone.objects.create(
            restaurant=restaurant,
            longitude=longitude,
            latitude=latitude,
            location_in_string=location_in_string,
        )

    return redirect('restaurant:edit_restaurant')

@owner_required
def manage_item_options(request: HttpRequest, item_pk: int):
    from modelapp.models import ItemVariant, ItemAddon
    item = MenuItem.objects.get(pk=item_pk)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'add_variant':
            ItemVariant.objects.create(
                item=item,
                name=request.POST.get('variant_name'),
                extra_price=request.POST.get('variant_price') or 0,
            )
        elif action == 'delete_variant':
            ItemVariant.objects.filter(pk=request.POST.get('variant_id'), item=item).delete()
        elif action == 'add_addon':
            ItemAddon.objects.create(
                item=item,
                name=request.POST.get('addon_name'),
                extra_price=request.POST.get('addon_price') or 0,
            )
        elif action == 'delete_addon':
            ItemAddon.objects.filter(pk=request.POST.get('addon_id'), item=item).delete()

    return redirect('restaurant:edit_menu', pk=item.menu.pk)
@owner_required
def toggle_item_availability(request: HttpRequest, item_pk: int):
    item = MenuItem.objects.get(pk=item_pk)
    if item.menu.restaurant.owner.pk == request.user.pk:
        item.is_available = not item.is_available
        item.save()
    return redirect('restaurant:edit_menu', pk=item.menu.pk)

@owner_required
def remove_delivery_zone(request: HttpRequest):
    if request.method == 'POST':
        delivery_zone_id = request.POST.get('delivery_zone_id')
        if delivery_zone_id:
            delivery_zone = DeliveryZone.objects.get(pk=delivery_zone_id)
            delivery_zone.delete()

    return redirect('restaurant:edit_restaurant')


@owner_required
def edit_menu(request: HttpRequest, pk: int):
    menu: Menu = Menu.objects.filter(pk=pk).last()

    if menu is None or menu.restaurant.owner.pk != request.user.pk:
        return redirect('restaurant:menus')

    # ── Handle rename from menu list ──
    if request.method == 'POST' and request.POST.get('rename'):
        new_name = request.POST.get('name', '').strip()
        if new_name:
            menu.name = new_name
            menu.save()
        from django.http import JsonResponse
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True})
        return redirect('restaurant:menus')

    # ── Handle add/edit item ──
    if request.method == 'POST':
        item_pk = request.POST.get('item_pk')
        item = None
        if item_pk:
            item = MenuItem.objects.get(pk=item_pk)
            menu_item_form = UpdateMenuItemForm(request.POST, request.FILES, instance=item)
            if menu_item_form.is_valid():
                menu_item_form.save()
            else:
                print(menu_item_form.errors)
        else:
            item = MenuItem.objects.create(
                menu_id=pk,
                description=request.POST.get('description'),
                name=request.POST.get('name'),
                price=request.POST.get('price'),
                image=request.FILES.get('image'),
            )
        return render(request, 'restaurant/menu-item-view.html',
                      {'item': item, 'menu_pk': pk})

    # ── GET — render edit menu page ──
    context = {
        'name': menu.name,
        'menu_pk': menu.pk,
        'items': [
            item for item in MenuItem.objects.filter(menu=menu)
        ],
    }

    return render(request, 'restaurant/edit-menu.html', context)
def delete_account(request: HttpRequest):
    if request.method == 'POST':
        owner = Owner.objects.get(pk=request.user.id)
        logout(request)
        owner.delete()
        return redirect('landingapp:landing_page')
    return redirect('restaurant:edit_restaurant')