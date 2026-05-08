import hashlib
from secrets import token_urlsafe

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class Enterprise(models.Model):
    PERSONAL = "personal"
    COMPANY = "company"
    SUPPLIER = "supplier"
    KIND_CHOICES = [
        (PERSONAL, "Личное пространство"),
        (COMPANY, "Компания"),
        (SUPPLIER, "Поставщик"),
    ]

    name = models.CharField(max_length=180, unique=True)
    kind = models.CharField(max_length=20, choices=KIND_CHOICES, default=COMPANY)
    inn = models.CharField(max_length=20, blank=True)
    contact_email = models.EmailField(blank=True)
    phone = models.CharField(max_length=40, blank=True)
    address = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Membership(models.Model):
    OWNER = "owner"
    ADMIN = "admin"
    FOREMAN = "foreman"
    ESTIMATOR = "estimator"
    VIEWER = "viewer"
    ROLE_CHOICES = [
        (OWNER, "Владелец"),
        (ADMIN, "Администратор"),
        (FOREMAN, "Прораб"),
        (ESTIMATOR, "Сметчик"),
        (VIEWER, "Наблюдатель"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="memberships")
    enterprise = models.ForeignKey(Enterprise, on_delete=models.CASCADE, related_name="memberships")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=VIEWER)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("user", "enterprise")]

    def __str__(self):
        return f"{self.user.username} / {self.enterprise.name} / {self.role}"


class Supplier(models.Model):
    enterprise = models.ForeignKey(
        Enterprise, null=True, blank=True, on_delete=models.CASCADE, related_name="suppliers"
    )
    name = models.CharField(max_length=180)
    lead_time_days = models.PositiveSmallIntegerField(default=5)
    reliability_percent = models.PositiveSmallIntegerField(default=95)
    phone = models.CharField(max_length=40, blank=True)
    email = models.EmailField(blank=True)
    address = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        unique_together = [("enterprise", "name")]

    def __str__(self):
        return self.name


class SupplierProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="supplier_profile")
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name="accounts")
    can_manage_catalog = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["supplier__name"]

    def __str__(self):
        return f"{self.user.username} / {self.supplier.name}"


class MaterialCategory(models.Model):
    name = models.CharField(max_length=120, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Material(models.Model):
    UNIT_CHOICES = [
        ("m3", "м3"),
        ("m2", "м2"),
        ("pcs", "шт"),
        ("kg", "кг"),
        ("bag", "мешок"),
        ("roll", "рулон"),
        ("set", "комплект"),
    ]

    enterprise = models.ForeignKey(
        Enterprise, null=True, blank=True, on_delete=models.CASCADE, related_name="materials"
    )
    category = models.ForeignKey(MaterialCategory, on_delete=models.PROTECT, related_name="materials")
    supplier = models.ForeignKey(
        Supplier, null=True, blank=True, on_delete=models.SET_NULL, related_name="materials"
    )
    name = models.CharField(max_length=180)
    unit = models.CharField(max_length=12, choices=UNIT_CHOICES)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    waste_factor = models.DecimalField(max_digits=5, decimal_places=3, default=0.050)
    delivery_days = models.PositiveSmallIntegerField(default=5)
    stock_level = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    alternative_group = models.CharField(max_length=80, db_index=True)
    properties = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["category__name", "name"]
        unique_together = [("enterprise", "name", "alternative_group")]

    def __str__(self):
        return self.name


class LaborNorm(models.Model):
    WORK_FOUNDATION = "foundation"
    WORK_WALLS = "walls"
    WORK_ROOF = "roof"
    WORK_FACADE = "facade"
    WORK_INTERIOR = "interior"
    WORK_ENGINEERING = "engineering"
    WORK_CHOICES = [
        (WORK_FOUNDATION, "Фундамент"),
        (WORK_WALLS, "Стены"),
        (WORK_ROOF, "Кровля"),
        (WORK_FACADE, "Фасад"),
        (WORK_INTERIOR, "Отделка"),
        (WORK_ENGINEERING, "Инженерные работы"),
    ]

    enterprise = models.ForeignKey(
        Enterprise, null=True, blank=True, on_delete=models.CASCADE, related_name="labor_norms"
    )
    work_type = models.CharField(max_length=30, choices=WORK_CHOICES, db_index=True)
    name = models.CharField(max_length=180)
    unit = models.CharField(max_length=12, default="m2")
    productivity_per_worker_day = models.DecimalField(max_digits=12, decimal_places=3)
    base_labor_hours = models.DecimalField(max_digits=12, decimal_places=3)
    tech_break_days = models.PositiveSmallIntegerField(default=0)
    recommended_crew_size = models.PositiveSmallIntegerField(default=4)
    labor_rate = models.DecimalField(max_digits=12, decimal_places=2, default=850)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["work_type", "name"]
        unique_together = [("enterprise", "work_type", "name")]

    def __str__(self):
        return f"{self.get_work_type_display()} - {self.name}"


class Project(models.Model):
    HOUSE = "house"
    APARTMENT = "apartment"
    OFFICE = "office"
    RETAIL = "retail"
    AUXILIARY = "auxiliary"
    OBJECT_CHOICES = [
        (HOUSE, "Жилой дом"),
        (APARTMENT, "Квартира"),
        (OFFICE, "Офис"),
        (RETAIL, "Торговое помещение"),
        (AUXILIARY, "Вспомогательное сооружение"),
    ]

    DRAFT = "draft"
    CALCULATED = "calculated"
    IN_PROGRESS = "in_progress"
    ARCHIVED = "archived"
    STATUS_CHOICES = [
        (DRAFT, "Черновик"),
        (CALCULATED, "Рассчитан"),
        (IN_PROGRESS, "В работе"),
        (ARCHIVED, "Архив"),
    ]

    enterprise = models.ForeignKey(Enterprise, on_delete=models.CASCADE, related_name="projects")
    owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="projects")
    name = models.CharField(max_length=180)
    object_type = models.CharField(max_length=20, choices=OBJECT_CHOICES, default=HOUSE)
    address = models.CharField(max_length=255, blank=True)
    length = models.DecimalField(max_digits=10, decimal_places=2)
    width = models.DecimalField(max_digits=10, decimal_places=2)
    height = models.DecimalField(max_digits=10, decimal_places=2)
    floors = models.PositiveSmallIntegerField(default=1)
    area = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    start_date = models.DateField(default=timezone.localdate)
    workers = models.PositiveSmallIntegerField(default=6)
    contingency_percent = models.DecimalField(max_digits=5, decimal_places=2, default=7)
    currency = models.CharField(max_length=8, default="RUB")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=DRAFT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return self.name


