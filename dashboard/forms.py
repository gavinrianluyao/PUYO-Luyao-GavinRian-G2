from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from accounts.models import CustomUser, Student
from .models import BoardingHouse, Room, Tenancy


class BoardingHouseForm(forms.ModelForm):
    class Meta:
        model = BoardingHouse
        fields = ("name", "address", "house_rules")
        widgets = {
            "house_rules": forms.Textarea(
                attrs={
                    "rows": 4,
                    "placeholder": "Enter boarding house rules and policies (optional)...",
                }
            ),
        }


class RoomForm(forms.ModelForm):
    class Meta:
        model = Room
        fields = ("house", "room_number", "capacity", "monthly_rate", "status")

    def __init__(self, owner=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if owner is not None:
            self.fields["house"].queryset = BoardingHouse.objects.filter(
                owner=owner
            )


class TenancyAssignmentForm(forms.ModelForm):
    monthly_rent = forms.DecimalField(
        required=False,
        max_digits=10,
        decimal_places=2,
        min_value=0,
        help_text="Leave blank to use the room's default rate.",
    )
    start_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}),
        initial=timezone.now,
    )

    class Meta:
        model = Tenancy
        fields = ("student", "room", "start_date", "monthly_rent")

    def __init__(self, owner=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if owner is not None:
            self.fields["room"].queryset = Room.objects.filter(
                house__owner=owner, status=Room.Status.AVAILABLE
            )
        else:
            self.fields["room"].queryset = Room.objects.filter(
                status=Room.Status.AVAILABLE
            )

        # Limit students to active student users without an active tenancy (BR-016, BR-017)
        self.fields["student"].queryset = Student.objects.filter(
            user__role=CustomUser.Role.STUDENT,
            user__is_active=True,
        ).exclude(tenancies__status=Tenancy.Status.ACTIVE)

        self.fields["student"].label_from_instance = (
            lambda obj: f"{obj.full_name} ({obj.user.email})"
        )
        self.fields["room"].label_from_instance = (
            lambda obj: f"{obj.house.name} - Room {obj.room_number} (₱{obj.monthly_rate}/mo, capacity: {obj.capacity}, available: {obj.available_slots})"
        )

    def clean(self):
        cleaned_data = super().clean()
        room = cleaned_data.get("room")
        student = cleaned_data.get("student")
        monthly_rent = cleaned_data.get("monthly_rent")

        if room:
            # BR-013: A room can be assigned only if status is Available
            if room.status != Room.Status.AVAILABLE:
                self.add_error("room", f"Room {room.room_number} is not Available.")

            # BR-014: Cannot exceed room capacity
            if room.active_tenants_count >= room.capacity:
                self.add_error(
                    "room",
                    f"Room {room.room_number} has reached maximum capacity ({room.capacity}).",
                )

            # BR-018: Default monthly rent if not provided
            if monthly_rent is None or monthly_rent == "":
                cleaned_data["monthly_rent"] = room.monthly_rate

        if student:
            # BR-017: Student can only have one active tenancy
            if Tenancy.objects.filter(
                student=student, status=Tenancy.Status.ACTIVE
            ).exists():
                self.add_error(
                    "student", f"{student.full_name} already has an active tenancy."
                )

        return cleaned_data


class TenancyUpdateForm(forms.ModelForm):
    start_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    end_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}),
        required=False,
    )
    monthly_rent = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0,
    )

    class Meta:
        model = Tenancy
        fields = ("monthly_rent", "start_date", "end_date", "status")

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")
        # BR-019: End date cannot be earlier than start date
        if end_date and start_date and end_date < start_date:
            self.add_error(
                "end_date", "The end date cannot be earlier than the start date."
            )
        return cleaned_data


class EndTenancyForm(forms.Form):
    end_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}),
        initial=timezone.now,
        required=True,
        help_text="Date the tenancy ended.",
    )
