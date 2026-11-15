from django.shortcuts import render
from django.contrib.auth.mixins import (
    LoginRequiredMixin, UserPassesTestMixin)
from django.views.generic import TemplateView
from accounts.models import CustomUser

# Create your views here.

class AdminPanelView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'dashboard/admin_panel.html'

    def test_func(self):
        return self.request.user.role == CustomUser.Role.OWNER

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["members"] = CustomUser.objects.filter(
            role=CustomUser.Role.STUDENT
        ).order_by("username")
        return context

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["is_admin"] = self.request.user.role == CustomUser.Role.OWNER
        if context["is_admin"]:
            context["member_count"] = CustomUser.objects.filter(
                role=CustomUser.Role.STUDENT
            ).count()
        return context