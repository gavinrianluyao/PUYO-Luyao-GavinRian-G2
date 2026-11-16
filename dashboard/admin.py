from django.contrib import admin
from .models import (
    Bill,
    BillItem,
    BoardingHouse,
    Notification,
    Payment,
    Room,
    Tenancy,
)


@admin.register(BoardingHouse)
class BoardingHouseAdmin(admin.ModelAdmin):
    list_display = ["name", "owner", "address", "created_at"]
    search_fields = ["name", "address", "owner__full_name"]


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = [
        "room_number",
        "house",
        "capacity",
        "monthly_rate",
        "status",
    ]
    list_filter = ["status", "house"]
    search_fields = ["room_number", "house__name"]


@admin.register(Tenancy)
class TenancyAdmin(admin.ModelAdmin):
    list_display = [
        "student",
        "room",
        "start_date",
        "end_date",
        "monthly_rent",
        "status",
    ]
    list_filter = ["status", "room__house"]
    search_fields = [
        "student__full_name",
        "room__room_number",
        "room__house__name",
    ]


class BillItemInline(admin.TabularInline):
    model = BillItem
    extra = 1


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    readonly_fields = ["recorded_at"]


@admin.register(Bill)
class BillAdmin(admin.ModelAdmin):
    list_display = [
        "bill_id",
        "tenancy",
        "created_by",
        "period_start",
        "period_end",
        "due_date",
        "total_amount",
        "status",
    ]
    list_filter = ["status", "created_by"]
    search_fields = ["tenancy__student__full_name", "bill_id"]
    inlines = [BillItemInline, PaymentInline]


@admin.register(BillItem)
class BillItemAdmin(admin.ModelAdmin):
    list_display = ["item_id", "bill", "charge_type", "description", "amount"]
    list_filter = ["charge_type"]
    search_fields = ["bill__bill_id", "description"]


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = [
        "payment_id",
        "bill",
        "amount_paid",
        "payment_date",
        "method",
        "recorded_by",
        "recorded_at",
    ]
    list_filter = ["method", "recorded_by"]
    search_fields = ["bill__bill_id", "remarks"]


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = [
        "notification_id",
        "student",
        "bill",
        "type",
        "scheduled_at",
        "is_read",
    ]
    list_filter = ["type", "is_read"]
    search_fields = ["student__full_name", "message"]
