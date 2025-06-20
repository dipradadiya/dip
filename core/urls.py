from django.urls import path
from .views import (
    ItemDetailView,
    CheckoutView,
    HomeView,
    kurti_view,
    western_view,
    Beauty_view,
    OrderSummaryView,
    add_to_cart,
    remove_from_cart,
    remove_single_item_from_cart,
    PaymentView,
    AddCouponView,
    RequestRefundView,
    OrderSuccessView,
    MyOrdersView,


)
from django.contrib.auth.views import LoginView
from core.views import create_razorpay_order
from .views import RazorpaySuccessView
from django.contrib.auth import views as auth_views

app_name = 'core'

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    # path('login/', LoginView.as_view(), name='login'),
    path('login/', auth_views.LoginView.as_view(template_name='account/login.html'), name='login'),
    path('kurti/', kurti_view, name='kurti'),
    path('western/', western_view, name='western'),
    path('Beauty/', Beauty_view, name='Beauty'),
    path('order-summary/', OrderSummaryView.as_view(), name='order-summary'),

    path('product/<slug:slug>/', ItemDetailView.as_view(), name='product-detail'),
    # path('product/<int:id>/', ItemDetailView.as_view(), name='product-detail'),


    path('add-to-cart/<slug>/', add_to_cart, name='add-to-cart'),
    path('add-coupon/', AddCouponView.as_view(), name='add-coupon'),
    path('remove-from-cart/<slug>/', remove_from_cart, name='remove-from-cart'),
    path('remove-item-from-cart/<slug>/', remove_single_item_from_cart,
         name='remove-single-item-from-cart'),
    path('payment/<payment_option>/', PaymentView.as_view(), name='payment'),
    path('request-refund/', RequestRefundView.as_view(), name='request-refund'),
    path('checkout/', CheckoutView.as_view(), name='checkout'),
    path('create-razorpay-order/', create_razorpay_order, name='create_razorpay_order'),
    path('razorpay-success/', RazorpaySuccessView.as_view(), name='razorpay_success'),
    path('order-success/<int:order_id>/', OrderSuccessView.as_view(), name='order_success'),
    path('my-orders/', MyOrdersView.as_view(), name='my-orders'),
]