class ProjectWork(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="works")
    work_type = models.CharField(max_length=30, choices=LaborNorm.WORK_CHOICES)
    material = models.ForeignKey(Material, null=True, blank=True, on_delete=models.SET_NULL)
    enabled = models.BooleanField(default=True)
    sequence = models.PositiveSmallIntegerField(default=10)
    coefficient = models.DecimalField(max_digits=7, decimal_places=3, default=1)
    quantity_override = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)
    workers_override = models.PositiveSmallIntegerField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["sequence"]
        unique_together = [("project", "work_type")]

    def __str__(self):
        return f"{self.project.name} - {self.get_work_type_display()}"


class ProjectParticipant(models.Model):
    DEVELOPER = "developer"
    FOREMAN = "foreman"
    BUILDER = "builder"
    ESTIMATOR = "estimator"
    VIEWER = "viewer"
    ROLE_CHOICES = [
        (DEVELOPER, "Застройщик"),
        (FOREMAN, "Прораб"),
        (BUILDER, "Исполнитель"),
        (ESTIMATOR, "Сметчик"),
        (VIEWER, "Наблюдатель"),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="participants")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="project_participations")
    enterprise = models.ForeignKey(
        Enterprise, null=True, blank=True, on_delete=models.SET_NULL, related_name="project_participations"
    )
    role = models.CharField(max_length=24, choices=ROLE_CHOICES, default=VIEWER)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["project__name", "role", "user__last_name"]
        unique_together = [("project", "user")]

    def __str__(self):
        return f"{self.project.name} / {self.user.username} / {self.role}"


class ProjectSeat(models.Model):
    OPEN = "open"
    ASSIGNED = "assigned"
    CANCELLED = "cancelled"
    STATUS_CHOICES = [
        (OPEN, "Ожидает участника"),
        (ASSIGNED, "Назначен"),
        (CANCELLED, "Отменено"),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="seats")
    title = models.CharField(max_length=180)
    planned_role = models.CharField(max_length=24, choices=ProjectParticipant.ROLE_CHOICES, default=ProjectParticipant.VIEWER)
    contact_name = models.CharField(max_length=180, blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=40, blank=True)
    note = models.TextField(blank=True)
    assigned_user = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="project_seats"
    )
    assigned_enterprise = models.ForeignKey(
        Enterprise, null=True, blank=True, on_delete=models.SET_NULL, related_name="project_seats"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=OPEN)
    created_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="created_project_seats"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["status", "id"]

    def __str__(self):
        return f"{self.project.name} / {self.title}"


class ProjectJoinRequest(models.Model):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    STATUS_CHOICES = [
        (PENDING, "На рассмотрении"),
        (APPROVED, "Принята"),
        (REJECTED, "Отклонена"),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="join_requests")
    applicant = models.ForeignKey(User, on_delete=models.CASCADE, related_name="project_join_requests")
    applicant_enterprise = models.ForeignKey(
        Enterprise, null=True, blank=True, on_delete=models.SET_NULL, related_name="project_join_requests"
    )
    requested_role = models.CharField(max_length=24, choices=ProjectParticipant.ROLE_CHOICES, default=ProjectParticipant.VIEWER)
    message = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    decided_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="decided_join_requests")
    decision_comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.project.name} / {self.applicant.username} / {self.status}"


