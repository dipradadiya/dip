import json
import random
import string

import razorpay
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse
from django.shortcuts import redirect
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import ListView, DetailView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView
from django.template.loader import render_to_string

from .forms import CheckoutForm, CouponForm
from .forms import RefundForm  # if you have a custom form
from .models import Item, ProductReview
from .models import OrderItem, Order, Address, Payment, Coupon, Refund


def create_ref_code():
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=20))


def products(request):
    context = {
        'items': Item.objects.all()
    }
    return render(request, "products.html", context)


def kurti_view(request):
    kurti_products = Item.objects.filter(category__iexact="kurti")  # Filter only Kurti category
    return render(request, "kurti.html", {"object_list": kurti_products})  # Pass products to template


def western_view(request):
    western_products = Item.objects.filter(category__iexact="Western")  # Filter only Kurti category
    return render(request, "western.html", {"object_list": western_products})  # Pass products to template


def Beauty_view(request):
    Beauty_products = Item.objects.filter(category__iexact="Beauty")  # Filter only Kurti category
    return render(request, "Beauty.html", {"object_list": Beauty_products})  # Pass products to template


def is_valid_form(values):
    valid = True
    for field in values:
        if field == '':
            valid = False
    return valid


class CheckoutView(View):
    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("login")

        order = Order.objects.filter(user=request.user, ordered=False).first()
        if not order:
            messages.warning(request, "You have no items in your cart.")
            return redirect("core:home")

        form = CheckoutForm()
        context = {
            'form': form,
            'order': order,
            'razorpay_key_id': settings.RAZORPAY_KEY_ID
        }
        return render(request, 'checkout.html', context)

    def post(self, request, *args, **kwargs):
        form = CheckoutForm(request.POST)
        if form.is_valid():
            payment_option = form.cleaned_data.get('payment_option')

            address = Address.objects.create(
                user=request.user,
                street_address=form.cleaned_data.get('shipping_address'),
                apartment_address=form.cleaned_data.get('shipping_address2'),
                country=form.cleaned_data.get('shipping_country'),
                zip=form.cleaned_data.get('shipping_zip'),
                address_type='S',
                default=True
            )

            try:
                order = Order.objects.get(user=request.user, ordered=False)
            except Order.DoesNotExist:
                messages.error(request, "No active order found.")
                return redirect("core:checkout")

            order.shipping_address = address
            order.billing_address = address
            order.save()

            if payment_option == 'cod':
                payment = Payment.objects.create(
                    user=request.user,
                    amount=order.get_total(),
                    payment_method='cod'
                )
                order.payment = payment
                order.ordered = True
                order.ordered_date = timezone.now()
                order.save()
                order.items.update(ordered=True)
                return redirect('core:order_success', order_id=order.id)

            elif payment_option == 'razorpay':
                return JsonResponse({'msg': 'Razorpay handled on frontend'})

        messages.warning(request, "Invalid form submission.")
        return redirect("core:checkout")


@method_decorator(csrf_exempt, name='dispatch')
class RazorpaySuccessView(View):
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            payment_id = data.get("razorpay_payment_id")
            razorpay_order_id = data.get("order_id")

            order = Order.objects.get(razorpay_order_id=razorpay_order_id, ordered=False)

            payment = Payment.objects.create(
                user=order.user,
                amount=order.get_total(),
                payment_method='razorpay',
                razorpay_payment_id=payment_id
            )

            order.payment = payment
            order.ordered = True
            order.ordered_date = timezone.now()
            order.save()
            order.items.update(ordered=True)

            return JsonResponse({
                "status": "success",
                "redirect_url": f"/order-success/{order.id}/"
            })

        except Exception as e:
            # ✅ SEND BACK PLAIN TEXT ERROR
            return HttpResponse(f"Internal Server Error: {e}", status=500)


class OrderSuccessView(View):
    def get(self, request, order_id):
        try:
            order = Order.objects.get(id=order_id, user=request.user)
        except Order.DoesNotExist:
            messages.error(request, "Order not found.")
            return redirect("core:home")

        return render(request, 'order_success.html', {'order': order})


@csrf_exempt
@login_required
def create_razorpay_order(request):
    if request.method == "POST":
        try:
            order = Order.objects.get(user=request.user, ordered=False)
        except Order.DoesNotExist:
            return JsonResponse({'error': 'Order not found'}, status=404)

        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        amount = int(order.get_total() * 100)  # amount in paise

        data = {
            "amount": amount,
            "currency": "INR",
            "payment_capture": 1
        }

        razorpay_order = client.order.create(data=data)

        # ✅ Save Razorpay order ID in the database
        order.razorpay_order_id = razorpay_order['id']
        order.save()

        return JsonResponse({
            'order_id': razorpay_order['id'],  # ✅ This will be used on frontend
            'amount': amount,
            'currency': "INR"
        })

    return JsonResponse({'error': 'Invalid request'}, status=400)


class OrderSuccessView(View):
    def get(self, request, order_id):
        try:
            order = Order.objects.get(id=order_id, user=request.user, ordered=True)
            context = {
                'order': order,
            }
            return render(request, "order_success.html", context)
        except Order.DoesNotExist:
            messages.error(request, "Order not found.")
            return redirect("core:home")


class MyOrdersView(ListView):
    model = Order
    template_name = 'my_orders.html'
    context_object_name = 'orders'

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user, ordered=True).order_by('-ordered_date')


class PaymentView(View):
    def get(self, request):
        # example logic
        return render(request, 'payment.html')


