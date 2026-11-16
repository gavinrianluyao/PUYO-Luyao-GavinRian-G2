from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    TemplateView,
    UpdateView,
)

from accounts.models import CustomUser, Owner, Student
from .forms import (
    BillCreateForm,
    BillItemForm,
    BillUpdateForm,
    BoardingHouseForm,
    EndTenancyForm,
    PaymentForm,
    RoomForm,
    TenancyAssignmentForm,
    TenancyUpdateForm,
)
from .models import (
    Bill,
    BillItem,
    BoardingHouse,
    Notification,
    Payment,
    Room,
    Tenancy,
    check_and_create_bill_reminders,
)


class OwnerRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    raise_exception = True

    def test_func(self):
        return self.request.user.role == CustomUser.Role.OWNER

    def get_owner_profile(self):
        owner, _ = Owner.objects.get_or_create(
            user=self.request.user,
            defaults={
                "full_name": self.request.user.get_full_name()
                or self.request.user.username,
                "contact_no": (self.request.user.contact_number or "")[:20],
            },
        )
        return owner


# ============================================================================
# Dashboard Views (Read operations for Owner & Student)
# ============================================================================


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context["is_admin"] = user.role == CustomUser.Role.OWNER

        if context["is_admin"]:
            owner, _ = Owner.objects.get_or_create(
                user=user,
                defaults={
                    "full_name": user.get_full_name() or user.username,
                    "contact_no": (user.contact_number or "")[:20],
                },
            )
            houses = BoardingHouse.objects.filter(owner=owner).prefetch_related(
                "rooms"
            )
            rooms = Room.objects.filter(house__owner=owner).select_related(
                "house"
            )
            active_tenancies = (
                Tenancy.objects.filter(
                    room__house__owner=owner, status=Tenancy.Status.ACTIVE
                )
                .select_related("student", "student__user", "room", "room__house")
                .order_by("-start_date")
            )
            bills = Bill.objects.filter(
                tenancy__room__house__owner=owner
            ).select_related("tenancy", "tenancy__student")

            # Update statuses
            for b in bills:
                b.update_status(save=True)
                check_and_create_bill_reminders(b)

            context["houses"] = houses
            context["rooms"] = rooms
            context["houses_count"] = houses.count()
            context["rooms_count"] = rooms.count()
            context["available_rooms_count"] = rooms.filter(
                status=Room.Status.AVAILABLE
            ).count()
            context["occupied_rooms_count"] = rooms.filter(
                status=Room.Status.OCCUPIED
            ).count()
            context["maintenance_rooms_count"] = rooms.filter(
                status=Room.Status.MAINTENANCE
            ).count()
            context["active_tenancies"] = active_tenancies
            context["active_tenancies_count"] = active_tenancies.count()
            context["total_bills_count"] = bills.count()
            context["unpaid_bills_count"] = bills.filter(
                status__in=[Bill.Status.UNPAID, Bill.Status.PARTIAL, Bill.Status.OVERDUE]
            ).count()
            context["recent_bills"] = bills.order_by("-due_date")[:5]
        else:
            student, _ = Student.objects.get_or_create(
                user=user,
                defaults={
                    "full_name": user.get_full_name() or user.username,
                    "contact_no": (user.contact_number or "")[:20],
                },
            )
            active_tenancy = (
                Tenancy.objects.filter(
                    student=student, status=Tenancy.Status.ACTIVE
                )
                .select_related("room", "room__house")
                .first()
            )
            past_tenancies = (
                Tenancy.objects.filter(
                    student=student, status=Tenancy.Status.ENDED
                )
                .select_related("room", "room__house")
                .order_by("-end_date")
            )

            # Check student bills and reminders
            student_bills = Bill.objects.filter(
                tenancy__student=student
            ).order_by("-due_date")
            for b in student_bills:
                b.update_status(save=True)
                check_and_create_bill_reminders(b)

            unread_notifications = Notification.objects.filter(
                student=student, is_read=False
            ).count()

            context["active_tenancy"] = active_tenancy
            context["past_tenancies"] = past_tenancies
            context["student_bills"] = student_bills[:5]
            context["active_bills_count"] = student_bills.filter(
                status__in=[Bill.Status.UNPAID, Bill.Status.PARTIAL, Bill.Status.OVERDUE]
            ).count()
            context["unread_notifications"] = unread_notifications
            if active_tenancy and active_tenancy.room.house.house_rules:
                context["house_rules"] = active_tenancy.room.house.house_rules
            else:
                context["house_rules"] = None

        return context


