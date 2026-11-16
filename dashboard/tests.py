from datetime import date, timedelta
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse

from accounts.models import CustomUser, Owner, Student
from dashboard.models import BoardingHouse, Room, Tenancy


class RoomAssignmentTests(TestCase):
    def setUp(self):
        # Create Owner 1
        self.owner_user = CustomUser.objects.create_user(
            username="testowner",
            email="owner@example.com",
            password="OwnerPassword123!",
            role=CustomUser.Role.OWNER,
        )
        self.owner = Owner.objects.get(user=self.owner_user)

        # Create Owner 2 (for multi-tenant isolation tests)
        self.owner_user2 = CustomUser.objects.create_user(
            username="otherowner",
            email="otherowner@example.com",
            password="OwnerPassword123!",
            role=CustomUser.Role.OWNER,
        )
        self.owner2 = Owner.objects.get(user=self.owner_user2)

        # Create Boarding House for Owner 1 (BR-010)
        self.house = BoardingHouse.objects.create(
            owner=self.owner,
            name="Sunrise Dormitory",
            address="123 University Ave",
            house_rules="No loud noise after 10 PM. No smoking inside.",
        )

        # Create Room (BR-011, BR-012)
        self.room = Room.objects.create(
            house=self.house,
            room_number="101",
            capacity=2,
            monthly_rate=Decimal("3500.00"),
            status=Room.Status.AVAILABLE,
        )

        # Create Student 1
        self.student_user1 = CustomUser.objects.create_user(
            username="student1",
            email="student1@example.com",
            password="StudentPass123!",
            role=CustomUser.Role.STUDENT,
        )
        self.student1 = Student.objects.get(user=self.student_user1)

        # Create Student 2
        self.student_user2 = CustomUser.objects.create_user(
            username="student2",
            email="student2@example.com",
            password="StudentPass123!",
            role=CustomUser.Role.STUDENT,
        )
        self.student2 = Student.objects.get(user=self.student_user2)

        # Create Student 3
        self.student_user3 = CustomUser.objects.create_user(
            username="student3",
            email="student3@example.com",
            password="StudentPass123!",
            role=CustomUser.Role.STUDENT,
        )
        self.student3 = Student.objects.get(user=self.student_user3)

    # ------------------------------------------------------------------------
    # Business Rules Tests
    # ------------------------------------------------------------------------

    def test_room_number_unique_per_house(self):
        """BR-011: Room number must be unique within a boarding house."""
        with self.assertRaises(IntegrityError):
            Room.objects.create(
                house=self.house,
                room_number="101",
                capacity=1,
                monthly_rate=Decimal("3000.00"),
            )

    def test_successful_tenancy_assignment(self):
        """BR-018: Assigning a student to an available room records start date and rent."""
        tenancy = Tenancy.objects.create(
            student=self.student1,
            room=self.room,
            start_date=date.today(),
            monthly_rent=Decimal("3500.00"),
        )
        self.assertEqual(tenancy.status, Tenancy.Status.ACTIVE)
        self.assertEqual(tenancy.monthly_rent, Decimal("3500.00"))
        # Room is not full yet (1/2), so still Available
        self.room.refresh_from_db()
        self.assertEqual(self.room.status, Room.Status.AVAILABLE)

    def test_room_status_becomes_occupied_when_full(self):
        """BR-015: When a room reaches capacity, status changes to Occupied."""
        Tenancy.objects.create(
            student=self.student1,
            room=self.room,
            start_date=date.today(),
            monthly_rent=Decimal("3500.00"),
        )
        Tenancy.objects.create(
            student=self.student2,
            room=self.room,
            start_date=date.today(),
            monthly_rent=Decimal("3500.00"),
        )
        self.room.refresh_from_db()
        self.assertEqual(self.room.status, Room.Status.OCCUPIED)

    def test_cannot_assign_to_occupied_or_full_room(self):
        """BR-013, BR-014: Cannot assign to a room that is not Available or exceeds capacity."""
        Tenancy.objects.create(
            student=self.student1,
            room=self.room,
            start_date=date.today(),
            monthly_rent=Decimal("3500.00"),
        )
        Tenancy.objects.create(
            student=self.student2,
            room=self.room,
            start_date=date.today(),
            monthly_rent=Decimal("3500.00"),
        )
        with self.assertRaises(ValidationError):
            tenancy3 = Tenancy(
                student=self.student3,
                room=self.room,
                start_date=date.today(),
                monthly_rent=Decimal("3500.00"),
            )
            tenancy3.clean()

    def test_cannot_assign_to_maintenance_room(self):
        """BR-013: A room can be assigned only if its status is Available."""
        maint_room = Room.objects.create(
            house=self.house,
            room_number="102",
            capacity=2,
            monthly_rate=Decimal("3000.00"),
            status=Room.Status.MAINTENANCE,
        )
        with self.assertRaises(ValidationError):
            tenancy = Tenancy(
                student=self.student1,
                room=maint_room,
                start_date=date.today(),
                monthly_rent=Decimal("3000.00"),
            )
            tenancy.clean()

    def test_student_can_only_have_one_active_tenancy(self):
        """BR-017: A student can have only one active tenancy at a time."""
        Tenancy.objects.create(
            student=self.student1,
            room=self.room,
            start_date=date.today(),
            monthly_rent=Decimal("3500.00"),
        )
        room2 = Room.objects.create(
            house=self.house,
            room_number="103",
            capacity=1,
            monthly_rate=Decimal("4000.00"),
            status=Room.Status.AVAILABLE,
        )
        with self.assertRaises(ValidationError):
            second_tenancy = Tenancy(
                student=self.student1,
                room=room2,
                start_date=date.today(),
                monthly_rent=Decimal("4000.00"),
            )
            second_tenancy.clean()

    def test_end_date_cannot_be_earlier_than_start_date(self):
        """BR-019: End date cannot be earlier than start date."""
        with self.assertRaises(ValidationError):
            tenancy = Tenancy(
                student=self.student1,
                room=self.room,
                start_date=date.today(),
                end_date=date.today() - timedelta(days=5),
                monthly_rent=Decimal("3500.00"),
            )
            tenancy.clean()

    def test_end_tenancy_restores_room_availability(self):
        """BR-015, BR-020: Ending a tenancy sets status to Ended and updates room status."""
        single_room = Room.objects.create(
            house=self.house,
            room_number="104",
            capacity=1,
            monthly_rate=Decimal("5000.00"),
            status=Room.Status.AVAILABLE,
        )
        tenancy = Tenancy.objects.create(
            student=self.student1,
            room=single_room,
            start_date=date.today(),
            monthly_rent=Decimal("5000.00"),
        )
        single_room.refresh_from_db()
        self.assertEqual(single_room.status, Room.Status.OCCUPIED)

        # End tenancy
        tenancy.end_tenancy(end_date=date.today())
        self.assertEqual(tenancy.status, Tenancy.Status.ENDED)
        self.assertIsNotNone(tenancy.end_date)

        single_room.refresh_from_db()
        self.assertEqual(single_room.status, Room.Status.AVAILABLE)

    def test_student_dashboard_displays_room_assignment_and_rules(self):
        """BR-044, BR-045: Student can view their own room assignment and house rules."""
        Tenancy.objects.create(
            student=self.student1,
            room=self.room,
            start_date=date.today(),
            monthly_rent=Decimal("3500.00"),
        )
        self.client.force_login(self.student_user1)
        response = self.client.get(reverse("dashboard"))
        self.assertContains(response, "Sunrise Dormitory")
        self.assertContains(response, "Room 101")
        self.assertContains(response, "3500.00")
        self.assertContains(response, "No loud noise after 10 PM")

    # ------------------------------------------------------------------------
    # Full CRUD Flow Tests (Vertical Slice Requirements)
    # ------------------------------------------------------------------------

    def test_boarding_house_crud(self):
        """Requirement 3: Boarding House Create, Read, Update, Delete."""
        self.client.force_login(self.owner_user)

        # CREATE
        response = self.client.post(
            reverse("boarding_house_add"),
            {
                "name": "Moonlight Dorm",
                "address": "456 College Blvd",
                "house_rules": "Gate closes at 11 PM.",
            },
            follow=True,
        )
        self.assertContains(response, "Boarding house added successfully.")
        new_house = BoardingHouse.objects.get(name="Moonlight Dorm")
        self.assertEqual(new_house.owner, self.owner)

        # READ (on dashboard)
        response = self.client.get(reverse("dashboard"))
        self.assertContains(response, "Moonlight Dorm")

        # UPDATE
        response = self.client.post(
            reverse("boarding_house_edit", kwargs={"pk": new_house.pk}),
            {
                "name": "Moonlight Dormitory Updated",
                "address": "456 College Blvd Updated",
                "house_rules": "Gate closes at midnight.",
            },
            follow=True,
        )
        self.assertContains(response, "Boarding house updated successfully.")
        new_house.refresh_from_db()
        self.assertEqual(new_house.name, "Moonlight Dormitory Updated")

        # DELETE
        response = self.client.post(
            reverse("boarding_house_delete", kwargs={"pk": new_house.pk}),
            follow=True,
        )
        self.assertContains(response, "Boarding house deleted successfully.")
        self.assertFalse(BoardingHouse.objects.filter(pk=new_house.pk).exists())

    def test_room_crud(self):
        """Requirement 3: Room Create, Read, Update, Delete."""
        self.client.force_login(self.owner_user)

        # CREATE
        response = self.client.post(
            reverse("room_add"),
            {
                "house": self.house.pk,
                "room_number": "201",
                "capacity": 3,
                "monthly_rate": "2800.00",
                "status": Room.Status.AVAILABLE,
            },
            follow=True,
        )
        self.assertContains(response, "Room added successfully.")
        new_room = Room.objects.get(house=self.house, room_number="201")
        self.assertEqual(new_room.capacity, 3)

        # READ
        response = self.client.get(reverse("dashboard"))
        self.assertContains(response, "Room 201")

        # UPDATE
        response = self.client.post(
            reverse("room_edit", kwargs={"pk": new_room.pk}),
            {
                "house": self.house.pk,
                "room_number": "201",
                "capacity": 4,
                "monthly_rate": "3000.00",
                "status": Room.Status.AVAILABLE,
            },
            follow=True,
        )
        self.assertContains(response, "Room updated successfully.")
        new_room.refresh_from_db()
        self.assertEqual(new_room.capacity, 4)
        self.assertEqual(new_room.monthly_rate, Decimal("3000.00"))

        # DELETE
        response = self.client.post(
            reverse("room_delete", kwargs={"pk": new_room.pk}),
            follow=True,
        )
        self.assertContains(response, "Room deleted successfully.")
        self.assertFalse(Room.objects.filter(pk=new_room.pk).exists())

    def test_tenancy_crud_and_end(self):
        """Requirement 3: Tenancy Create, Read, Update, End, Delete."""
        self.client.force_login(self.owner_user)

        # CREATE
        response = self.client.post(
            reverse("room_assign"),
            {
                "student": self.student1.pk,
                "room": self.room.pk,
                "start_date": str(date.today()),
                "monthly_rent": "3500.00",
            },
            follow=True,
        )
        self.assertContains(response, "Student assigned to room successfully.")
        tenancy = Tenancy.objects.get(student=self.student1, room=self.room)

        # READ (on admin panel)
        response = self.client.get(reverse("admin_panel"))
        self.assertContains(response, self.student1.full_name)
        self.assertContains(response, "Room 101")

        # UPDATE
        response = self.client.post(
            reverse("tenancy_edit", kwargs={"pk": tenancy.pk}),
            {
                "monthly_rent": "3200.00",
                "start_date": str(date.today()),
                "status": Tenancy.Status.ACTIVE,
            },
            follow=True,
        )
        self.assertContains(response, "Tenancy updated successfully.")
        tenancy.refresh_from_db()
        self.assertEqual(tenancy.monthly_rent, Decimal("3200.00"))

        # END
        response = self.client.post(
            reverse("tenancy_end", kwargs={"pk": tenancy.pk}),
            {"end_date": str(date.today())},
            follow=True,
        )
        self.assertContains(response, "has been ended.")
        tenancy.refresh_from_db()
        self.assertEqual(tenancy.status, Tenancy.Status.ENDED)

        # DELETE
        response = self.client.post(
            reverse("tenancy_delete", kwargs={"pk": tenancy.pk}),
            follow=True,
        )
        self.assertContains(response, "Tenancy record deleted successfully.")
        self.assertFalse(Tenancy.objects.filter(pk=tenancy.pk).exists())

    # ------------------------------------------------------------------------
    # Role-Based Access and Multi-Tenant Isolation Tests (Requirements 5 & 6)
    # ------------------------------------------------------------------------

    def test_student_cannot_access_owner_views(self):
        """Requirement 5 & 6: Non-owners cannot access room assignment or owner endpoints."""
        self.client.force_login(self.student_user1)

        endpoints = [
            reverse("admin_panel"),
            reverse("boarding_house_add"),
            reverse("room_add"),
            reverse("room_assign"),
        ]
        for url in endpoints:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 403)

    def test_owner_cannot_modify_other_owner_records(self):
        """Requirement 5: Users can only view and modify their own records."""
        # Create house for Owner 2
        other_house = BoardingHouse.objects.create(
            owner=self.owner2,
            name="Other Dorm",
            address="789 Avenue",
        )
        other_room = Room.objects.create(
            house=other_house,
            room_number="301",
            capacity=1,
            monthly_rate=Decimal("3000.00"),
        )

        # Log in as Owner 1 and attempt to edit Owner 2's room
        self.client.force_login(self.owner_user)
        response = self.client.get(reverse("room_edit", kwargs={"pk": other_room.pk}))
        self.assertEqual(response.status_code, 404)

        # Attempt to delete Owner 2's house
        response = self.client.post(
            reverse("boarding_house_delete", kwargs={"pk": other_house.pk})
        )
        self.assertEqual(response.status_code, 404)