class HomeView(ListView):
    model = Item
    template_name = "home.html"

    def get_queryset(self):
        return Item.objects.all()


class OrderSummaryView(LoginRequiredMixin, View):
    def get(self, *args, **kwargs):
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            context = {
                'object': order
            }
            return render(self.request, 'order_summary.html', context)
        except ObjectDoesNotExist:
            messages.warning(self.request, "You do not have an active order")
            return redirect("/")


class ItemDetailView(DetailView):
    model = Item
    template_name = "product.html"  # Make sure the template name matches
    context_object_name = 'item'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['reviews'] = ProductReview.objects.filter(item=self.object)
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()

        rating = request.POST.get('rating')
        comment = request.POST.get('comment')

        if rating and comment:
            ProductReview.objects.create(
                item=self.object,
                user=request.user,
                rating=int(rating),
                comment=comment
            )

        # Redirect back to the same product page
        return redirect('product-detail', slug=self.object.slug)
        cd


@login_required
def add_to_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)

    if item.stock == 0:
        messages.warning(request, "This item is out of stock.")
        return redirect("core:home")

    order_item, created = OrderItem.objects.get_or_create(
        item=item,
        user=request.user,
        ordered=False
    )

    order_qs = Order.objects.filter(user=request.user, ordered=False)

    if order_qs.exists():
        order = order_qs[0]
        if order.items.filter(item__slug=item.slug).exists():
            if item.stock > order_item.quantity:
                order_item.quantity += 1
                order_item.save()
                messages.info(request, "This item quantity was updated.")
            else:
                messages.warning(request, "Not enough stock available.")
        else:
            order.items.add(order_item)
            messages.info(request, "This item was added to your cart.")
    else:
        ordered_date = timezone.now()
        order = Order.objects.create(user=request.user, ordered_date=ordered_date)
        order.items.add(order_item)
        messages.info(request, "This item was added to your cart.")

    return redirect("core:order-summary")


@login_required
def remove_from_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)
    order_qs = Order.objects.filter(
        user=request.user,
        ordered=False
    )
    if order_qs.exists():
        order = order_qs[0]
        # check if the order item is in the order
        if order.items.filter(item__slug=item.slug).exists():
            order_item = OrderItem.objects.filter(
                item=item,
                user=request.user,
                ordered=False
            )[0]
            order.items.remove(order_item)
            order_item.delete()
            messages.info(request, "This item was removed from your cart.")
            return redirect("core:order-summary")
        else:
            messages.info(request, "This item was not in your cart")
            return redirect("core:product", slug=slug)
    else:
        messages.info(request, "You do not have an active order")
        return redirect("core:product", slug=slug)


@login_required
def remove_single_item_from_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)
    order_qs = Order.objects.filter(
        user=request.user,
        ordered=False
    )
    if order_qs.exists():
        order = order_qs[0]
        # check if the order item is in the order
        if order.items.filter(item__slug=item.slug).exists():
            order_item = OrderItem.objects.filter(
                item=item,
                user=request.user,
                ordered=False
            )[0]
            if order_item.quantity > 1:
                order_item.quantity -= 1
                order_item.save()
            else:
                order.items.remove(order_item)
            messages.info(request, "This item quantity was updated.")
            return redirect("core:order-summary")
        else:
            messages.info(request, "This item was not in your cart")
            return redirect("core:product", slug=slug)
    else:
        messages.info(request, "You do not have an active order")
        return redirect("core:product", slug=slug)


def get_coupon(request, code):
    try:
        coupon = Coupon.objects.get(code=code)
        return coupon
    except ObjectDoesNotExist:
        messages.info(request, "This coupon does not exist")
        return redirect("core:checkout")


class AddCouponView(View):
    def post(self, *args, **kwargs):
        form = CouponForm(self.request.POST or None)
        if form.is_valid():
            try:
                code = form.cleaned_data.get('code')
                order = Order.objects.get(
                    user=self.request.user, ordered=False)
                order.coupon = get_coupon(self.request, code)
                order.save()
                messages.success(self.request, "Successfully added coupon")
                return redirect("core:checkout")
            except ObjectDoesNotExist:
                messages.info(self.request, "You do not have an active order")
                return redirect("core:checkout")


class RequestRefundView(View):
    def get(self, *args, **kwargs):
        form = RefundForm()
        context = {
            'form': form
        }
        return render(self.request, "request_refund.html", context)

    def post(self, *args, **kwargs):
        form = RefundForm(self.request.POST)
        if form.is_valid():
            ref_code = form.cleaned_data.get('ref_code')
            message = form.cleaned_data.get('message')
            email = form.cleaned_data.get('email')
            # edit the order
            try:
                order = Order.objects.get(ref_code=ref_code)
                order.refund_requested = True
                order.save()

                # store the refund
                refund = Refund()
                refund.order = order
                refund.reason = message
                refund.email = email
                refund.save()

                messages.info(self.request, "Your request was received.")
                return redirect("core:request-refund")

            except ObjectDoesNotExist:
                messages.info(self.request, "This order does not exist.")
                return redirect("core:request-refund")


@login_required(login_url='/login/')
def MyOrdersView(request):
    orders = Order.objects.filter(user=request.user, ordered=True).order_by('-ordered_date')
    return render(request, 'orders/my_orders.html', {'orders': orders})


class MyOrdersView(LoginRequiredMixin, ListView):
    model = Order
    template_name = 'my_orders.html'  # This file must exist
    context_object_name = 'orders'
    login_url = '/login/'

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user, ordered=True).order_by('-ordered_date')