class AdminPanelView(OwnerRequiredMixin, TemplateView):
    template_name = "dashboard/admin_panel.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        owner = self.get_owner_profile()
        tenancies = (
            Tenancy.objects.filter(room__house__owner=owner)
            .select_related("student", "student__user", "room", "room__house")
            .order_by("-status", "-start_date")
        )
        context["tenancies"] = tenancies
        context["active_count"] = tenancies.filter(
            status=Tenancy.Status.ACTIVE
        ).count()
        context["available_rooms"] = Room.objects.filter(
            house__owner=owner, status=Room.Status.AVAILABLE
        ).select_related("house")
        return context


# ============================================================================
# Boarding House CRUD Views
# ============================================================================


class BoardingHouseCreateView(
    OwnerRequiredMixin, SuccessMessageMixin, CreateView
):
    model = BoardingHouse
    form_class = BoardingHouseForm
    template_name = "dashboard/boarding_house_form.html"
    success_url = reverse_lazy("dashboard")
    success_message = "Boarding house added successfully."

    def form_valid(self, form):
        form.instance.owner = self.get_owner_profile()
        return super().form_valid(form)


class BoardingHouseUpdateView(
    OwnerRequiredMixin, SuccessMessageMixin, UpdateView
):
    model = BoardingHouse
    form_class = BoardingHouseForm
    template_name = "dashboard/boarding_house_form.html"
    success_url = reverse_lazy("dashboard")
    success_message = "Boarding house updated successfully."

    def get_queryset(self):
        return BoardingHouse.objects.filter(owner=self.get_owner_profile())


class BoardingHouseDeleteView(
    OwnerRequiredMixin, SuccessMessageMixin, DeleteView
):
    model = BoardingHouse
    template_name = "dashboard/confirm_delete.html"
    success_url = reverse_lazy("dashboard")
    success_message = "Boarding house deleted successfully."

    def get_queryset(self):
        return BoardingHouse.objects.filter(owner=self.get_owner_profile())


# ============================================================================
# Room CRUD Views
# ============================================================================


class RoomCreateView(OwnerRequiredMixin, SuccessMessageMixin, CreateView):
    model = Room
    form_class = RoomForm
    template_name = "dashboard/room_form.html"
    success_url = reverse_lazy("dashboard")
    success_message = "Room added successfully."

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["owner"] = self.get_owner_profile()
        return kwargs

    def form_valid(self, form):
        if form.instance.house.owner != self.get_owner_profile():
            raise PermissionDenied(
                "You can only add rooms to boarding houses you own."
            )
        return super().form_valid(form)


