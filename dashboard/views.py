from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_403, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import (
    CreateView,
    DeleteView,
    TemplateView,
    UpdateView,
)

from accounts.models import CustomUser, Owner, Student
from .forms import (
    BoardingHouseForm,
    EndTenancyForm,
    RoomForm,
    TenancyAssignmentForm,
    TenancyUpdateForm,
)
from .models import BoardingHouse, Room, Tenancy


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

            context["active_tenancy"] = active_tenancy
            context["past_tenancies"] = past_tenancies
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
        # Refresh room occupancy status in case status changed
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
        tenancy = get_object_or_403(
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