class EstimateLine(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="estimate_lines")
    work_type = models.CharField(max_length=30, choices=LaborNorm.WORK_CHOICES)
    material = models.ForeignKey(Material, null=True, blank=True, on_delete=models.SET_NULL)
    description = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=14, decimal_places=3)
    unit = models.CharField(max_length=12)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    waste_factor = models.DecimalField(max_digits=5, decimal_places=3, default=0)
    material_cost = models.DecimalField(max_digits=14, decimal_places=2)
    labor_hours = models.DecimalField(max_digits=14, decimal_places=2)
    labor_cost = models.DecimalField(max_digits=14, decimal_places=2)
    total_cost = models.DecimalField(max_digits=14, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]


class ScheduleTask(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="schedule_tasks")
    work_type = models.CharField(max_length=30, choices=LaborNorm.WORK_CHOICES)
    title = models.CharField(max_length=180)
    sequence = models.PositiveSmallIntegerField(default=10)
    start_date = models.DateField()
    end_date = models.DateField()
    work_days = models.PositiveSmallIntegerField(default=1)
    tech_break_days = models.PositiveSmallIntegerField(default=0)
    labor_hours = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    workers = models.PositiveSmallIntegerField(default=1)
    status = models.CharField(max_length=40, default="planned")

    class Meta:
        ordering = ["sequence", "start_date"]


class ProjectGoal(models.Model):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    BLOCKED = "blocked"
    STATUS_CHOICES = [
        (TODO, "К выполнению"),
        (IN_PROGRESS, "В работе"),
        (DONE, "Готово"),
        (BLOCKED, "Заблокировано"),
    ]

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    PRIORITY_CHOICES = [
        (LOW, "Низкий"),
        (NORMAL, "Обычный"),
        (HIGH, "Высокий"),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="goals")
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.CASCADE, related_name="subgoals"
    )
    title = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    assignee = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="assigned_goals")
    created_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="created_goals")
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=TODO)
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default=NORMAL)
    sequence = models.PositiveSmallIntegerField(default=10)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["status", "due_date", "sequence", "id"]

    def __str__(self):
        return self.title


class ProcurementPlan(models.Model):
    PLANNED = "planned"
    ORDERED = "ordered"
    DELIVERED = "delivered"
    STATUS_CHOICES = [
        (PLANNED, "Запланировано"),
        (ORDERED, "Заказано"),
        (DELIVERED, "Поставлено"),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="procurement_items")
    material = models.ForeignKey(Material, null=True, blank=True, on_delete=models.SET_NULL)
    supplier = models.ForeignKey(Supplier, null=True, blank=True, on_delete=models.SET_NULL)
    quantity = models.DecimalField(max_digits=14, decimal_places=3)
    unit = models.CharField(max_length=12)
    needed_by = models.DateField()
    order_before = models.DateField()
    lead_time_days = models.PositiveSmallIntegerField(default=1)
    estimated_cost = models.DecimalField(max_digits=14, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PLANNED)

    class Meta:
        ordering = ["order_before", "needed_by"]


class ApiAccessToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="api_tokens")
    key_hash = models.CharField(max_length=64, unique=True)
    prefix = models.CharField(max_length=12)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    @classmethod
    def issue(cls, user, request=None):
        raw_key = token_urlsafe(40)
        key_hash = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
        meta = getattr(request, "META", {}) if request else {}
        token = cls.objects.create(
            user=user,
            key_hash=key_hash,
            prefix=raw_key[:10],
            user_agent=meta.get("HTTP_USER_AGENT", "")[:255],
            ip_address=meta.get("REMOTE_ADDR") or None,
        )
        return raw_key, token

    @classmethod
    def hash_key(cls, raw_key):
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    @property
    def is_active(self):
        if self.revoked_at:
            return False
        if self.expires_at and self.expires_at <= timezone.now():
            return False
        return True


class AuditEvent(models.Model):
    enterprise = models.ForeignKey(
        Enterprise, null=True, blank=True, on_delete=models.SET_NULL, related_name="audit_events"
    )
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=120)
    entity = models.CharField(max_length=120, blank=True)
    entity_id = models.CharField(max_length=80, blank=True)
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class SupplierApplication(models.Model):
    NEW = "new"
    CONTACTED = "contacted"
    APPROVED = "approved"
    REJECTED = "rejected"
    STATUS_CHOICES = [
        (NEW, "Новая"),
        (CONTACTED, "Связались"),
        (APPROVED, "Одобрена"),
        (REJECTED, "Отклонена"),
    ]

    company_name = models.CharField(max_length=180)
    contact_name = models.CharField(max_length=180)
    email = models.EmailField()
    phone = models.CharField(max_length=40, blank=True)
    city = models.CharField(max_length=120, blank=True)
    materials = models.CharField(max_length=255, blank=True)
    message = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=NEW)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.company_name} / {self.email}"
