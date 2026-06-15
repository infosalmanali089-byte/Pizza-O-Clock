from django.contrib.auth import login, authenticate, logout
from django.db.transaction import atomic
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, redirect
from django.views import View

import datetime
from modelapp.models import Rider, Restaurant, Order, OrderedItem, OrderStatus, Transaction, Message, assign_nearest_rider
from rider.decorators import rider_required
from rider.forms import UpdateRiderForm


class LoginView(View):
    def get(self, request):
        logout(request)

        return render(request, 'rider/login.html')

    def post(self, request):
        email = request.POST.get('email')
        password = request.POST.get('password')

        rider = authenticate(email=email, password=password)
        if rider and rider.is_rider:
            login(request, rider)

            return redirect('landingapp:landing_page')

        return render(request, 'rider/login.html', {'error': 'Invalid email or password.'})


class RegisterView(View):
    def get(self, request: HttpRequest) -> HttpResponse:
        return render(request, 'rider/register.html')

    def post(self, request: HttpRequest) -> HttpResponse:
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        password = request.POST.get('password')

        try:
            rider = Rider.objects.create_user(first_name=first_name, last_name=last_name, email=email,
                                              password=password
                                              )
            return redirect('rider:login')
        except Exception as e:
            print(e)
            return render(request, 'rider/register.html', {'error': str(e)})


@rider_required
def respond_to_order(request: HttpRequest) -> HttpResponse:
    if request.method == 'POST':
        rider = Rider.objects.get(pk=request.user.id)
        order_pk = request.POST.get('order_pk')
        action = request.POST.get('action')

        order = Order.objects.filter(pk=order_pk, rider=rider, status=OrderStatus.RIDER_ASSIGNED).first()

        if order:
            if action == 'accept':
                order.accept_by_rider()
            elif action == 'reject':
                order.reject_by_rider()

    return redirect('rider:track_orders')

@atomic
@rider_required
def edit_profile(request: HttpRequest) -> HttpResponse:
    rider = Rider.objects.get(pk=request.user.id)
    location_object = rider.get_location_object()

    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        is_available_for_ride = request.POST.get('is_available_for_ride')

        rider.first_name = first_name
        rider.last_name = last_name
        rider.email = email
        rider.phone = phone
        rider.is_available_for_ride = is_available_for_ride or False
        rider.save()

        latitude = request.POST.get('latitude')
        longitude = request.POST.get('longitude')
        location_in_string = request.POST.get('location')



        location_object.latitude = latitude if latitude else 31.5204
        location_object.longitude = longitude if longitude else 74.3587
        location_object.location_in_string = location_in_string or ''
        location_object.save()

    context = {
        'rider': rider,
    }
    return render(request, 'rider/edit-profile.html', context)

@rider_required
def check_new_orders(request: HttpRequest):
    from django.http import JsonResponse
    rider = Rider.objects.get(pk=request.user.id)
    count = Order.objects.filter(rider=rider, status=OrderStatus.RIDER_ASSIGNED).count()
    return JsonResponse({'count': count})

