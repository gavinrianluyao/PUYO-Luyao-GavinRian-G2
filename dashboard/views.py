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