class RoomUpdateView(OwnerRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Room
    form_class = RoomForm
    template_name = "dashboard/room_form.html"
    success_url = reverse_lazy("dashboard")
    success_message = "Room updated successfully."

    def get_queryset(self):
        return Room.objects.filter(house__owner=self.get_owner_profile())

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["owner"] = self.get_owner_profile()
        return kwargs


class RoomDeleteView(OwnerRequiredMixin, SuccessMessageMixin, DeleteView):
    model = Room
    template_name = "dashboard/confirm_delete.html"
    success_url = reverse_lazy("dashboard")
    success_message = "Room deleted successfully."

    def get_queryset(self):
        return Room.objects.filter(house__owner=self.get_owner_profile())


# ============================================================================
# Tenancy / Room Assignment CRUD Views
# ============================================================================


class RoomAssignmentView(OwnerRequiredMixin, SuccessMessageMixin, CreateView):
    model = Tenancy
    form_class = TenancyAssignmentForm
    template_name = "dashboard/room_assignment_form.html"
    success_url = reverse_lazy("admin_panel")
    success_message = "Student assigned to room successfully."

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["owner"] = self.get_owner_profile()
        return kwargs

    def form_valid(self, form):
        if form.instance.room.house.owner != self.get_owner_profile():
            raise PermissionDenied(
                "You can only assign students to rooms in boarding houses you own."
            )
        return super().form_valid(form)


class TenancyUpdateView(OwnerRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Tenancy
    form_class = TenancyUpdateForm
    template_name = "dashboard/tenancy_form.html"
    success_url = reverse_lazy("admin_panel")
    success_message = "Tenancy updated successfully."

    def get_queryset(self):
        return Tenancy.objects.filter(
            room__house__owner=self.get_owner_profile()
        )

    def form_valid(self, form):
        response = super().form_valid(form)
        form.instance.room.update_occupancy_status(save=True)
        return response


class TenancyDeleteView(OwnerRequiredMixin, SuccessMessageMixin, DeleteView):
    model = Tenancy
    template_name = "dashboard/confirm_delete.html"
    success_url = reverse_lazy("admin_panel")
    success_message = "Tenancy record deleted successfully."

    def get_queryset(self):
        return Tenancy.objects.filter(
            room__house__owner=self.get_owner_profile()
        )

    def form_valid(self, form):
        tenancy = self.get_object()
        room = tenancy.room
        response = super().form_valid(form)
        room.update_occupancy_status(save=True)
        return response


class EndTenancyView(OwnerRequiredMixin, View):
    template_name = "dashboard/end_tenancy_confirm.html"

    def get_tenancy(self, pk):
        owner = self.get_owner_profile()
        tenancy = get_object_or_404(
            Tenancy.objects.select_related(
                "student", "student__user", "room", "room__house"
            ),
            pk=pk,
        )
        if tenancy.room.house.owner != owner:
            raise PermissionDenied(
                "You can only manage tenancies for boarding houses you own."
            )
        return tenancy

    def get(self, request, pk):
        tenancy = self.get_tenancy(pk)
        form = EndTenancyForm(initial={"end_date": timezone.now().date()})
        return render(
            request,
            self.template_name,
            {"tenancy": tenancy, "form": form},
        )

    def post(self, request, pk):
        tenancy = self.get_tenancy(pk)
        form = EndTenancyForm(request.POST)
        if form.is_valid():
            end_date = form.cleaned_data["end_date"]
            tenancy.end_tenancy(end_date=end_date)
            messages.success(
                request,
                f"Tenancy for {tenancy.student.full_name} in Room {tenancy.room.room_number} has been ended.",
            )
            return redirect("admin_panel")
        return render(
            request,
            self.template_name,
            {"tenancy": tenancy, "form": form},
        )


# ============================================================================
# Billing CRUD Views (Owner Management)
# ============================================================================


class BillListView(OwnerRequiredMixin, TemplateView):
    template_name = "dashboard/bill_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        owner = self.get_owner_profile()
        bills = (
            Bill.objects.filter(tenancy__room__house__owner=owner)
            .select_related(
                "tenancy",
                "tenancy__student",
                "tenancy__room",
                "tenancy__room__house",
            )
            .prefetch_related("items", "payments")
        )

        for bill in bills:
            bill.update_status(save=True)
            check_and_create_bill_reminders(bill)

        status_filter = self.request.GET.get("status")
        if status_filter and status_filter in Bill.Status.values:
            filtered_bills = [b for b in bills if b.status == status_filter]
        else:
            filtered_bills = list(bills)

        total_billed = sum(
            b.total_amount for b in bills if b.status != Bill.Status.VOID
        )
        total_collected = sum(
            b.total_payments for b in bills if b.status != Bill.Status.VOID
        )
        total_outstanding = sum(
            b.balance_remaining for b in bills if b.status != Bill.Status.VOID
        )
        overdue_count = sum(
            1 for b in bills if b.status == Bill.Status.OVERDUE
        )

        context["bills"] = filtered_bills
        context["status_filter"] = status_filter
        context["statuses"] = Bill.Status.choices
        context["total_billed"] = total_billed
        context["total_collected"] = total_collected
        context["total_outstanding"] = total_outstanding
        context["overdue_count"] = overdue_count
        return context


class BillCreateView(OwnerRequiredMixin, SuccessMessageMixin, CreateView):
    model = Bill
    form_class = BillCreateForm
    template_name = "dashboard/bill_form.html"
    success_message = "Bill issued successfully."

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["owner"] = self.get_owner_profile()
        return kwargs

    def form_valid(self, form):
        owner = self.get_owner_profile()
        tenancy = form.cleaned_data["tenancy"]

        if tenancy.room.house.owner != owner:
            raise PermissionDenied(
                "You can only issue bills for boarding houses you own (BR-008)."
            )

        form.instance.created_by = owner
        response = super().form_valid(form)
        bill = self.object

        # Create the initial required bill item (BR-023, BR-025)
        BillItem.objects.create(
            bill=bill,
            charge_type=form.cleaned_data["charge_type"],
            description=form.cleaned_data.get("charge_description")
            or "Monthly Rent",
            amount=form.cleaned_data["charge_amount"],
        )
        bill.update_total_amount(save=True)
        check_and_create_bill_reminders(bill)
        return response

    def get_success_url(self):
        return reverse_lazy("bill_detail", kwargs={"pk": self.object.pk})


class BillDetailView(OwnerRequiredMixin, DetailView):
    model = Bill
    template_name = "dashboard/bill_detail.html"
    context_object_name = "bill"

    def get_queryset(self):
        return (
            Bill.objects.filter(
                tenancy__room__house__owner=self.get_owner_profile()
            )
            .select_related(
                "tenancy",
                "tenancy__student",
                "tenancy__room",
                "tenancy__room__house",
                "created_by",
            )
            .prefetch_related("items", "payments", "payments__recorded_by")
        )

    def get_object(self, queryset=None):
        bill = super().get_object(queryset)
        bill.update_status(save=True)
        check_and_create_bill_reminders(bill)
        return bill

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["item_form"] = BillItemForm()
        context["payment_form"] = PaymentForm(bill=self.object)
        return context


class BillUpdateView(OwnerRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Bill
    form_class = BillUpdateForm
    template_name = "dashboard/bill_edit_form.html"
    success_message = "Bill updated successfully."

    def get_queryset(self):
        return Bill.objects.filter(
            tenancy__room__house__owner=self.get_owner_profile()
        )

    def dispatch(self, request, *args, **kwargs):
        bill = self.get_object()
        # BR-028: a bill can be edited only while it is not fully paid
        if not bill.can_edit:
            messages.error(
                request,
                "A fully paid or void bill cannot be edited (BR-028).",
            )
            return redirect("bill_detail", pk=bill.pk)
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse_lazy("bill_detail", kwargs={"pk": self.object.pk})


class BillVoidView(OwnerRequiredMixin, View):
    template_name = "dashboard/bill_void_confirm.html"

    def get_bill(self, pk):
        return get_object_or_404(
            Bill.objects.filter(
                tenancy__room__house__owner=self.get_owner_profile()
            ),
            pk=pk,
        )

    def get(self, request, pk):
        bill = self.get_bill(pk)
        return render(request, self.template_name, {"bill": bill})

    def post(self, request, pk):
        bill = self.get_bill(pk)
        bill.void_bill()  # BR-029: mistaken bill marked void
        messages.success(
            request, f"Bill #{bill.bill_id} has been marked as Void (BR-029)."
        )
        return redirect("bill_detail", pk=bill.pk)


class BillItemCreateView(OwnerRequiredMixin, View):
    def post(self, request, pk):
        bill = get_object_or_404(
            Bill.objects.filter(
                tenancy__room__house__owner=self.get_owner_profile()
            ),
            pk=pk,
        )
        if not bill.can_edit:  # BR-028
            messages.error(
                request, "Cannot add charges to a fully paid or void bill."
            )
            return redirect("bill_detail", pk=bill.pk)

        form = BillItemForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.bill = bill
            item.save()  # Auto updates bill total (BR-026)
            messages.success(
                request,
                f"Added charge: {item.get_charge_type_display()} of ₱{item.amount}.",
            )
        else:
            messages.error(
                request,
                "Error adding charge item. Amount must be greater than 0.",
            )
        return redirect("bill_detail", pk=bill.pk)


class BillItemDeleteView(OwnerRequiredMixin, View):
    def post(self, request, pk):
        item = get_object_or_404(
            BillItem.objects.select_related("bill"),
            pk=pk,
            bill__tenancy__room__house__owner=self.get_owner_profile(),
        )
        bill = item.bill
        if not bill.can_edit:  # BR-028
            messages.error(
                request, "Cannot modify items on a fully paid or void bill."
            )
            return redirect("bill_detail", pk=bill.pk)

        # BR-023: At least one bill item must remain
        if bill.items.count() <= 1:
            messages.error(
                request,
                "A bill must have at least one bill item (BR-023). Cannot delete the last item.",
            )
            return redirect("bill_detail", pk=bill.pk)

        item.delete()  # Auto updates bill total (BR-026)
        messages.success(request, "Bill item deleted successfully.")
        return redirect("bill_detail", pk=bill.pk)


class PaymentCreateView(OwnerRequiredMixin, View):
    def post(self, request, pk):
        bill = get_object_or_404(
            Bill.objects.filter(
                tenancy__room__house__owner=self.get_owner_profile()
            ),
            pk=pk,
        )
        if bill.status == Bill.Status.VOID:
            messages.error(request, "Cannot record payments on a Void bill.")
            return redirect("bill_detail", pk=bill.pk)

        if bill.balance_remaining <= 0:
            messages.info(request, "This bill is already fully paid.")
            return redirect("bill_detail", pk=bill.pk)

        form = PaymentForm(bill=bill, data=request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.bill = bill
            payment.recorded_by = self.get_owner_profile()
            payment.save()  # Auto updates bill status (BR-035)
            messages.success(
                request,
                f"Payment of ₱{payment.amount_paid} recorded via {payment.get_method_display()} (BR-030).",
            )
        else:
            for error in form.errors.values():
                messages.error(request, error)
        return redirect("bill_detail", pk=bill.pk)


class PaymentDeleteView(OwnerRequiredMixin, View):
    def post(self, request, pk):
        payment = get_object_or_404(
            Payment.objects.select_related("bill"),
            pk=pk,
            recorded_by=self.get_owner_profile(),
        )
        bill = payment.bill
        payment.delete()  # Recalculates bill status
        messages.success(request, "Payment record deleted.")
        return redirect("bill_detail", pk=bill.pk)


# ============================================================================
# Student Billing Views (Read-Only per BR-007, BR-037, BR-038)
# ============================================================================


class StudentBillListView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/student_bill_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        if not hasattr(user, "student_profile"):
            student, _ = Student.objects.get_or_create(
                user=user,
                defaults={
                    "full_name": user.get_full_name() or user.username,
                    "contact_no": (user.contact_number or "")[:20],
                },
            )
        else:
            student = user.student_profile

        # BR-037 & BR-038: All bills across current and previous tenancies
        bills = (
            Bill.objects.filter(tenancy__student=student)
            .select_related("tenancy", "tenancy__room", "tenancy__room__house")
            .prefetch_related("items", "payments")
            .order_by("-due_date")
        )

        for b in bills:
            b.update_status(save=True)
            check_and_create_bill_reminders(b)

        active_bills = [
            b
            for b in bills
            if b.status
            in [Bill.Status.UNPAID, Bill.Status.PARTIAL, Bill.Status.OVERDUE]
        ]
        settled_bills = [
            b
            for b in bills
            if b.status in [Bill.Status.PAID, Bill.Status.VOID]
        ]

        total_due = sum(b.balance_remaining for b in active_bills)

        context["active_bills"] = active_bills
        context["settled_bills"] = settled_bills
        context["total_due"] = total_due
        return context


class StudentBillDetailView(LoginRequiredMixin, DetailView):
    model = Bill
    template_name = "dashboard/student_bill_detail.html"
    context_object_name = "bill"

    def get_queryset(self):
        # BR-006: Student can view only their own bills
        student = getattr(self.request.user, "student_profile", None)
        if not student:
            return Bill.objects.none()
        return (
            Bill.objects.filter(tenancy__student=student)
            .select_related(
                "tenancy",
                "tenancy__room",
                "tenancy__room__house",
                "created_by",
            )
            .prefetch_related("items", "payments")
        )


class NotificationListView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/notification_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        student = getattr(self.request.user, "student_profile", None)
        if student:
            notifications = (
                Notification.objects.filter(student=student)
                .select_related("bill", "bill__tenancy__room")
                .order_by("-scheduled_at")
            )
        else:
            notifications = Notification.objects.none()
        context["notifications"] = notifications
        context["unread_count"] = notifications.filter(is_read=False).count()
        return context


class NotificationMarkReadView(LoginRequiredMixin, View):
    def post(self, request, pk):
        student = getattr(request.user, "student_profile", None)
        notification = get_object_or_404(
            Notification,
            pk=pk,
            student=student,
        )
        notification.is_read = True
        notification.save(update_fields=["is_read"])
        messages.success(request, "Reminder marked as read.")
        return redirect("notification_list")
