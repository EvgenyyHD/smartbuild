from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP
from math import ceil

from django.db import transaction
from django.db.models import Case, IntegerField, Q, Value, When
from django.utils import timezone

from .models import (
    AuditEvent,
    EstimateLine,
    LaborNorm,
    Material,
    ProcurementPlan,
    Project,
    ProjectWork,
    ScheduleTask,
)


MONEY = Decimal("0.01")
QTY = Decimal("0.001")

MATERIAL_GROUP_LABELS = {
    "foundation_concrete": "Фундамент и бетон",
    "wall_blocks": "Стеновые материалы",
    "roofing": "Кровельные материалы",
    "facade_finish": "Фасадная отделка",
    "interior_finish": "Внутренняя отделка",
    "engineering_set": "Инженерные комплекты",
}

WORK_CATALOG = {
    LaborNorm.WORK_FOUNDATION: {
        "title": "Устройство фундамента",
        "sequence": 10,
        "material_group": "foundation_concrete",
        "scope_unit": "m3",
    },
    LaborNorm.WORK_WALLS: {
        "title": "Возведение стен",
        "sequence": 20,
        "material_group": "wall_blocks",
        "scope_unit": "m2",
    },
    LaborNorm.WORK_ROOF: {
        "title": "Монтаж кровли",
        "sequence": 30,
        "material_group": "roofing",
        "scope_unit": "m2",
    },
    LaborNorm.WORK_FACADE: {
        "title": "Фасадные работы",
        "sequence": 40,
        "material_group": "facade_finish",
        "scope_unit": "m2",
    },
    LaborNorm.WORK_INTERIOR: {
        "title": "Отделочные работы",
        "sequence": 50,
        "material_group": "interior_finish",
        "scope_unit": "m2",
    },
    LaborNorm.WORK_ENGINEERING: {
        "title": "Инженерные работы",
        "sequence": 60,
        "material_group": "engineering_set",
        "scope_unit": "set",
    },
}


def dec(value, default="0"):
    if value in (None, ""):
        return Decimal(default)
    return Decimal(str(value))


def money(value):
    return dec(value).quantize(MONEY, rounding=ROUND_HALF_UP)


def qty(value):
    return dec(value).quantize(QTY, rounding=ROUND_HALF_UP)


def number(value):
    if isinstance(value, Decimal):
        return float(value)
    return value


def project_floor_area(project):
    if project.area:
        return dec(project.area)
    return dec(project.length) * dec(project.width) * dec(project.floors)


def wall_area(project):
    perimeter = (dec(project.length) + dec(project.width)) * Decimal("2")
    openings_factor = Decimal("0.82")
    return perimeter * dec(project.height) * dec(project.floors) * openings_factor


def calculate_scope(project, work_type):
    floor_area = project_floor_area(project)
    if work_type == LaborNorm.WORK_FOUNDATION:
        slab_thickness = Decimal("0.28")
        return dec(project.length) * dec(project.width) * slab_thickness
    if work_type == LaborNorm.WORK_WALLS:
        return wall_area(project)
    if work_type == LaborNorm.WORK_ROOF:
        roof_slope_factor = Decimal("1.32")
        return dec(project.length) * dec(project.width) * roof_slope_factor
    if work_type == LaborNorm.WORK_FACADE:
        return wall_area(project) * Decimal("0.95")
    if work_type == LaborNorm.WORK_INTERIOR:
        finish_factor = Decimal("2.85")
        return floor_area * finish_factor
    if work_type == LaborNorm.WORK_ENGINEERING:
        return max(Decimal("1"), (floor_area / Decimal("95")).quantize(QTY, rounding=ROUND_HALF_UP))
    return floor_area


