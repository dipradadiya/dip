from django.contrib import admin
from django.utils.html import format_html
from .models import Item, OrderItem, Order, Payment, Coupon, Refund, Address, ProductReview
from django.urls import reverse

# Inline Order Items inside the OrderAdmin
class OrderItemInline(admin.TabularInline):
    model = Order.items.through  # Use ManyToMany "through" model
    extra = 0
    verbose_name = "Ordered Item"
    verbose_name_plural = "Ordered Items"
    readonly_fields = ('orderitem_display',)

    def orderitem_display(self, obj):
        return f"{obj.orderitem.quantity} x {obj.orderitem.item.title} (₹{obj.orderitem.item.price})"

    orderitem_display.short_description = "Item Details"


def make_refund_accepted(modeladmin, request, queryset):
    queryset.update(refund_requested=False, refund_granted=True)

make_refund_accepted.short_description = 'Mark selected orders as refund granted'


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'ordered', 'ordered_date', 'total_amount', 'payment_method', 'delivery_status', 'edit_link', 'delete_link']
    list_filter = ['ordered', 'being_delivered', 'received', 'refund_requested', 'refund_granted']
    search_fields = ['user__username', 'razorpay_order_id']
    inlines = [OrderItemInline]
    actions = [make_refund_accepted]
    readonly_fields = ['ordered_date', 'total_amount', 'payment_method', 'shipping_address_display']

    def total_amount(self, obj):
        return f"₹{obj.get_total()}"

    total_amount.short_description = "Total Amount"

    def payment_method(self, obj):
        return obj.payment.payment_method.title() if obj.payment else "-"

    payment_method.short_description = "Payment"

    def delivery_status(self, obj):
        if obj.received:
            return "Received"
        elif obj.being_delivered:
            return "Out for Delivery"
        else:
            return "Pending"

    delivery_status.short_description = "Delivery Status"

    def shipping_address_display(self, obj):
        if obj.shipping_address:
            return format_html(f"""
                <b>{obj.shipping_address.street_address}</b><br>
                {obj.shipping_address.apartment_address}<br>
                {obj.shipping_address.country}, {obj.shipping_address.zip}
            """)
        return "No Address"

    shipping_address_display.short_description = "Shipping Address"

    def edit_link(self, obj):
        return format_html('<a href="{}">Edit</a>',
                           reverse('admin:%s_%s_change' % (obj._meta.app_label, obj._meta.model_name), args=[obj.pk]))

    def delete_link(self, obj):
        return format_html('<a href="{}">Delete</a>',
                           reverse('admin:%s_%s_delete' % (obj._meta.app_label, obj._meta.model_name), args=[obj.pk]))

    edit_link.short_description = 'Edit Link'
    delete_link.short_description = 'Delete Link'

    fieldsets = (
        ("User & Status", {
            'fields': ('user', 'ordered', 'ordered_date', 'being_delivered', 'received')
        }),
        ("Address & Payment", {
            'fields': ('shipping_address_display', 'payment', 'payment_method', 'coupon')
        }),
        ("Extra Info", {
            'fields': ('refund_requested', 'refund_granted', 'razorpay_order_id')
        }),
    )


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['user', 'item', 'quantity', 'ordered', 'edit_link', 'delete_link']
    list_filter = ['ordered']
    search_fields = ['user__username', 'item__title']
    actions = ['mark_out_of_stock']

    def mark_out_of_stock(self, request, queryset):
        queryset.update(quantity=0)  # Custom action to mark items as out of stock

    mark_out_of_stock.short_description = "Mark selected items as out of stock"

    def edit_link(self, obj):
        return format_html('<a href="{}">Edit</a>',
                           reverse('admin:%s_%s_change' % (obj._meta.app_label, obj._meta.model_name), args=[obj.pk]))

    def delete_link(self, obj):
        return format_html('<a href="{}">Delete</a>',
                           reverse('admin:%s_%s_delete' % (obj._meta.app_label, obj._meta.model_name), args=[obj.pk]))

    edit_link.short_description = 'Edit Link'
    delete_link.short_description = 'Delete Link'


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ['title', 'price', 'stock', 'category', 'image_preview', 'edit_link', 'delete_link']
    search_fields = ['title', 'category']
    prepopulated_fields = {"slug": ("title",)}

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="40" height="40" />', obj.image.url)
        return "No Image"

    def edit_link(self, obj):
        return format_html('<a href="{}">Edit</a>',
                           reverse('admin:%s_%s_change' % (obj._meta.app_label, obj._meta.model_name), args=[obj.pk]))

    def delete_link(self, obj):
        return format_html('<a href="{}">Delete</a>',
                           reverse('admin:%s_%s_delete' % (obj._meta.app_label, obj._meta.model_name), args=[obj.pk]))

    edit_link.short_description = 'Edit Link'
    delete_link.short_description = 'Delete Link'


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'user_name', 'amount', 'payment_method', 'timestamp', 'edit_link', 'delete_link')
    search_fields = ('user__username', 'payment_method')
    list_filter = ('payment_method', 'timestamp')

    def user_name(self, obj):
        return obj.user.username if obj.user else "Unknown"

    user_name.short_description = 'User'

    def edit_link(self, obj):
        return format_html('<a href="{}">Edit</a>',
                           reverse('admin:%s_%s_change' % (obj._meta.app_label, obj._meta.model_name), args=[obj.pk]))

    def delete_link(self, obj):
        return format_html('<a href="{}">Delete</a>',
                           reverse('admin:%s_%s_delete' % (obj._meta.app_label, obj._meta.model_name), args=[obj.pk]))

    edit_link.short_description = 'Edit Link'
    delete_link.short_description = 'Delete Link'


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ['user', 'street_address', 'apartment_address', 'country', 'zip', 'address_type', 'default', 'edit_link', 'delete_link']
    list_filter = ['default', 'address_type', 'country']

    def edit_link(self, obj):
        return format_html('<a href="{}">Edit</a>',
                           reverse('admin:%s_%s_change' % (obj._meta.app_label, obj._meta.model_name), args=[obj.pk]))

    def delete_link(self, obj):
        return format_html('<a href="{}">Delete</a>',
                           reverse('admin:%s_%s_delete' % (obj._meta.app_label, obj._meta.model_name), args=[obj.pk]))

    edit_link.short_description = 'Edit Link'
    delete_link.short_description = 'Delete Link'


