from django.contrib import admin

from .models import (
    ApiAccessToken,
    AuditEvent,
    Enterprise,
    EstimateLine,
    LaborNorm,
    Material,
    MaterialCategory,
    Membership,
    ProcurementPlan,
    Project,
    ProjectGoal,
    ProjectJoinRequest,
    ProjectParticipant,
    ProjectSeat,
    ProjectWork,
    ScheduleTask,
    Supplier,
    SupplierApplication,
    SupplierProfile,
)


@admin.register(Enterprise)
class EnterpriseAdmin(admin.ModelAdmin):
    list_display = ("name", "kind", "inn", "contact_email", "is_active")
    list_filter = ("kind", "is_active")
    search_fields = ("name", "inn", "contact_email")


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "enterprise", "role", "is_active")
    list_filter = ("role", "is_active")


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ("name", "enterprise", "lead_time_days", "reliability_percent", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "email", "phone")


@admin.register(SupplierProfile)
class SupplierProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "supplier", "can_manage_catalog", "created_at")
    list_filter = ("can_manage_catalog",)
    search_fields = ("user__username", "supplier__name")


@admin.register(MaterialCategory)
class MaterialCategoryAdmin(admin.ModelAdmin):
    search_fields = ("name",)


@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "enterprise", "supplier", "unit", "price", "alternative_group")
    list_filter = ("category", "alternative_group", "is_active")
    search_fields = ("name",)


@admin.register(LaborNorm)
class LaborNormAdmin(admin.ModelAdmin):
    list_display = ("name", "work_type", "enterprise", "productivity_per_worker_day", "tech_break_days")
    list_filter = ("work_type",)


class ProjectWorkInline(admin.TabularInline):
    model = ProjectWork
    extra = 0


class ProjectParticipantInline(admin.TabularInline):
    model = ProjectParticipant
    extra = 0


class ProjectSeatInline(admin.TabularInline):
    model = ProjectSeat
    extra = 0


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "enterprise", "object_type", "status", "start_date", "workers")
    list_filter = ("status", "object_type", "enterprise")
    search_fields = ("name", "address")
    inlines = [ProjectWorkInline, ProjectParticipantInline, ProjectSeatInline]


@admin.register(ProjectParticipant)
class ProjectParticipantAdmin(admin.ModelAdmin):
    list_display = ("project", "user", "enterprise", "role", "is_active")
    list_filter = ("role", "is_active")
    search_fields = ("project__name", "user__username", "enterprise__name")


@admin.register(ProjectJoinRequest)
class ProjectJoinRequestAdmin(admin.ModelAdmin):
    list_display = ("project", "applicant", "requested_role", "status", "created_at")
    list_filter = ("status", "requested_role")
    search_fields = ("project__name", "applicant__username", "message")


@admin.register(ProjectSeat)
class ProjectSeatAdmin(admin.ModelAdmin):
    list_display = ("project", "title", "planned_role", "status", "assigned_user", "contact_email")
    list_filter = ("planned_role", "status")
    search_fields = ("project__name", "title", "contact_name", "contact_email", "assigned_user__username")


@admin.register(EstimateLine)
class EstimateLineAdmin(admin.ModelAdmin):
    list_display = ("project", "work_type", "material", "quantity", "total_cost")
    list_filter = ("work_type",)


@admin.register(ScheduleTask)
class ScheduleTaskAdmin(admin.ModelAdmin):
    list_display = ("project", "title", "start_date", "end_date", "workers")
    list_filter = ("work_type", "status")


@admin.register(ProjectGoal)
class ProjectGoalAdmin(admin.ModelAdmin):
    list_display = ("project", "title", "assignee", "due_date", "status", "priority")
    list_filter = ("status", "priority")
    search_fields = ("project__name", "title", "assignee__username")


@admin.register(ProcurementPlan)
class ProcurementPlanAdmin(admin.ModelAdmin):
    list_display = ("project", "material", "supplier", "order_before", "needed_by", "status")
    list_filter = ("status",)


@admin.register(ApiAccessToken)
class ApiAccessTokenAdmin(admin.ModelAdmin):
    list_display = ("user", "prefix", "created_at", "expires_at", "revoked_at")
    readonly_fields = ("key_hash", "prefix")


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ("created_at", "enterprise", "user", "action", "entity", "entity_id")
    list_filter = ("action",)


@admin.register(SupplierApplication)
class SupplierApplicationAdmin(admin.ModelAdmin):
    list_display = ("company_name", "contact_name", "email", "city", "status", "created_at")
    list_filter = ("status", "city")
    search_fields = ("company_name", "contact_name", "email", "materials")
