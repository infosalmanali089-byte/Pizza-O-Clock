import json

import stripe
from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt

from modelapp.models import Order, StripeCheckoutSession, StripeSuccessfulPaymentIntent
from user.decorators import user_required

# Stripe does NOT support PKR natively.
# We charge in USD using an approximate exchange rate.
# 1 USD ≈ 280 PKR — update this value periodically if needed.
PKR_TO_USD_RATE = 280


def pkr_to_usd_cents(pkr_amount):
    """Convert a PKR amount to USD cents for Stripe (minimum 50 cents)."""
    usd = pkr_amount / PKR_TO_USD_RATE
    cents = int(usd * 100)
    return max(cents, 50)  # Stripe minimum is 50 cents USD


@user_required
def handle_stripe_payment(request, order_id):
    stripe.api_key = settings.STRIPE_SECRET_KEY

    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        return HttpResponse("<h1>Order not found. <a href='/'>Home</a></h1>", status=404)

    total_pkr = order.total_amount()

    if not total_pkr or total_pkr <= 0:
        return HttpResponse(
            "<h1>Order total is invalid. <a href='/'>Home</a></h1>",
            status=400
        )

    total_usd_cents = pkr_to_usd_cents(total_pkr)

    try:
        checkout_session = stripe.checkout.Session.create(
            line_items=[
                {
                    'price_data': {
                        'currency': 'usd',
                        'unit_amount': total_usd_cents,
                        'product_data': {
                            'name': f'Order #{order.id} — {order.restaurant.name}',
                            'description': f'Total: Rs.{total_pkr} PKR (~${total_usd_cents / 100:.2f} USD)',
                        },
                    },
                    'quantity': 1,
                }
            ],
            mode='payment',
            success_url=settings.SERVER_DOMAIN + "payment/success/",
            cancel_url=settings.SERVER_DOMAIN + "payment/failure/",
            metadata={
                'order_id': order_id,
            },
        )

        # Save checkout session immediately so the webhook can match it later
        StripeCheckoutSession.objects.get_or_create(
            order=order,
            defaults={'payment_intent': checkout_session.payment_intent or ''}
        )

        order.send_email_to_user_notifying_of_order(
            payment_url=checkout_session.url,
        )

    except stripe.error.StripeError as e:
        print(f"Stripe error: {e.user_message}")
        return HttpResponse(
            f"<h1>Payment Error: {e.user_message} <a href='/'>Home</a></h1>",
            status=500
        )
    except Exception as e:
        print(f"Unexpected error during Stripe checkout: {e}")
        return HttpResponse(
            f"<h1>Unexpected error: {e} <a href='/'>Home</a></h1>",
            status=500
        )

    print(f"[STRIPE] Checkout URL: {checkout_session.url}")
    return redirect(checkout_session.url)


def success(request):
    return render(request, 'payment/payment-successful.html')


def failure(request):
    return render(request, 'payment/payment-failure.html')


@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')

    if not sig_header:
        return HttpResponse(status=400)

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.ENDPOINT_SECRET
        )
    except ValueError as e:
        print('Error parsing payload: {}'.format(str(e)))
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        print('Error verifying webhook signature: {}'.format(str(e)))
        return HttpResponse(status=400)

    if event.type == 'payment_intent.succeeded':
        payment_intent = event.data.object
        stripe_payment_succeeded = StripeSuccessfulPaymentIntent.objects.create(
            payment_intent=payment_intent.id,
        )
        stripe_payment_succeeded.mark_as_paid_if_possible()
        print('PaymentIntent was successful!')

    elif event.type == 'checkout.session.completed':
        session_object = event.data.object

        stripe_session_checkout, created = StripeCheckoutSession.objects.get_or_create(
            order_id=session_object['metadata']['order_id'],
            defaults={'payment_intent': session_object['payment_intent']}
        )

        # Fill in payment_intent if it was blank when first saved
        if not stripe_session_checkout.payment_intent:
            stripe_session_checkout.payment_intent = session_object['payment_intent']
            stripe_session_checkout.save()

        stripe_session_checkout.mark_as_paid_if_possible()
        print(stripe_session_checkout)
        print("Checkout session completed!")

    else:
        print('Unhandled event type {}'.format(event.type))

    return HttpResponse(status=200)