def material_quantity(scope_quantity, material, work):
    props = material.properties or {}
    coverage = dec(props.get("coverage_m2_per_unit"))
    quantity_per_scope = dec(props.get("quantity_per_scope"), "1")

    if coverage > 0:
        base_quantity = scope_quantity / coverage
    else:
        base_quantity = scope_quantity * quantity_per_scope

    base_quantity *= dec(work.coefficient, "1")
    with_waste = base_quantity * (Decimal("1") + dec(material.waste_factor))
    if material.unit in {"pcs", "bag", "roll", "set"} or props.get("discrete"):
        return Decimal(ceil(with_waste))
    return qty(with_waste)


def scoped_materials(enterprise, group):
    return Material.objects.filter(
        alternative_group=group,
        is_active=True,
    ).filter(Q(enterprise=enterprise) | Q(enterprise__isnull=True)).select_related("category", "supplier")


def default_material(enterprise, group):
    return (
        scoped_materials(enterprise, group)
        .annotate(
            scope_rank=Case(
                When(enterprise=enterprise, then=Value(0)),
                default=Value(1),
                output_field=IntegerField(),
            )
        )
        .order_by("scope_rank", "price")
        .first()
    )


def labor_norm(enterprise, work_type):
    return (
        LaborNorm.objects.filter(work_type=work_type)
        .filter(Q(enterprise=enterprise) | Q(enterprise__isnull=True))
        .annotate(
            scope_rank=Case(
                When(enterprise=enterprise, then=Value(0)),
                default=Value(1),
                output_field=IntegerField(),
            )
        )
        .order_by("scope_rank", "id")
        .first()
    )


def ensure_project_works(project):
    existing = set(project.works.values_list("work_type", flat=True))
    for work_type, meta in WORK_CATALOG.items():
        if work_type in existing:
            continue
        ProjectWork.objects.create(
            project=project,
            work_type=work_type,
            material=default_material(project.enterprise, meta["material_group"]),
            sequence=meta["sequence"],
        )


def work_financials(project, work, material):
    meta = WORK_CATALOG[work.work_type]
    scope = dec(work.quantity_override) if work.quantity_override else calculate_scope(project, work.work_type)
    scope *= dec(work.coefficient, "1")
    quantity = material_quantity(scope, material, work)
    norm = labor_norm(project.enterprise, work.work_type)

    workers = work.workers_override or project.workers or (norm.recommended_crew_size if norm else 4)
    if norm:
        install_factor = dec((material.properties or {}).get("installation_factor"), "1")
        labor_hours = money(scope * dec(norm.base_labor_hours) * install_factor)
        labor_cost = money(labor_hours * dec(norm.labor_rate))
        productivity = max(dec(norm.productivity_per_worker_day) / install_factor, Decimal("0.001"))
        work_days = max(1, ceil(scope / (productivity * Decimal(workers))))
        tech_break_days = norm.tech_break_days
    else:
        labor_hours = Decimal("0.00")
        labor_cost = Decimal("0.00")
        work_days = 1
        tech_break_days = 0

    material_cost = money(quantity * dec(material.price))
    total_cost = money(material_cost + labor_cost)
    return {
        "meta": meta,
        "scope": qty(scope),
        "scope_unit": meta["scope_unit"],
        "quantity": qty(quantity),
        "unit": material.unit,
        "material_cost": material_cost,
        "labor_hours": labor_hours,
        "labor_cost": labor_cost,
        "total_cost": total_cost,
        "work_days": work_days,
        "tech_break_days": tech_break_days,
        "workers": workers,
    }


