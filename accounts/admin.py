from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Owner, Student


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ["username", "email", "role", "is_active", "is_staff"]
    list_filter = ["role", "is_active", "is_staff"]
    fieldsets = UserAdmin.fieldsets + (
        ("Boarding House Role", {"fields": ("role", "contact_number")}),
    )


@admin.register(Owner)
class OwnerAdmin(admin.ModelAdmin):
    list_display = ["user", "full_name", "contact_no"]
    search_fields = ["full_name", "user__email", "user__username"]


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ["user", "full_name", "contact_no", "school_id", "course_year"]
    search_fields = ["full_name", "school_id", "user__email", "user__username"]
