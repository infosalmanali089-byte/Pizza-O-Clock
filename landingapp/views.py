from collections import defaultdict
from datetime import timedelta
from math import radians, cos, sin, acos

from django.utils import timezone
from django.http import HttpResponse
from django.shortcuts import render, redirect

from modelapp.models import PasswordReset, Person, MenuItem
from .models import CoveredCity
from modelapp.managers import Roles


RADIUS_KM = 15


def get_distance_km(lat1, lon1, lat2, lon2):
    try:
        lat1, lon1, lat2, lon2 = map(radians, [float(lat1), float(lon1), float(lat2), float(lon2)])
        val = sin(lat1) * sin(lat2) + cos(lat1) * cos(lat2) * cos(lon2 - lon1)
        val = max(-1.0, min(1.0, val))
        return acos(val) * 6371
    except Exception:
        return 9999


def normalise(text):
    """Strip whitespace and lowercase for case-insensitive comparison."""
    return text.strip().lower() if text else ''


def landing_page(request):
    print(request.user)

    covered_cities = CoveredCity.objects.all()[:10]

    user_lat = None
    user_lng = None

    if request.user.is_authenticated:
        try:
            raw_lat = request.user.get_latitude()
            raw_lng = request.user.get_longitude()
            if raw_lat and raw_lng:
                user_lat = float(raw_lat)
                user_lng = float(raw_lng)
        except Exception:
            pass

    # Fetch all menu items with images, best-rated first
    all_items = MenuItem.objects.filter(
        image__isnull=False,
    ).exclude(image='').select_related(
        'menu', 'menu__restaurant', 'menu__restaurant__owner'
    ).order_by('-average_rating')

    # Filter to nearby restaurants if user has a location
    if user_lat and user_lng:
        filtered_items = []
        for item in all_items:
            try:
                rest_lat = item.menu.restaurant.get_latitude()
                rest_lng = item.menu.restaurant.get_longitude()
                if rest_lat and rest_lng:
                    dist = get_distance_km(user_lat, user_lng, rest_lat, rest_lng)
                    if dist <= RADIUS_KM:
                        filtered_items.append(item)
            except Exception:
                continue
        items_to_group = filtered_items
    else:
        items_to_group = list(all_items)

    # ── Group by normalised menu/category name ──────────────────────────
    # "pizza", "Pizza", "PIZZA" all map to the same group key.
    # display_name_map keeps the cleanest title-cased name for the heading.

    grouped_raw = defaultdict(list)   # normalised_name -> [items]
    display_name_map = {}             # normalised_name -> display name

    for item in items_to_group:
        menu_name = item.menu.name or ''
        key = normalise(menu_name)

        grouped_raw[key].append(item)

        # First item encountered sets the display name for this category
        if key not in display_name_map:
            display_name_map[key] = menu_name.strip().title()

    # ── Build food_groups — NO deduplication, show all items ───────────

    food_groups = []

    for norm_menu_name, items in grouped_raw.items():

        # Sort: highest rated first
        items.sort(key=lambda i: -i.average_rating)

        # Cap at 12 items per category
        items = items[:12]

        if not items:
            continue

        food_groups.append({
            'name': display_name_map[norm_menu_name],
            'items': items,
            'top_rating': items[0].average_rating,
        })

    # Rated categories first, then alphabetically
    food_groups.sort(key=lambda g: (-g['top_rating'], g['name'].lower()))

    context = {
        "covered_cities": covered_cities,
        "roles": Roles,
        "food_groups": food_groups,
        "user_has_location": bool(user_lat and user_lng),
    }

    return render(request, 'landing/landing.html', context)


def reset_password(request, reset_id):
    reset_obj = PasswordReset.objects.filter(
        last_update__gt=timezone.now() - timedelta(minutes=5),
        reset_token=reset_id
    ).last()

    if not reset_obj:
        return HttpResponse(status=404)

    if request.method == 'POST':
        password = request.POST.get('password')
        reset_obj.person.set_password(password)
        reset_obj.person.save()
        reset_obj.delete()
        return redirect('user:login')

    context = {
        'reset_id': reset_id,
        'person': reset_obj.person,
    }
    return render(request, 'landing/reset-password.html', context)


def request_reset_password(request):
    context = {}
    if request.method == 'POST':
        email = request.POST.get('email')
        person = Person.objects.filter(email__iexact=email).last()
        if person:
            person.send_password_reset_email()
            return render(request, 'landing/password-reset-request-successful.html')
        context['error'] = "Email Not Found"

    return render(request, 'landing/reqeust-reset-password.html', context)