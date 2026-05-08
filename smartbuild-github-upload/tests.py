from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase

from .calculations import recalculate_project
from .models import Enterprise, LaborNorm, Material, MaterialCategory, Membership, Project, Supplier


class CalculationTests(TestCase):
    def setUp(self):
        self.enterprise = Enterprise.objects.create(name="TestBuild")
        self.user = User.objects.create_user(username="owner@test.local", password="pass")
        Membership.objects.create(user=self.user, enterprise=self.enterprise, role=Membership.OWNER)
        category = MaterialCategory.objects.create(name="Бетон")
        supplier = Supplier.objects.create(name="Поставщик", lead_time_days=3)
        Material.objects.create(
            category=category,
            supplier=supplier,
            name="Бетон тестовый",
            unit="m3",
            price=5000,
            waste_factor="0.05",
            delivery_days=2,
            alternative_group="foundation_concrete",
            properties={"quantity_per_scope": 1},
        )
        for work_type, group in [
            (LaborNorm.WORK_FOUNDATION, "foundation_concrete"),
            (LaborNorm.WORK_WALLS, "foundation_concrete"),
            (LaborNorm.WORK_ROOF, "foundation_concrete"),
            (LaborNorm.WORK_FACADE, "foundation_concrete"),
            (LaborNorm.WORK_INTERIOR, "foundation_concrete"),
            (LaborNorm.WORK_ENGINEERING, "foundation_concrete"),
        ]:
            LaborNorm.objects.create(
                work_type=work_type,
                name=f"Норма {group}",
                unit="m2",
                productivity_per_worker_day=5,
                base_labor_hours=1,
                tech_break_days=0,
                recommended_crew_size=4,
                labor_rate=800,
            )

    def test_recalculate_project_creates_outputs(self):
        project = Project.objects.create(
            enterprise=self.enterprise,
            owner=self.user,
            name="Объект",
            length=10,
            width=8,
            height=3,
            floors=1,
            start_date=date(2026, 6, 1),
            workers=5,
        )

        summary = recalculate_project(project, user=self.user)

        self.assertGreater(project.estimate_lines.count(), 0)
        self.assertGreater(project.schedule_tasks.count(), 0)
        self.assertGreater(project.procurement_items.count(), 0)
        self.assertGreater(summary["grand_total"], 0)

