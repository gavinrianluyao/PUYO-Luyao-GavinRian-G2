from django.urls import path
from .views import (
    AdminPanelView,
    BillCreateView,
    BillDetailView,
    BillItemCreateView,
    BillItemDeleteView,
    BillListView,
    BillUpdateView,
    BillVoidView,
    BoardingHouseCreateView,
    BoardingHouseDeleteView,
    BoardingHouseUpdateView,
    DashboardView,
    EndTenancyView,
    NotificationListView,
    NotificationMarkReadView,
    PaymentCreateView,
    PaymentDeleteView,
    RoomAssignmentView,
    RoomCreateView,
    RoomDeleteView,
    RoomUpdateView,
    StudentBillDetailView,
    StudentBillListView,
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
    # Billing CRUD (Owner)
    path("bills/", BillListView.as_view(), name="bill_list"),
    path("bills/add/", BillCreateView.as_view(), name="bill_add"),
    path("bills/<int:pk>/", BillDetailView.as_view(), name="bill_detail"),
    path("bills/<int:pk>/edit/", BillUpdateView.as_view(), name="bill_edit"),
    path("bills/<int:pk>/void/", BillVoidView.as_view(), name="bill_void"),
    path(
        "bills/<int:pk>/items/add/",
        BillItemCreateView.as_view(),
        name="bill_item_add",
    ),
    path(
        "items/<int:pk>/delete/",
        BillItemDeleteView.as_view(),
        name="bill_item_delete",
    ),
    path(
        "bills/<int:pk>/payments/add/",
        PaymentCreateView.as_view(),
        name="payment_add",
    ),
    path(
        "payments/<int:pk>/delete/",
        PaymentDeleteView.as_view(),
        name="payment_delete",
    ),
    # Student Billing Views
    path("my-bills/", StudentBillListView.as_view(), name="student_bill_list"),
    path(
        "my-bills/<int:pk>/",
        StudentBillDetailView.as_view(),
        name="student_bill_detail",
    ),
    path(
        "notifications/",
        NotificationListView.as_view(),
        name="notification_list",
    ),
    path(
        "notifications/<int:pk>/read/",
        NotificationMarkReadView.as_view(),
        name="notification_read",
    ),
]
