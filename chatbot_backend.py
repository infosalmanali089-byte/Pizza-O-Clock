import re
import random


# ── RESPONSE BANK ──────────────────────────────────────────────────────────────

RESPONSES = {

    "greeting": [
        "Assalamu Alaikum! 👋 Welcome to Pizza'O Clock support. How can I help you today?",
        "Hello! I'm here to help with anything about Pizza'O Clock — orders, delivery, payments, and more. What do you need?",
        "Wa Alaikum Assalam! Great to have you here. Ask me anything about your orders, restaurants, or delivery!",
    ],

    "farewell": [
        "Thank you for reaching out to Pizza'O Clock! Have a great day and enjoy your meal! 🍕",
        "Goodbye! Feel free to come back anytime you need help. We're always here!",
        "Allah Hafiz! Hope we could help. Come back anytime — we're available 24/7!",
    ],

    "thanks": [
        "You're welcome! Is there anything else I can help you with?",
        "Happy to help! Let me know if you have any other questions.",
        "Glad I could assist! Feel free to ask if you need anything else.",
    ],

    "order_how": [
        "To place an order:\n1. Go to the home page and enter your location\n2. Browse nearby restaurants\n3. Add items to your cart\n4. Go to checkout, confirm your address and payment method\n5. Place your order!\n\nMake sure your phone number and delivery address are saved in your profile first.",
        "Ordering is easy!\n• Search restaurants near you on the home page\n• Pick your items and add them to cart\n• Review your order, choose Cash on Delivery or Stripe\n• Hit Place Order — done!\n\nTip: Save your address and phone number in your profile before your first order.",
    ],

    "order_status": [
        "You can check your order status under My Orders in the navigation bar. Here's what each status means:\n\n• Pending — Waiting for the restaurant to accept\n• Preparing — The restaurant is making your food\n• Rider Assigned — A rider has been assigned to your order\n• Rider On Way — Your rider has picked up and is heading to you\n• Delivered — Your order has arrived!\n• Cancelled — The order was cancelled",
        "Go to My Orders to see your current status. Here's a quick guide:\n\n🕐 Pending → Restaurant hasn't confirmed yet\n🍳 Preparing → Food is being made\n🚴 Rider On Way → Rider is coming to you\n✅ Delivered → Enjoy your meal!\n❌ Cancelled → Order didn't go through",
    ],

    "order_cancel": [
        "You can cancel an order only while its status is Preparing. Go to My Orders, find the order, and tap the Cancel button.\n\nOnce the rider is on the way, cancellation is no longer possible.",
        "To cancel your order:\n• Go to My Orders\n• Find the order you want to cancel\n• Tap Cancel (only available while status is Preparing)\n\nIf the rider is already on the way, you'll need to contact support via Feedback.",
    ],

    "order_track": [
        "Head to My Orders in the top navigation to track your order in real time. You'll see the current status — Preparing, Rider On Way, or Delivered.",
        "Track your order anytime from My Orders. The status updates automatically so you always know where your food is!",
    ],

    "order_pending": [
        "Your order is Pending when the restaurant hasn't accepted it yet. Restaurants typically respond within a few minutes. If it stays Pending for more than 5 minutes, it may be automatically cancelled and you'll be notified.",
        "The Pending status means we're waiting for the restaurant to confirm your order. Most restaurants respond quickly. If there's no response within 5 minutes, the order is automatically cancelled.",
    ],

    "order_modify": [
        "Unfortunately, orders cannot be modified once placed. If you need changes, you would need to cancel the current order (while it's still in Preparing status) and place a new one.",
        "We're unable to modify an order after it's placed. Your options are:\n• Cancel the order from My Orders (only while Preparing)\n• Place a new order with the correct items\n\nSorry for the inconvenience!",
    ],

    "delivery_time": [
        "Delivery time depends on the restaurant's preparation time and your distance from them. Most orders arrive within 30–60 minutes. You can track your order status live under My Orders.",
        "Typical delivery takes 30–60 minutes, but it can vary based on:\n• How busy the restaurant is\n• Distance from restaurant to your location\n• Traffic conditions\n\nTrack your live order status under My Orders!",
    ],

    "delivery_area": [
        "Pizza'O Clock operates in Lahore, Karachi, Islamabad, Faisalabad, and many more cities across Pakistan. Enter your location on the home page to see restaurants available near you.",
        "We cover major cities across Pakistan including Lahore, Karachi, Islamabad, and Faisalabad. Just enter your address on the home page and we'll show you what's available near you!",
    ],

    "delivery_charges": [
        "Delivery charges vary by restaurant and your distance from them. You'll see the exact amount at checkout before you confirm your order — no surprises!",
        "Each restaurant sets its own delivery fee based on distance. The exact charge is shown at checkout before you place the order, so you always know what you're paying.",
    ],

    "payment_methods": [
        "We support two payment methods:\n\n• Cash on Delivery — Pay the rider when your order arrives\n• Stripe — Pay online securely with your credit or debit card\n\nYou can select your preferred method at checkout.",
        "Pizza'O Clock accepts:\n\n💵 Cash on Delivery — Pay when your order arrives\n💳 Stripe — Secure online card payment\n\nChoose your method at the checkout page before placing your order.",
    ],

    "payment_failed": [
        "If your payment failed, please check that your card details are correct and try again. If the issue continues, try switching to Cash on Delivery as an alternative, or contact your bank.",
        "Payment failures can happen due to:\n• Incorrect card details\n• Insufficient balance\n• Bank blocking the transaction\n\nTry again or switch to Cash on Delivery. If problems persist, contact your bank or reach us via Feedback.",
    ],

    "payment_status": [
        "Payment status can be:\n\n• Pending — Payment not yet confirmed\n• Accepted — Payment was successful\n• Rejected — Payment failed\n\nYou can see this under My Orders next to each order.",
        "Check your payment status under My Orders. Pending means it's being processed, Accepted means it went through, and Rejected means something went wrong — try again or use Cash on Delivery.",
    ],

    "rider_chat": [
        "Once your order status changes to Rider On Way, a Chat button will appear in My Orders. Tap it to send messages directly to your rider.",
        "You can message your rider directly! Go to My Orders → find your active order → tap Chat. The chat becomes available once your rider is assigned and on the way.",
    ],

    "rider_location": [
        "You can ask your rider directly via the chat in My Orders once the status is Rider On Way. The chat button appears on your active order.",
        "Once the rider is heading your way, use the Chat option in My Orders to message them and ask for their location or ETA.",
    ],

    "rider_otp": [
        "When your rider arrives, they will ask for a delivery OTP to confirm the handover. Share the OTP shown in your order details to complete the delivery.",
        "Your delivery OTP is shown in My Orders on the order detail page. Give this code to your rider when they arrive — it confirms the handover and marks your order as Delivered.",
    ],

    "rider_register": [
        "To join as a rider, click the Rider Login option and then Register. After signing up, update your profile with your location and set yourself as available to start receiving delivery assignments. Flexible hours and great pay!",
        "Interested in riding with us? Here's how:\n1. Click Rider Login in the navigation\n2. Select Register and fill in your details\n3. Set your location and mark yourself available\n4. Start receiving orders!\n\nEarn money on your own schedule!",
    ],

    "rider_availability": [
        "Riders can toggle their availability from their profile dashboard. When you're available, you'll be assigned nearby delivery orders automatically.",
        "To go online as a rider, log in to your rider account and toggle your availability to ON. Orders will start coming in based on your location. Toggle it OFF when you're done for the day.",
    ],

    "restaurant_register": [
        "Restaurant owners can register by clicking Restaurant Login in the top navbar, then selecting Register. After registering, set up your profile, add your menu items, and publish your restaurant to start receiving orders.",
        "To list your restaurant on Pizza'O Clock:\n1. Click Restaurant Login in the navbar\n2. Select Register\n3. Fill in your restaurant details\n4. Add your menu items and prices\n5. Publish your restaurant — customers can now find you!\n\nYou're in full control of your menu, hours, and orders.",
    ],

    "restaurant_menu": [
        "As a restaurant owner, go to your dashboard and select Menus to add or manage your menu sections and items. You can add item names, descriptions, prices, and photos for each dish.",
        "Managing your menu is simple:\n• Go to your restaurant dashboard\n• Click Menus\n• Add menu sections (e.g. Deals, Burgers, Drinks)\n• Add items with name, description, price, and photo\n\nYou can also mark items as unavailable without deleting them.",
    ],

    "restaurant_orders": [
        "Restaurant owners can view and manage all incoming orders from the Track Orders section in the restaurant dashboard. You can accept or reject orders from there.",
        "To manage orders:\n• Open your restaurant dashboard\n• Go to Track Orders\n• Accept or reject incoming orders\n• Orders must be accepted before a rider is assigned\n\nTip: Keep an eye on your dashboard during busy hours!",
    ],

    "restaurant_publish": [
        "To publish your restaurant and make it visible to customers, make sure your profile is complete — name, phone numbers, cover image, and opening hours must all be filled in. Then toggle the Publish switch in your restaurant settings.",
        "Your restaurant won't appear in search results until it's published. Go to your dashboard → Edit Restaurant → toggle Publish Restaurant to ON. Make sure your name, phones, image, and hours are all set first.",
    ],

    "profile_update": [
        "You can update your name, email, phone number, profile picture, and delivery address from your Profile page. Make sure your phone number and address are saved before placing your first order.",
        "To update your profile:\n• Click your profile icon in the navigation\n• Edit your name, email, phone, or address\n• Save your changes\n\nKeep your phone number and delivery address up to date for smooth deliveries!",
    ],

    "password_reset": [
        "To reset your password, click Forgot Password on the login page. We'll send a reset link to your registered email address. Check your spam folder if you don't see it within a few minutes.",
        "Forgot your password? No worries!\n1. Go to the login page\n2. Click Forgot Password\n3. Enter your email address\n4. Check your inbox (and spam folder) for the reset link\n5. Set a new password\n\nThe link expires after a short time, so use it quickly.",
    ],

    "location": [
        "On the home page, enter your address in the search box or click Use My Location to automatically detect where you are. This shows you only the restaurants that deliver to your area.",
        "To set your location:\n• Type your city or street address in the search bar on the home page\n• Or click Use My Location to auto-detect\n\nYou can also update your saved delivery address in your profile settings.",
    ],

    "no_restaurants": [
        "If no restaurants appear, it could mean we don't have coverage in your exact area yet, or your location wasn't detected correctly. Try typing your city name manually in the search box.",
        "No restaurants showing? Try these:\n• Type your city name manually instead of using GPS\n• Double-check your location is set correctly\n• We're expanding constantly — check back soon!\n\nIf you keep having issues, contact us via Feedback.",
    ],

    "rating_review": [
        "After your order is delivered, a Write a Review button will appear in My Orders. You can rate the food, the rider, and the restaurant. Your feedback helps us improve the platform!",
        "To leave a review:\n• Go to My Orders\n• Find your delivered order\n• Tap Write a Review\n• Rate the food, rider, and restaurant\n\nYour honest feedback helps other customers and improves our service!",
    ],

    "contact": [
        "For further help, use the Feedback section in the app to send us a message. You can also use this Live Chat anytime — we're here to help!",
        "Need more help? You can:\n• Use this Live Chat (we reply instantly!)\n• Submit feedback through the Feedback section\n\nWe're here to make sure your experience is great.",
    ],

    "hours": [
        "Pizza'O Clock is available whenever restaurants in your area are open. Each restaurant sets its own hours — you'll see if a restaurant is currently open or closed when you browse.",
        "Our platform is available 24/7, but restaurant availability depends on their own hours. Check the restaurant listing to see if they're currently open. Closed restaurants won't accept new orders.",
    ],

    "app": [
        "Pizza'O Clock is a web-based platform — you can use it directly from your browser on any device, including your phone. No app download needed!",
        "Good news — no app download required! Pizza'O Clock works right in your mobile or desktop browser. Just open the website and you're good to go.",
    ],

    "promo_discount": [
        "Promotions and discounts are offered directly by restaurants. Keep an eye on restaurant listings for any special deals when browsing.",
        "We don't currently have a platform-wide promo system, but individual restaurants may offer their own deals. Browse restaurant listings to spot any special offers!",
    ],

    "minimum_order": [
        "Minimum order amounts (if any) are set by individual restaurants and will be shown at checkout before you confirm.",
        "Some restaurants set a minimum order amount. If yours does, you'll see it when reviewing your cart. Add more items to meet the minimum before placing your order.",
    ],

    "refund": [
        "For refund requests, please use the Feedback section and describe your issue in detail. Our team will review your case as soon as possible and get back to you.",
        "To request a refund:\n• Go to the Feedback section\n• Describe the issue clearly and include your order ID\n• Our team will review and respond as soon as possible\n\nRefunds are handled case by case.",
    ],

    "food_quality": [
        "If you experienced a food quality issue, please leave a review after your order is delivered, or contact us via the Feedback section with your order ID. We take quality seriously!",
        "We're sorry to hear about a food quality issue! Please:\n1. Leave a review on the order\n2. Submit a report via Feedback with your order ID\n\nWe take this seriously and will follow up with the restaurant.",
    ],

    "missing_item": [
        "If an item is missing from your order, please contact us through the Feedback section with your order ID and the missing item details. We'll look into it right away.",
        "Missing something from your order? Here's what to do:\n• Go to Feedback\n• Mention your order ID and the missing item\n• We'll investigate and get back to you quickly\n\nSorry for the trouble!",
    ],

    "wrong_order": [
        "Sorry to hear you received the wrong order! Please reach out via the Feedback section with your order ID and we'll work to resolve it as quickly as possible.",
        "That shouldn't happen — we apologize! Please:\n1. Take a photo if possible\n2. Go to Feedback\n3. Include your order ID and describe what went wrong\n\nWe'll resolve this as fast as we can.",
    ],

    "late_delivery": [
        "We're sorry your order is taking longer than expected. Delays can happen due to high demand or traffic. You can track your order status live under My Orders. If it's been unusually long, please contact us via Feedback.",
        "Sorry for the wait! A few things that can cause delays:\n• High order volume at the restaurant\n• Heavy traffic\n• Bad weather\n\nCheck your live status under My Orders. If it's been over 90 minutes, please let us know via Feedback.",
    ],

    "item_customization": [
        "Some menu items have variants (like size or flavour) and add-ons (like extra toppings). You'll see these options when you add an item to your cart — just select your preferences before adding.",
        "When adding an item to your cart, look for variant and add-on options below the item. Select your preferred size, flavour, or extras before tapping Add to Cart.",
    ],

    "cart": [
        "Your cart stores items from one restaurant at a time. You can view it by tapping the cart icon. From there you can adjust quantities, remove items, or proceed to checkout.",
        "To manage your cart:\n• Tap the cart icon to view your items\n• Use + and - to change quantities\n• Remove items you don't want\n• Tap Checkout when you're ready\n\nNote: You can only order from one restaurant at a time.",
    ],

    "account_delete": [
        "To delete your account, please contact us through the Feedback section with your request. Our team will process it and confirm once done.",
    ],

    "multiple_orders": [
        "Currently, you can have one active order at a time per restaurant. You're free to place orders from different restaurants, but each will be a separate order.",
    ],

    "default": [
        "I'm not sure I understood that. Could you try rephrasing? You can ask me about placing orders, delivery, payments, your account, or anything else about Pizza'O Clock.",
        "I didn't quite catch that. Feel free to ask about orders, tracking, payments, restaurants, or your account!",
        "Hmm, I'm not sure about that one. Try asking about order status, delivery areas, payment methods, or how to use Pizza'O Clock.",
        "I want to help but I'm not sure what you mean. Could you be more specific? For example: 'How do I track my order?' or 'What payment methods do you accept?'",
    ],
}


