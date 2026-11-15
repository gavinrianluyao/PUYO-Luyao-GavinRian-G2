from django.shortcuts import render
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.views.generic import CreateView, DetailView, UpdateView
from .forms import CustomUserCreationForm, UserProfileForm
from .models import CustomUser

# Create your views here.


class SignUpView(CreateView):
    form_class = CustomUserCreationForm
    success_url = reverse_lazy('login')
    template_name = 'registration/signup.html'


class ProfileView(LoginRequiredMixin, DetailView):
    model = CustomUser
    context_object_name = "profile"
    template_name = "accounts/profile.html"

    def get_object(self, queryset=None):
        return self.request.user


class ProfileUpdateView(
    LoginRequiredMixin, SuccessMessageMixin, UpdateView
):
    model = CustomUser
    form_class = UserProfileForm
    context_object_name = "profile"
    template_name = "accounts/profile_edit.html"
    success_url = reverse_lazy("profile")
    success_message = "Your profile has been updated."

    def get_object(self, queryset=None):
        return self.request.user