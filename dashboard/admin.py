from django.contrib import admin
from .models import BoardingHouse, Room, Tenancy


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