# ── INTENT RULES ───────────────────────────────────────────────────────────────

INTENT_RULES = [
    # Farewells first
    ("farewell",            [r"\b(bye|goodbye|see you|later|take care|khuda hafiz|allah hafiz|khuda|hafiz|alvida|tata|good night)\b"]),
    ("thanks",              [r"\b(thank|thanks|thankyou|thank you|shukriya|shukar|meherbani|nawazish)\b"]),
    ("greeting",            [r"\b(hello|hi|hey|assalam|salam|aoa|howdy|good morning|good evening|good afternoon|greetings|helo|hii|kya hal|kaise ho|ap kaise|hola|sup|whats up)\b"]),

    # Problem reports
    ("missing_item",        [r"\b(missing|not received|didn.t receive|item.*missing|missing.*item|item nahi aaya|cheez nahi|missing item|mila nahi|nahi mila)\b"]),
    ("wrong_order",         [r"\b(wrong order|wrong item|incorrect order|not what i ordered|galat order|galat cheez|ulta order)\b"]),
    ("late_delivery",       [r"\b(late|taking long|too long|delay|slow delivery|not arrived yet|der ho rahi|bahut der|abhi tak nahi|late ho gaya|kab ayega|itna time|itni der)\b"]),
    ("food_quality",        [r"\b(bad food|food quality|stale|cold food|quality issue|not fresh|kharab khana|ganda khana|taste nahi|bekar khana)\b"]),
    ("payment_failed",      [r"\b(payment fail|payment not work|card fail|stripe fail|transaction fail|payment error|payment nahi hua|card kaam nahi|payment stuck)\b"]),

    # Orders
    ("order_cancel",        [r"\b(cancel|cancellation|cancel karo|order cancel|band karo|wapas karo|order hatao)\b"]),
    ("order_modify",        [r"\b(change.*order|modify.*order|edit.*order|update.*order|order.*change|order badlo)\b"]),
    ("order_pending",       [r"\b(pending|restaurant.*not.*accept|not.*accepted|waiting.*restaurant|restaurant ne accept nahi|order pending)\b"]),
    ("order_status",        [r"\b(order status|status of order|what.*status|preparing|rider on way|mera order|order ka status|order kahan|kahan hai mera|order check)\b"]),
    ("order_track",         [r"\b(track|where is my order|track.*order|order.*track|order dhundo|order track karo|mera order kahan|locate.*order)\b"]),
    ("order_how",           [r"\b(how.*order|place.*order|how do i order|ordering|start.*order|order kaise|order karna|order lagana)\b"]),

    # Delivery
    ("delivery_time",       [r"\b(how long|delivery time|eta|when will|arrive|how much time|time.*delivery|kitna time|kab ayega|kb aaye ga|jaldi aaye|estimated time|kitni der)\b"]),
    ("delivery_area",       [r"\b(city|cities|area|cover|lahore|karachi|islamabad|faisalabad|where.*available|kon se city|kaun si jagah|available kahan)\b"]),
    ("delivery_charges",    [r"\b(delivery charge|delivery fee|delivery cost|how much.*deliver|delivery kitna|charge kitna|fee kitna|delivery ka paisa)\b"]),

    # Payment
    ("payment_status",      [r"\b(payment status|paid|pending.*payment|payment.*pending|rejected|payment.*accepted|payment hua|payment confirm)\b"]),
    ("payment_methods",     [r"\b(payment|pay|stripe|cash|cod|card|credit|debit|how.*pay|payment.*method|payment kaise|kaise pay|cod kya|paisa kaise|online pay)\b"]),

    # Rider
    ("rider_location",      [r"\b(rider.*kahan|where.*rider|rider.*location|rider.*near|rider.*close|rider ka location|rider aa raha)\b"]),
    ("rider_chat",          [r"\b(chat.*rider|message.*rider|talk.*rider|rider.*chat|contact.*rider|rider se baat|rider ko message)\b"]),
    ("rider_otp",           [r"\b(otp|verification code|delivery.*code|confirm.*deliver|rider.*code|code rider ko|delivery otp)\b"]),
    ("rider_availability",  [r"\b(rider.*available|go online|rider online|set.*available|toggle.*available|available karna|online karna)\b"]),
    ("rider_register",      [r"\b(become.*rider|join.*rider|register.*rider|rider.*register|sign up.*rider|rider.*job|rider banana|rider banna)\b"]),

    # Restaurant
    ("restaurant_publish",  [r"\b(publish.*restaurant|restaurant.*publish|visible|show.*restaurant|restaurant.*live|live karna|publish karna)\b"]),
    ("restaurant_register", [r"\b(register.*restaurant|add.*restaurant|list.*restaurant|restaurant.*register|become.*restaurant|restaurant.*owner|restaurant banana)\b"]),
    ("restaurant_menu",     [r"\b(add.*menu|menu.*item|manage.*menu|restaurant.*menu|edit.*menu|menu add|menu update)\b"]),
    ("restaurant_orders",   [r"\b(restaurant.*order|incoming.*order|manage.*order|restaurant.*dashboard|order aaya|new order)\b"]),

    # Account
    ("account_delete",      [r"\b(delete.*account|remove.*account|close.*account|account delete|account band karo)\b"]),
    ("password_reset",      [r"\b(forgot.*password|reset.*password|password.*reset|change.*password|password.*forgot|password bhool|password nahi pata)\b"]),
    ("profile_update",      [r"\b(update.*profile|edit.*profile|change.*name|change.*email|change.*phone|my profile|profile.*update|profile change)\b"]),

    # Cart & ordering details
    ("cart",                [r"\b(cart|basket|bag|add.*cart|remove.*cart|cart mein|cart se hatao)\b"]),
    ("item_customization",  [r"\b(variant|addon|add.on|customize|customise|size|flavou?r|topping|extra|special.*instruction)\b"]),
    ("multiple_orders",     [r"\b(multiple.*order|two.*order|double.*order|ek se zyada|more than one order)\b"]),

    # Location & discovery
    ("no_restaurants",      [r"\b(no restaurant|no result|nothing.*near|can.t find.*restaurant|no.*available|restaurant nahi|koi restaurant nahi)\b"]),
    ("location",            [r"\b(location|address|use.*location|detect.*location|find.*restaurant|my location|meri location|address set)\b"]),

    # Misc
    ("rating_review",       [r"\b(rate|review|rating|write.*review|feedback.*order|leave.*review|review karna|rating dena)\b"]),
    ("refund",              [r"\b(refund|money back|return.*money|compensation|get.*money|paisa wapas|refund chahiye)\b"]),
    ("contact",             [r"\b(contact|support|help|reach|speak.*someone|customer.*care|helpline|madad)\b"]),
    ("hours",               [r"\b(hour|timing|open|close|when.*open|working hour|restaurant.*time|kab khulta|band kab)\b"]),
    ("app",                 [r"\b(app|download|mobile app|play store|app store|install|application)\b"]),
    ("promo_discount",      [r"\b(promo|discount|coupon|offer|deal|voucher|special offer|discount karo|sasta|offer koi)\b"]),
    ("minimum_order",       [r"\b(minimum order|min order|minimum amount|least.*order|kam se kam|minimum kitna)\b"]),
]


# ── RESPONSE ROTATION ──────────────────────────────────────────────────────────
_response_index: dict[str, int] = {}


def _get_response(intent: str) -> str:
    options = RESPONSES.get(intent, RESPONSES["default"])
    idx = _response_index.get(intent, 0)
    response = options[idx % len(options)]
    _response_index[intent] = idx + 1
    return response


# ── MAIN ENTRY POINT ───────────────────────────────────────────────────────────

def generate_response(user_input: str) -> str:
    if not user_input or not user_input.strip():
        return _get_response("default")

    text = user_input.lower().strip()
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text)

    for intent, patterns in INTENT_RULES:
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return _get_response(intent)

    return _get_response("default")