@rider_required
def track_orders(request: HttpRequest) -> HttpResponse:
    rider = Rider.objects.get(pk=request.user.id)
    orders: list[Order] = Order.objects.filter(rider=rider).order_by('-pk')

    order_list = []

    if request.method == 'POST':
        order_pk = request.POST.get('order_pk')
        order_status = request.POST.get('order_status')

        order = Order.objects.get(pk=order_pk, rider=rider)

        if order_status == OrderStatus.RIDER_ON_WAY:
            order.mark_as_rider_on_way()
        if order_status == OrderStatus.DELIVERED:
             delivery_otp = request.POST.get('delivery_otp', '').strip()
             if order.user_otp and delivery_otp and str(order.user_otp) == delivery_otp:
                order.user_otp = None
                order.save()
                order.mark_as_delivered()
             else:
                for o in orders:
                    order_list.append({
                        'order': o,
                        'transaction': Transaction.objects.filter(order=o).first(),
                        'restaurant': o.restaurant,
                        'user': o.user,
                        'items': OrderedItem.objects.filter(order=o),
                        'otp_error': o.pk == order.pk,
                    })
                context = {
                    'order_list': order_list,
                    'rider': rider,
                    'empty_list': False,
                    'order_status': OrderStatus,
                }
                return render(request, 'rider/track-orders.html', context)

    for order in orders:
        order_list.append({
            'order': order,
            'transaction': Transaction.objects.filter(order=order).first(),
            'restaurant': order.restaurant,
            'user': order.user,
            'items': OrderedItem.objects.filter(order=order),
            'otp_error': False,
        })

    today = datetime.date.today()
    week_start = today - datetime.timedelta(days=today.weekday())

    delivered_orders = Order.objects.filter(rider=rider, status=OrderStatus.DELIVERED)

    deliveries_today = delivered_orders.filter(created_at__date=today).count()
    deliveries_this_week = delivered_orders.filter(created_at__date__gte=week_start).count()
    deliveries_total = delivered_orders.count()

    earnings_today = sum(o.total_amount() for o in delivered_orders.filter(created_at__date=today))
    earnings_this_week = sum(o.total_amount() for o in delivered_orders.filter(created_at__date__gte=week_start))
    earnings_total = sum(o.total_amount() for o in delivered_orders)

    context = {
        'order_list': order_list,
        'rider': rider,
        'empty_list': len(order_list) == 0,
        'order_status': OrderStatus,
        'deliveries_today': deliveries_today,
        'deliveries_this_week': deliveries_this_week,
        'deliveries_total': deliveries_total,
        'earnings_today': earnings_today,
        'earnings_this_week': earnings_this_week,
        'earnings_total': earnings_total,
    }
    return render(request, 'rider/track-orders.html', context)

@rider_required
def toggle_availability(request: HttpRequest) -> HttpResponse:
    if request.method == 'POST':
        rider = Rider.objects.get(pk=request.user.id)

        if rider.is_available_for_ride:
            active_orders = Order.objects.filter(
                rider=rider,
                status__in=[OrderStatus.RIDER_ASSIGNED, OrderStatus.RIDER_ON_WAY]
            )
            if active_orders.exists():
                return HttpResponse(status=409)

        rider.is_available_for_ride = not rider.is_available_for_ride
        rider.save()
        # return just the toggle snippet as plain HTML
        is_online = rider.is_available_for_ride
        from django.template.loader import render_to_string
        from django.middleware.csrf import get_token
        html = render_to_string('rider/track-orders.html', {
            'rider': rider,
            'csrf_token': get_token(request),
        }, request=request)
        # simpler: just return the small HTML fragment directly
        status_text = "You're Online" if is_online else "You're Offline"
        sub_text = "New orders will be assigned to you" if is_online else "You will not receive new orders"
        online_class = "is-online" if is_online else ""
        csrf = get_token(request)
        fragment = f"""
        <div id="availability-toggle" class="availability-card {online_class}">
            <div class="avail-left">
                <span class="avail-dot"></span>
                <div>
                    <div class="avail-title">{status_text}</div>
                    <div class="avail-sub">{sub_text}</div>
                </div>
            </div>
            <button class="avail-toggle-btn"
                    hx-post="/rider/toggle-availability/"
                    hx-target="#availability-toggle"
                    hx-swap="outerHTML"
                    hx-headers='{{"X-CSRFToken": "{csrf}"}}'>
                <span class="avail-switch"><span class="avail-knob"></span></span>
            </button>
        </div>
        """
        return HttpResponse(fragment, content_type='text/html')
    return HttpResponse(status=405)

@rider_required
def live_chat_with_user(request: HttpRequest, order_id: int) -> HttpResponse:
    order = Order.objects.get(pk=order_id)
    if not order.is_rider_chat_open():
        return redirect('rider:track_orders')
    sender = order.rider
    receiver = order.user

    context = {
        'order': order,
        'sender': sender,
        'receiver': receiver,
        'messages': Message.objects.filter(order=order),
    }
    if request.method == 'POST':
        message = Message.objects.create(
            sender=sender,
            receiver=receiver,
            text=request.POST.get('text'),
            order=order,
        )

        return HttpResponse(status=200)

    if request.method == 'GET' and request.GET.get('only-messages'):
        return render(request,'rider/user-chat-all-messages.html', context)

    return render(request, 'rider/live-chat-with-user.html', context)

def delete_account(request: HttpRequest):
    if request.method == 'POST':
        rider = Rider.objects.get(pk=request.user.id)
        logout(request)
        rider.delete()
        return redirect('landingapp:landing_page')
    return redirect('rider:edit_profile')