@transaction.atomic
def recalculate_project(project, user=None):
    ensure_project_works(project)

    EstimateLine.objects.filter(project=project).delete()
    ScheduleTask.objects.filter(project=project).delete()
    ProcurementPlan.objects.filter(project=project).delete()

    current_start = project.start_date or timezone.localdate()
    summary = {
        "material_cost": Decimal("0.00"),
        "labor_cost": Decimal("0.00"),
        "total_cost": Decimal("0.00"),
        "duration_days": 0,
        "issues": [],
    }

    for work in project.works.filter(enabled=True).order_by("sequence"):
        meta = WORK_CATALOG[work.work_type]
        material = work.material or default_material(project.enterprise, meta["material_group"])
        if not material:
            summary["issues"].append(f"Не найден материал для этапа: {meta['title']}")
            continue
        if work.material_id != material.id:
            work.material = material
            work.save(update_fields=["material"])

        calculated = work_financials(project, work, material)
        EstimateLine.objects.create(
            project=project,
            work_type=work.work_type,
            material=material,
            description=calculated["meta"]["title"],
            quantity=calculated["quantity"],
            unit=calculated["unit"],
            unit_price=material.price,
            waste_factor=material.waste_factor,
            material_cost=calculated["material_cost"],
            labor_hours=calculated["labor_hours"],
            labor_cost=calculated["labor_cost"],
            total_cost=calculated["total_cost"],
        )

        end_date = current_start + timedelta(
            days=calculated["work_days"] + calculated["tech_break_days"] - 1
        )
        task = ScheduleTask.objects.create(
            project=project,
            work_type=work.work_type,
            title=calculated["meta"]["title"],
            sequence=work.sequence,
            start_date=current_start,
            end_date=end_date,
            work_days=calculated["work_days"],
            tech_break_days=calculated["tech_break_days"],
            labor_hours=calculated["labor_hours"],
            workers=calculated["workers"],
        )

        lead_time = material.delivery_days
        if material.supplier:
            lead_time = max(lead_time, material.supplier.lead_time_days)
        ProcurementPlan.objects.create(
            project=project,
            material=material,
            supplier=material.supplier,
            quantity=calculated["quantity"],
            unit=material.unit,
            needed_by=task.start_date,
            order_before=task.start_date - timedelta(days=lead_time),
            lead_time_days=lead_time,
            estimated_cost=calculated["material_cost"],
        )

        summary["material_cost"] += calculated["material_cost"]
        summary["labor_cost"] += calculated["labor_cost"]
        summary["total_cost"] += calculated["total_cost"]
        summary["duration_days"] = (end_date - project.start_date).days + 1
        current_start = end_date + timedelta(days=1)

    contingency = money(summary["total_cost"] * dec(project.contingency_percent) / Decimal("100"))
    grand_total = money(summary["total_cost"] + contingency)
    project.status = Project.CALCULATED
    project.save(update_fields=["status", "updated_at"])

    AuditEvent.objects.create(
        enterprise=project.enterprise,
        user=user,
        action="project.recalculate",
        entity="project",
        entity_id=str(project.id),
        payload={"total_cost": str(grand_total), "duration_days": summary["duration_days"]},
    )

    return {
        "material_cost": money(summary["material_cost"]),
        "labor_cost": money(summary["labor_cost"]),
        "direct_cost": money(summary["total_cost"]),
        "contingency": contingency,
        "grand_total": grand_total,
        "duration_days": summary["duration_days"],
        "issues": summary["issues"],
    }


def replacement_options(project, work_type):
    ensure_project_works(project)
    work = project.works.filter(work_type=work_type).first()
    if not work:
        return []

    meta = WORK_CATALOG[work_type]
    current_material = work.material or default_material(project.enterprise, meta["material_group"])
    if not current_material:
        return []

    current = work_financials(project, work, current_material)
    options = []
    for material in scoped_materials(project.enterprise, current_material.alternative_group):
        calculated = work_financials(project, work, material)
        options.append(
            {
                "material_id": material.id,
                "name": material.name,
                "unit": material.unit,
                "price": float(material.price),
                "supplier": material.supplier.name if material.supplier else None,
                "delivery_days": material.delivery_days,
                "quantity": float(calculated["quantity"]),
                "total_cost": float(calculated["total_cost"]),
                "cost_delta": float(calculated["total_cost"] - current["total_cost"]),
                "work_days": calculated["work_days"],
                "duration_delta": calculated["work_days"] - current["work_days"],
                "waste_factor": float(material.waste_factor),
                "is_current": material.id == current_material.id,
            }
        )
    return sorted(options, key=lambda item: (item["total_cost"], item["delivery_days"]))
