from django.urls import path
from .views import (
    AdminPanelView,
    BoardingHouseCreateView,
    BoardingHouseDeleteView,
    BoardingHouseUpdateView,
    DashboardView,
    EndTenancyView,
    RoomAssignmentView,
    RoomCreateView,
    RoomDeleteView,
    RoomUpdateView,
    TenancyDeleteView,
    TenancyUpdateView,
)

urlpatterns = [
    path("", DashboardView.as_view(), name="dashboard"),
    path("admin-panel/", AdminPanelView.as_view(), name="admin_panel"),
    # Boarding House CRUD
    path(
        "boarding-houses/add/",
        BoardingHouseCreateView.as_view(),
        name="boarding_house_add",
    ),
    path(
        "boarding-houses/<int:pk>/edit/",
        BoardingHouseUpdateView.as_view(),
        name="boarding_house_edit",
    ),
    path(
        "boarding-houses/<int:pk>/delete/",
        BoardingHouseDeleteView.as_view(),
        name="boarding_house_delete",
    ),
    # Room CRUD
    path("rooms/add/", RoomCreateView.as_view(), name="room_add"),
    path("rooms/<int:pk>/edit/", RoomUpdateView.as_view(), name="room_edit"),
    path(
        "rooms/<int:pk>/delete/",
        RoomDeleteView.as_view(),
        name="room_delete",
    ),
    # Tenancy / Room Assignment CRUD
    path("rooms/assign/", RoomAssignmentView.as_view(), name="room_assign"),
    path(
        "tenancies/<int:pk>/edit/",
        TenancyUpdateView.as_view(),
        name="tenancy_edit",
    ),
    path(
        "tenancies/<int:pk>/delete/",
        TenancyDeleteView.as_view(),
        name="tenancy_delete",
    ),
    path(
        "tenancies/<int:pk>/end/",
        EndTenancyView.as_view(),
        name="tenancy_end",
    ),
]
