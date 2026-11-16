from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from accounts.models import CustomUser, Student
from .models import Bill, BillItem, BoardingHouse, Payment, Room, Tenancy


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



class BillCreateForm(forms.ModelForm):
    period_start = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}),
        initial=timezone.now,
    )
    period_end = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}),
        initial=timezone.now,
    )
    due_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}),
        initial=timezone.now,
    )
    # BR-023: At least one bill item must be provided when creating a bill
    charge_type = forms.ChoiceField(
        choices=BillItem.ChargeType.choices,
        initial=BillItem.ChargeType.RENT,
        help_text="Initial charge category (BR-023, BR-025)",
    )
    charge_description = forms.CharField(
        max_length=255,
        required=False,
        initial="Monthly Rent",
        widget=forms.TextInput(attrs={"placeholder": "e.g. Monthly Room Rent"}),
    )
    charge_amount = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0.01,
        help_text="Charge amount must be greater than 0 (BR-025)",
    )

    class Meta:
        model = Bill
        fields = ("tenancy", "period_start", "period_end", "due_date")

    def __init__(self, owner=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if owner is not None:
            self.fields["tenancy"].queryset = Tenancy.objects.filter(
                room__house__owner=owner
            ).select_related("student", "room", "room__house")
        else:
            self.fields["tenancy"].queryset = Tenancy.objects.select_related(
                "student", "room", "room__house"
            )

        self.fields["tenancy"].label_from_instance = (
            lambda t: f"{t.student.full_name} — {t.room} (Tenancy #{t.pk})"
        )

    def clean(self):
        cleaned_data = super().clean()
        tenancy = cleaned_data.get("tenancy")
        period_start = cleaned_data.get("period_start")
        period_end = cleaned_data.get("period_end")
        due_date = cleaned_data.get("due_date")
        charge_amount = cleaned_data.get("charge_amount")

        if period_start and due_date and due_date < period_start:
            self.add_error(
                "due_date",
                "The due date cannot be earlier than the start of the billing period (BR-024).",
            )

        if period_start and period_end and period_end < period_start:
            self.add_error(
                "period_end",
                "The billing period end date cannot be earlier than its start date.",
            )

        if tenancy and period_start and period_end:
            existing = (
                Bill.objects.filter(
                    tenancy=tenancy,
                    period_start=period_start,
                    period_end=period_end,
                )
                .exclude(status=Bill.Status.VOID)
            )
            if existing.exists():
                self.add_error(
                    "tenancy",
                    "A bill already exists for this tenancy during this billing period (BR-027). Add additional charges as bill items instead.",
                )

        if charge_amount is not None and charge_amount <= 0:
            self.add_error(
                "charge_amount", "Charge amount must be greater than 0 (BR-025)."
            )

        return cleaned_data


class BillUpdateForm(forms.ModelForm):
    period_start = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    period_end = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    due_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    class Meta:
        model = Bill
        fields = ("period_start", "period_end", "due_date")

    def clean(self):
        cleaned_data = super().clean()
        period_start = cleaned_data.get("period_start")
        period_end = cleaned_data.get("period_end")
        due_date = cleaned_data.get("due_date")

        if period_start and due_date and due_date < period_start:
            self.add_error(
                "due_date",
                "The due date cannot be earlier than the start of the billing period (BR-024).",
            )

        if period_start and period_end and period_end < period_start:
            self.add_error(
                "period_end",
                "The billing period end date cannot be earlier than its start date.",
            )

        return cleaned_data


class BillItemForm(forms.ModelForm):
    amount = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0.01,
        help_text="Amount must be greater than 0 (BR-025).",
    )

    class Meta:
        model = BillItem
        fields = ("charge_type", "description", "amount")


class PaymentForm(forms.ModelForm):
    amount_paid = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0.01,
        help_text="Amount must be greater than 0 and cannot exceed the bill balance (BR-033).",
    )
    payment_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}),
        initial=timezone.now,
    )

    class Meta:
        model = Payment
        fields = ("amount_paid", "payment_date", "method", "remarks")

    def __init__(self, bill=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bill = bill
        if bill and "amount_paid" not in self.data and not self.is_bound:
            self.fields["amount_paid"].initial = bill.balance_remaining

    def clean_amount_paid(self):
        amount = self.cleaned_data.get("amount_paid")
        if amount is not None and amount <= 0:
            raise forms.ValidationError("Payment amount must be greater than 0.")

        if self.bill:
            if self.bill.status == Bill.Status.VOID:
                raise forms.ValidationError(
                    "Cannot record a payment for a Void bill."
                )

            current_payments = self.bill.total_payments
            if self.instance.pk:
                current_payments -= self.instance.amount_paid

            if (current_payments + amount) > self.bill.total_amount:
                max_payable = self.bill.total_amount - current_payments
                raise forms.ValidationError(
                    f"Payment of ₱{amount} exceeds remaining balance. Maximum payable is ₱{max_payable} (BR-033)."
                )

        return amount