@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    list_display = ['user', 'get_item_title', 'get_item_image', 'rating', 'created_at', 'edit_link', 'delete_link']
    search_fields = ['user__username', 'item__title']
    list_filter = ['rating', 'created_at']
    actions = ['approve_reviews']

    # Method to show Item title
    def get_item_title(self, obj):
        return obj.item.title if obj.item else "No Item"

    get_item_title.short_description = 'Item'

    # Method to display the image of the item being reviewed
    def get_item_image(self, obj):
        if obj.item.image:
            return format_html('<img src="{}" width="50" height="50" />', obj.item.image.url)
        return "No Image"

    get_item_image.short_description = 'Item Image'

    # Add edit link to each review for quick access
    def edit_link(self, obj):
        return format_html('<a href="{}">Edit</a>',
                           reverse('admin:%s_%s_change' % (obj._meta.app_label, obj._meta.model_name), args=[obj.pk]))

    # Add delete link to each review for quick deletion
    def delete_link(self, obj):
        return format_html('<a href="{}">Delete</a>',
                           reverse('admin:%s_%s_delete' % (obj._meta.app_label, obj._meta.model_name), args=[obj.pk]))

    edit_link.short_description = 'Edit Link'
    delete_link.short_description = 'Delete Link'

    # Action to approve selected reviews
    def approve_reviews(self, request, queryset):
        queryset.update(approved=True)

    approve_reviews.short_description = "Approve selected reviews"


# Register other models
admin.site.register(Coupon)
admin.site.register(Refund)
