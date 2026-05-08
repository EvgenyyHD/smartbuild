import json
from decimal import Decimal

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Q, Sum
from django.http import JsonResponse
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.decorators.csrf import csrf_exempt

from .auth import authenticate_token, membership_for_request, revoke_token
from .calculations import MATERIAL_GROUP_LABELS, WORK_CATALOG, ensure_project_works, recalculate_project, replacement_options
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


WRITE_ROLES = {Membership.OWNER, Membership.ADMIN, Membership.FOREMAN, Membership.ESTIMATOR}
ADMIN_ROLES = {Membership.OWNER, Membership.ADMIN}
PROJECT_WRITE_ROLES = {ProjectParticipant.DEVELOPER, ProjectParticipant.FOREMAN, ProjectParticipant.ESTIMATOR}
WORKING_PROJECT_ROLES = {ProjectParticipant.FOREMAN, ProjectParticipant.BUILDER, ProjectParticipant.ESTIMATOR}


def decimal_value(value):
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    return value


def json_error(message, status=400, code="bad_request"):
    return JsonResponse({"error": {"code": code, "message": message}}, status=status)


def read_payload(request):
    if not request.body:
        return {}
    try:
        return json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return None


def api_endpoint(methods, auth_required=True, enterprise_required=True):
    def decorator(func):
        @csrf_exempt
        def wrapper(request, *args, **kwargs):
            if request.method not in methods:
                return json_error("Метод не поддерживается", status=405, code="method_not_allowed")

            if auth_required:
                user, token = authenticate_token(request)
                if not user:
                    return json_error("Требуется авторизация", status=401, code="unauthorized")
                request.user = user
                request.api_token = token
                if enterprise_required:
                    membership = membership_for_request(request, user)
                    if not membership:
                        return json_error("Нет доступа к выбранной организации", status=403, code="forbidden")
                    request.enterprise = membership.enterprise
                    request.membership = membership

            return func(request, *args, **kwargs)

        return wrapper

    return decorator


def require_write(request):
    if request.membership.role not in WRITE_ROLES:
        return json_error("Недостаточно прав для изменения данных", status=403, code="forbidden")
    return None


def require_admin(request):
    if request.membership.role not in ADMIN_ROLES:
        return json_error("Доступно только администраторам организации", status=403, code="forbidden")
    return None


def serialize_user(user):
    memberships = []
    for membership in user.memberships.select_related("enterprise").filter(is_active=True, enterprise__is_active=True):
        memberships.append(
            {
                "enterprise_id": membership.enterprise_id,
                "enterprise_name": membership.enterprise.name,
                "enterprise_kind": membership.enterprise.kind,
                "enterprise_kind_label": membership.enterprise.get_kind_display(),
                "role": membership.role,
                "role_label": membership.get_role_display(),
            }
        )
    try:
        supplier_profile = user.supplier_profile
    except SupplierProfile.DoesNotExist:
        supplier_profile = None
    supplier_payload = None
    if supplier_profile:
        supplier_payload = serialize_supplier(supplier_profile.supplier)
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "memberships": memberships,
        "supplier_profile": supplier_payload,
    }


def serialize_supplier(supplier):
    return {
        "id": supplier.id,
        "name": supplier.name,
        "lead_time_days": supplier.lead_time_days,
        "reliability_percent": supplier.reliability_percent,
        "phone": supplier.phone,
        "email": supplier.email,
        "address": supplier.address,
        "is_global": supplier.enterprise_id is None,
    }


def serialize_material(material):
    return {
        "id": material.id,
        "name": material.name,
        "category": material.category.name,
        "category_id": material.category_id,
        "supplier": serialize_supplier(material.supplier) if material.supplier else None,
        "unit": material.unit,
        "price": decimal_value(material.price),
        "waste_factor": decimal_value(material.waste_factor),
        "delivery_days": material.delivery_days,
        "stock_level": decimal_value(material.stock_level),
        "alternative_group": material.alternative_group,
        "alternative_group_label": MATERIAL_GROUP_LABELS.get(material.alternative_group, material.alternative_group),
        "properties": material.properties,
        "is_global": material.enterprise_id is None,
    }


def serialize_work(work):
    return {
        "id": work.id,
        "work_type": work.work_type,
        "work_label": work.get_work_type_display(),
        "enabled": work.enabled,
        "sequence": work.sequence,
        "coefficient": decimal_value(work.coefficient),
        "quantity_override": decimal_value(work.quantity_override),
        "workers_override": work.workers_override,
        "material": serialize_material(work.material) if work.material else None,
        "notes": work.notes,
    }


def display_user(user):
    if not user:
        return ""
    full_name = " ".join(part for part in [user.first_name, user.last_name] if part).strip()
    return full_name or user.email or user.username


def project_role_for_user(project, user):
    if not user or not getattr(user, "is_authenticated", False):
        return None
    if project.owner_id == user.id:
        return ProjectParticipant.DEVELOPER
    participant = project.participants.filter(user=user, is_active=True).first()
    return participant.role if participant else None


def can_manage_project(user, project):
    if project.owner_id == user.id:
        return True
    return Membership.objects.filter(
        user=user,
        enterprise=project.enterprise,
        is_active=True,
        role__in=ADMIN_ROLES,
    ).exists()


def can_write_project(user, project):
    if can_manage_project(user, project):
        return True
    role = project_role_for_user(project, user)
    return role in PROJECT_WRITE_ROLES


def require_project_write(request, project):
    if not can_write_project(request.user, project):
        return json_error("Недостаточно прав для изменения проекта", status=403, code="forbidden")
    return None


def require_project_manager(request, project):
    if not can_manage_project(request.user, project):
        return json_error("Заявками и участниками управляет владелец проекта", status=403, code="forbidden")
    return None


def user_enterprise_for_project(user, project):
    participant = project.participants.filter(user=user, is_active=True).select_related("enterprise").first()
    if participant and participant.enterprise:
        return participant.enterprise
    membership = user.memberships.filter(enterprise=project.enterprise, is_active=True).first()
    return membership.enterprise if membership else None


def serialize_participant(participant):
    return {
        "id": participant.id,
        "user_id": participant.user_id,
        "name": display_user(participant.user),
        "email": participant.user.email,
        "enterprise_id": participant.enterprise_id,
        "enterprise_name": participant.enterprise.name if participant.enterprise else "",
        "enterprise_kind": participant.enterprise.kind if participant.enterprise else "",
        "role": participant.role,
        "role_label": participant.get_role_display(),
        "is_active": participant.is_active,
    }


def serialize_seat(seat):
    return {
        "id": seat.id,
        "title": seat.title,
        "planned_role": seat.planned_role,
        "planned_role_label": seat.get_planned_role_display(),
        "contact_name": seat.contact_name,
        "contact_email": seat.contact_email,
        "contact_phone": seat.contact_phone,
        "note": seat.note,
        "assigned_user_id": seat.assigned_user_id,
        "assigned_user_name": display_user(seat.assigned_user),
        "assigned_user_email": seat.assigned_user.email if seat.assigned_user else "",
        "assigned_enterprise_id": seat.assigned_enterprise_id,
        "assigned_enterprise_name": seat.assigned_enterprise.name if seat.assigned_enterprise else "",
        "assigned_enterprise_kind": seat.assigned_enterprise.kind if seat.assigned_enterprise else "",
        "status": seat.status,
        "status_label": seat.get_status_display(),
        "created_at": seat.created_at.isoformat(),
        "updated_at": seat.updated_at.isoformat(),
    }


def serialize_join_request(join_request):
    return {
        "id": join_request.id,
        "project_id": join_request.project_id,
        "project_name": join_request.project.name,
        "applicant_id": join_request.applicant_id,
        "applicant_name": display_user(join_request.applicant),
        "applicant_email": join_request.applicant.email,
        "applicant_enterprise_id": join_request.applicant_enterprise_id,
        "applicant_enterprise_name": join_request.applicant_enterprise.name if join_request.applicant_enterprise else "",
        "requested_role": join_request.requested_role,
        "requested_role_label": join_request.get_requested_role_display(),
        "message": join_request.message,
        "status": join_request.status,
        "status_label": join_request.get_status_display(),
        "decision_comment": join_request.decision_comment,
        "created_at": join_request.created_at.isoformat(),
    }


def serialize_goal(goal):
    return {
        "id": goal.id,
        "parent_id": goal.parent_id,
        "title": goal.title,
        "description": goal.description,
        "assignee_id": goal.assignee_id,
        "assignee_name": display_user(goal.assignee),
        "due_date": goal.due_date.isoformat() if goal.due_date else "",
        "status": goal.status,
        "status_label": goal.get_status_display(),
        "priority": goal.priority,
        "priority_label": goal.get_priority_display(),
        "sequence": goal.sequence,
        "updated_at": goal.updated_at.isoformat(),
    }


def serialize_project(project, include_totals=True, user=None):
    role = project_role_for_user(project, user) if user else None
    membership_role_label = ""
    if user and not role:
        membership = user.memberships.filter(enterprise=project.enterprise, is_active=True).first()
        membership_role_label = membership.get_role_display() if membership else ""
    payload = {
        "id": project.id,
        "name": project.name,
        "enterprise_id": project.enterprise_id,
        "enterprise_name": project.enterprise.name,
        "owner_id": project.owner_id,
        "owner_name": display_user(project.owner),
        "project_role": role,
        "project_role_label": dict(ProjectParticipant.ROLE_CHOICES).get(role, "") or membership_role_label,
        "access_kind": "participant" if user and role and project.enterprise_id not in user.memberships.filter(is_active=True).values_list("enterprise_id", flat=True) else "workspace",
        "object_type": project.object_type,
        "object_type_label": project.get_object_type_display(),
        "address": project.address,
        "length": decimal_value(project.length),
        "width": decimal_value(project.width),
        "height": decimal_value(project.height),
        "floors": project.floors,
        "area": decimal_value(project.area),
        "start_date": project.start_date.isoformat(),
        "workers": project.workers,
        "contingency_percent": decimal_value(project.contingency_percent),
        "currency": project.currency,
        "status": project.status,
        "status_label": project.get_status_display(),
        "updated_at": project.updated_at.isoformat(),
    }
    if include_totals:
        totals = project.estimate_lines.aggregate(
            material_cost=Sum("material_cost"),
            labor_cost=Sum("labor_cost"),
            total_cost=Sum("total_cost"),
        )
        direct = totals["total_cost"] or Decimal("0")
        contingency = direct * project.contingency_percent / Decimal("100")
        payload["totals"] = {
            "material_cost": decimal_value(totals["material_cost"] or Decimal("0")),
            "labor_cost": decimal_value(totals["labor_cost"] or Decimal("0")),
            "direct_cost": decimal_value(direct),
            "contingency": decimal_value(contingency),
            "grand_total": decimal_value(direct + contingency),
        }
    return payload


def serialize_estimate(line):
    return {
        "id": line.id,
        "work_type": line.work_type,
        "work_label": line.get_work_type_display(),
        "material": serialize_material(line.material) if line.material else None,
        "description": line.description,
        "quantity": decimal_value(line.quantity),
        "unit": line.unit,
        "unit_price": decimal_value(line.unit_price),
        "waste_factor": decimal_value(line.waste_factor),
        "material_cost": decimal_value(line.material_cost),
        "labor_hours": decimal_value(line.labor_hours),
        "labor_cost": decimal_value(line.labor_cost),
        "total_cost": decimal_value(line.total_cost),
    }


def serialize_task(task):
    return {
        "id": task.id,
        "work_type": task.work_type,
        "work_label": task.get_work_type_display(),
        "title": task.title,
        "sequence": task.sequence,
        "start_date": task.start_date.isoformat(),
        "end_date": task.end_date.isoformat(),
        "work_days": task.work_days,
        "tech_break_days": task.tech_break_days,
        "labor_hours": decimal_value(task.labor_hours),
        "workers": task.workers,
        "status": task.status,
    }


def serialize_procurement(item):
    return {
        "id": item.id,
        "material": serialize_material(item.material) if item.material else None,
        "supplier": serialize_supplier(item.supplier) if item.supplier else None,
        "quantity": decimal_value(item.quantity),
        "unit": item.unit,
        "needed_by": item.needed_by.isoformat(),
        "order_before": item.order_before.isoformat(),
        "lead_time_days": item.lead_time_days,
        "estimated_cost": decimal_value(item.estimated_cost),
        "status": item.status,
        "status_label": item.get_status_display(),
    }


def project_queryset(request):
    return (
        Project.objects.filter(
            Q(enterprise=request.enterprise)
            | Q(participants__user=request.user, participants__is_active=True)
            | Q(owner=request.user)
        )
        .select_related("enterprise", "owner")
        .distinct()
    )


def project_payload(project, user=None):
    ensure_project_works(project)
    return {
        "project": serialize_project(project, user=user),
        "works": [serialize_work(work) for work in project.works.select_related("material", "material__category", "material__supplier")],
        "estimate": [serialize_estimate(line) for line in project.estimate_lines.select_related("material", "material__category", "material__supplier")],
        "schedule": [serialize_task(task) for task in project.schedule_tasks.all()],
        "procurement": [serialize_procurement(item) for item in project.procurement_items.select_related("material", "material__category", "material__supplier", "supplier")],
        "participants": [
            serialize_participant(item)
            for item in project.participants.select_related("user", "enterprise").filter(is_active=True)
        ],
        "seats": [
            serialize_seat(item)
            for item in project.seats.select_related("assigned_user", "assigned_enterprise").all()
        ],
        "goals": [
            serialize_goal(item)
            for item in project.goals.select_related("assignee", "created_by").all()
        ],
        "join_requests": [
            serialize_join_request(item)
            for item in project.join_requests.select_related("applicant", "applicant_enterprise", "project").all()[:20]
        ],
    }


@api_endpoint(["GET"], auth_required=False, enterprise_required=False)
def health(request):
    return JsonResponse({"status": "ok", "service": "SmartBuild API"})


@api_endpoint(["POST"], auth_required=False, enterprise_required=False)
def supplier_application(request):
    payload = read_payload(request)
    if payload is None:
        return json_error("Некорректный JSON")
    company_name = (payload.get("company_name") or "").strip()
    contact_name = (payload.get("contact_name") or "").strip()
    email = (payload.get("email") or "").strip().lower()
    if not company_name or not contact_name or not email:
        return json_error("Укажите компанию, контактное лицо и email")
    application = SupplierApplication.objects.create(
        company_name=company_name,
        contact_name=contact_name,
        email=email,
        phone=(payload.get("phone") or "").strip(),
        city=(payload.get("city") or "").strip(),
        materials=(payload.get("materials") or "").strip(),
        message=(payload.get("message") or "").strip(),
    )
    return JsonResponse({"status": "sent", "application_id": application.id}, status=201)


@api_endpoint(["POST"], auth_required=False, enterprise_required=False)
def login(request):
    payload = read_payload(request)
    if payload is None:
        return json_error("Некорректный JSON")

    username = (payload.get("username") or payload.get("email") or "").strip()
    password = payload.get("password") or ""
    user = authenticate(username=username, password=password)
    if user is None:
        candidate = User.objects.filter(email__iexact=username).first()
        if candidate and candidate.check_password(password):
            user = candidate
    if user is None or not user.is_active:
        return json_error("Неверный логин или пароль", status=401, code="invalid_credentials")

    raw_key, token = ApiAccessToken.issue(user, request)
    AuditEvent.objects.create(user=user, action="auth.login", entity="user", entity_id=str(user.id))
    return JsonResponse({"token": raw_key, "token_prefix": token.prefix, "user": serialize_user(user)})


def unique_enterprise_name(base_name):
    name = base_name.strip()[:180] or "Рабочее пространство"
    if not Enterprise.objects.filter(name=name).exists():
        return name
    counter = 2
    while True:
        suffix = f" {counter}"
        candidate = f"{name[:180 - len(suffix)]}{suffix}"
        if not Enterprise.objects.filter(name=candidate).exists():
            return candidate
        counter += 1


def request_value(payload, field, default):
    value = payload.get(field, default)
    return default if value in (None, "") else value


@api_endpoint(["POST"], auth_required=False, enterprise_required=False)
def register(request):
    payload = read_payload(request)
    if payload is None:
        return json_error("Некорректный JSON")

    email = (payload.get("email") or payload.get("username") or "").strip().lower()
    password = payload.get("password") or ""
    first_name = (payload.get("first_name") or "").strip()
    last_name = (payload.get("last_name") or "").strip()
    account_type = payload.get("account_type") or ("company" if payload.get("is_company") else "personal")

    if not email or "@" not in email:
        return json_error("Укажите корректный email")
    if len(password) < 8:
        return json_error("Пароль должен содержать не менее 8 символов")
    if User.objects.filter(Q(username__iexact=email) | Q(email__iexact=email)).exists():
        return json_error("Пользователь с таким email уже зарегистрирован", status=409, code="user_exists")
    if account_type not in {Enterprise.PERSONAL, Enterprise.COMPANY, Enterprise.SUPPLIER}:
        return json_error("Неизвестный тип регистрации")
    company_name = (payload.get("company_name") or "").strip()
    supplier_name = (payload.get("supplier_name") or payload.get("company_name") or "").strip()
    if account_type == Enterprise.COMPANY and not company_name:
        return json_error("Укажите название компании")
    if account_type == Enterprise.SUPPLIER and not supplier_name:
        return json_error("Укажите название поставщика")

    display_name = " ".join(part for part in [first_name, last_name] if part).strip() or email.split("@")[0]
    with transaction.atomic():
        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
        )

        if account_type == Enterprise.COMPANY:
            enterprise = Enterprise.objects.create(
                name=unique_enterprise_name(company_name),
                kind=Enterprise.COMPANY,
                inn=(payload.get("inn") or "").strip(),
                contact_email=email,
                phone=(payload.get("phone") or "").strip(),
                address=(payload.get("address") or "").strip(),
            )
        elif account_type == Enterprise.SUPPLIER:
            enterprise = Enterprise.objects.create(
                name=unique_enterprise_name(f"Поставщик: {supplier_name}"),
                kind=Enterprise.SUPPLIER,
                inn=(payload.get("inn") or "").strip(),
                contact_email=email,
                phone=(payload.get("phone") or "").strip(),
                address=(payload.get("address") or "").strip(),
            )
            supplier = Supplier.objects.create(
                enterprise=enterprise,
                name=supplier_name,
                lead_time_days=int(request_value(payload, "lead_time_days", 5)),
                reliability_percent=95,
                email=email,
                phone=(payload.get("phone") or "").strip(),
                address=(payload.get("address") or "").strip(),
            )
            SupplierProfile.objects.create(user=user, supplier=supplier)
        else:
            enterprise = Enterprise.objects.create(
                name=unique_enterprise_name(f"Личное пространство: {display_name}"),
                kind=Enterprise.PERSONAL,
                contact_email=email,
                phone=(payload.get("phone") or "").strip(),
            )

        Membership.objects.create(user=user, enterprise=enterprise, role=Membership.OWNER)
        raw_key, token = ApiAccessToken.issue(user, request)
        AuditEvent.objects.create(
            enterprise=enterprise,
            user=user,
            action="auth.register",
            entity="user",
            entity_id=str(user.id),
            payload={"account_type": account_type},
        )

    return JsonResponse({"token": raw_key, "token_prefix": token.prefix, "user": serialize_user(user)}, status=201)


@api_endpoint(["POST"], enterprise_required=False)
def logout(request):
    revoke_token(request.api_token)
    return JsonResponse({"status": "logged_out"})


@api_endpoint(["GET"], enterprise_required=False)
def me(request):
    return JsonResponse({"user": serialize_user(request.user)})


@api_endpoint(["GET"])
def dashboard(request):
    projects = project_queryset(request)
    today = timezone.localdate()
    procurements = ProcurementPlan.objects.filter(project__in=projects).order_by("order_before")[:8]
    totals = EstimateLine.objects.filter(project__in=projects).aggregate(
        material_cost=Sum("material_cost"),
        labor_cost=Sum("labor_cost"),
        total_cost=Sum("total_cost"),
    )
    status_counts = {
        key: projects.filter(status=key).count()
        for key, _label in Project.STATUS_CHOICES
    }
    return JsonResponse(
        {
            "enterprise": {
                "id": request.enterprise.id,
                "name": request.enterprise.name,
                "kind": request.enterprise.kind,
                "kind_label": request.enterprise.get_kind_display(),
                "role": request.membership.role,
            },
            "cards": {
                "projects": projects.count(),
                "materials": Material.objects.filter(
                    Q(enterprise=request.enterprise) | Q(enterprise__isnull=True), is_active=True
                ).count(),
                "suppliers": Supplier.objects.filter(
                    Q(enterprise=request.enterprise) | Q(enterprise__isnull=True), is_active=True
                ).count(),
                "planned_orders": ProcurementPlan.objects.filter(
                    project__in=projects,
                    order_before__gte=today,
                    status=ProcurementPlan.PLANNED,
                ).count(),
                "my_goals": ProjectGoal.objects.filter(project__in=projects, assignee=request.user)
                .exclude(status=ProjectGoal.DONE)
                .count(),
            },
            "status_counts": status_counts,
            "totals": {
                "material_cost": decimal_value(totals["material_cost"] or Decimal("0")),
                "labor_cost": decimal_value(totals["labor_cost"] or Decimal("0")),
                "direct_cost": decimal_value(totals["total_cost"] or Decimal("0")),
            },
            "upcoming_procurement": [serialize_procurement(item) for item in procurements],
            "my_goals": [
                serialize_goal(item)
                for item in ProjectGoal.objects.filter(project__in=projects, assignee=request.user)
                .exclude(status=ProjectGoal.DONE)
                .select_related("project", "assignee")[:8]
            ],
            "join_requests": [
                serialize_join_request(item)
                for item in ProjectJoinRequest.objects.filter(project__in=projects, status=ProjectJoinRequest.PENDING)
                .select_related("project", "applicant", "applicant_enterprise")[:8]
            ],
        }
    )


@api_endpoint(["GET", "POST"])
def suppliers(request):
    if request.method == "GET":
        queryset = Supplier.objects.filter(
            Q(enterprise=request.enterprise) | Q(enterprise__isnull=True), is_active=True
        )
        return JsonResponse({"suppliers": [serialize_supplier(item) for item in queryset]})

    denied = require_admin(request)
    if denied:
        return denied
    payload = read_payload(request)
    if payload is None:
        return json_error("Некорректный JSON")
    supplier = Supplier.objects.create(
        enterprise=request.enterprise,
        name=payload.get("name", "").strip(),
        lead_time_days=int(payload.get("lead_time_days", 5)),
        reliability_percent=int(payload.get("reliability_percent", 95)),
        phone=payload.get("phone", ""),
        email=payload.get("email", ""),
        address=payload.get("address", ""),
    )
    return JsonResponse({"supplier": serialize_supplier(supplier)}, status=201)


@api_endpoint(["GET", "POST"])
def materials(request):
    if request.method == "GET":
        queryset = Material.objects.filter(
            Q(enterprise=request.enterprise) | Q(enterprise__isnull=True), is_active=True
        ).select_related("category", "supplier")
        search = request.GET.get("search")
        group = request.GET.get("group")
        if search:
            queryset = queryset.filter(name__icontains=search)
        if group:
            queryset = queryset.filter(alternative_group=group)
        return JsonResponse({"materials": [serialize_material(item) for item in queryset]})

    denied = require_admin(request)
    if denied:
        return denied
    payload = read_payload(request)
    if payload is None:
        return json_error("Некорректный JSON")
    category, _created = MaterialCategory.objects.get_or_create(name=payload.get("category", "Материалы"))
    try:
        supplier_profile = request.user.supplier_profile
    except SupplierProfile.DoesNotExist:
        supplier_profile = None
    is_supplier_space = request.enterprise.kind == Enterprise.SUPPLIER and supplier_profile
    supplier = None
    if is_supplier_space:
        supplier = supplier_profile.supplier
    elif payload.get("supplier_id"):
        supplier = Supplier.objects.filter(
            Q(enterprise=request.enterprise) | Q(enterprise__isnull=True), id=payload["supplier_id"]
        ).first()
    material_name = payload.get("name", "").strip()
    if not material_name:
        return json_error("Укажите название материала")
    material = Material.objects.create(
        enterprise=None if is_supplier_space else request.enterprise,
        category=category,
        supplier=supplier,
        name=material_name,
        unit=payload.get("unit", "m2"),
        price=request_value(payload, "price", 0),
        waste_factor=request_value(payload, "waste_factor", "0.05"),
        delivery_days=int(request_value(payload, "delivery_days", 5)),
        stock_level=request_value(payload, "stock_level", 0),
        alternative_group=payload.get("alternative_group", "custom"),
        properties=payload.get("properties", {}),
    )
    return JsonResponse({"material": serialize_material(material)}, status=201)


@api_endpoint(["GET"])
def labor_norms(request):
    queryset = (
        LaborNorm.objects.filter(Q(enterprise=request.enterprise) | Q(enterprise__isnull=True))
        .order_by("work_type")
    )
    return JsonResponse(
        {
            "labor_norms": [
                {
                    "id": item.id,
                    "work_type": item.work_type,
                    "work_label": item.get_work_type_display(),
                    "name": item.name,
                    "unit": item.unit,
                    "productivity_per_worker_day": decimal_value(item.productivity_per_worker_day),
                    "base_labor_hours": decimal_value(item.base_labor_hours),
                    "tech_break_days": item.tech_break_days,
                    "recommended_crew_size": item.recommended_crew_size,
                    "labor_rate": decimal_value(item.labor_rate),
                }
                for item in queryset
            ]
        }
    )


@api_endpoint(["GET", "POST"])
def projects(request):
    if request.method == "GET":
        items = [serialize_project(project, user=request.user) for project in project_queryset(request)]
        return JsonResponse({"projects": items})

    denied = require_write(request)
    if denied:
        return denied
    payload = read_payload(request)
    if payload is None:
        return json_error("Некорректный JSON")
    start_date = parse_date(payload.get("start_date", "")) or timezone.localdate()
    project = Project.objects.create(
        enterprise=request.enterprise,
        owner=request.user,
        name=payload.get("name", "Новый объект").strip(),
        object_type=payload.get("object_type", Project.HOUSE),
        address=payload.get("address", ""),
        length=request_value(payload, "length", 10),
        width=request_value(payload, "width", 8),
        height=request_value(payload, "height", 3),
        floors=int(request_value(payload, "floors", 1)),
        area=payload.get("area") or None,
        start_date=start_date,
        workers=int(request_value(payload, "workers", 6)),
        contingency_percent=request_value(payload, "contingency_percent", 7),
    )
    ProjectParticipant.objects.update_or_create(
        project=project,
        user=request.user,
        defaults={"enterprise": request.enterprise, "role": ProjectParticipant.DEVELOPER, "is_active": True},
    )
    recalculate_project(project, user=request.user)
    return JsonResponse(project_payload(project, request.user), status=201)


@api_endpoint(["GET", "PATCH", "DELETE"])
def project_detail(request, project_id):
    project = project_queryset(request).filter(id=project_id).first()
    if not project:
        return json_error("Проект не найден", status=404, code="not_found")

    if request.method == "GET":
        return JsonResponse(project_payload(project, request.user))

    if request.method == "DELETE":
        denied = require_project_manager(request, project)
        if denied:
            return denied
        project.delete()
        return JsonResponse({"status": "deleted"})

    denied = require_project_write(request, project)
    if denied:
        return denied
    payload = read_payload(request)
    if payload is None:
        return json_error("Некорректный JSON")
    editable_fields = {
        "name",
        "object_type",
        "address",
        "length",
        "width",
        "height",
        "floors",
        "area",
        "start_date",
        "workers",
        "contingency_percent",
        "status",
    }
    for field in editable_fields:
        if field not in payload:
            continue
        value = payload[field]
        if field == "start_date":
            value = parse_date(value) or project.start_date
        setattr(project, field, value)
    project.save()
    recalculate_project(project, user=request.user)
    return JsonResponse(project_payload(project, request.user))


@api_endpoint(["GET", "POST"])
def project_calculate(request, project_id):
    project = project_queryset(request).filter(id=project_id).first()
    if not project:
        return json_error("Проект не найден", status=404, code="not_found")
    if request.method == "POST":
        denied = require_project_write(request, project)
        if denied:
            return denied
        summary = recalculate_project(project, user=request.user)
        payload = project_payload(project, request.user)
        payload["summary"] = {key: decimal_value(value) for key, value in summary.items()}
        return JsonResponse(payload)
    return JsonResponse(project_payload(project, request.user))


@api_endpoint(["PATCH"])
def project_works(request, project_id):
    project = project_queryset(request).filter(id=project_id).first()
    if not project:
        return json_error("Проект не найден", status=404, code="not_found")
    denied = require_project_write(request, project)
    if denied:
        return denied
    payload = read_payload(request)
    if payload is None:
        return json_error("Некорректный JSON")

    ensure_project_works(project)
    for item in payload.get("works", []):
        work = project.works.filter(work_type=item.get("work_type")).first()
        if not work:
            continue
        if "enabled" in item:
            work.enabled = bool(item["enabled"])
        if "coefficient" in item:
            work.coefficient = item["coefficient"]
        if "quantity_override" in item:
            work.quantity_override = item["quantity_override"] or None
        if "workers_override" in item:
            work.workers_override = item["workers_override"] or None
        if item.get("material_id"):
            material = Material.objects.filter(
                id=item["material_id"],
            ).filter(
                Q(enterprise=request.enterprise) | Q(enterprise__isnull=True)
            ).first()
            if material:
                work.material = material
        work.save()
    summary = recalculate_project(project, user=request.user)
    payload = project_payload(project, request.user)
    payload["summary"] = {key: decimal_value(value) for key, value in summary.items()}
    return JsonResponse(payload)


@api_endpoint(["GET", "POST"])
def project_alternatives(request, project_id):
    project = project_queryset(request).filter(id=project_id).first()
    if not project:
        return json_error("Проект не найден", status=404, code="not_found")
    if request.method == "GET":
        work_type = request.GET.get("work_type") or LaborNorm.WORK_WALLS
        if work_type not in WORK_CATALOG:
            return json_error("Неизвестный тип работ")
        return JsonResponse({"alternatives": replacement_options(project, work_type)})

    denied = require_project_write(request, project)
    if denied:
        return denied
    payload = read_payload(request)
    if payload is None:
        return json_error("Некорректный JSON")
    work_type = payload.get("work_type")
    material_id = payload.get("material_id")
    if work_type not in WORK_CATALOG or not material_id:
        return json_error("Нужно передать тип работ и материал")
    ensure_project_works(project)
    work = project.works.filter(work_type=work_type).first()
    material = (
        Material.objects.filter(id=material_id)
        .filter(Q(enterprise=request.enterprise) | Q(enterprise__isnull=True))
        .first()
    )
    if not work or not material:
        return json_error("Материал или этап не найден", status=404, code="not_found")
    work.material = material
    work.save(update_fields=["material"])
    summary = recalculate_project(project, user=request.user)
    payload = project_payload(project, request.user)
    payload["summary"] = {key: decimal_value(value) for key, value in summary.items()}
    return JsonResponse(payload)


@api_endpoint(["GET", "POST"])
def project_goals(request, project_id):
    project = project_queryset(request).filter(id=project_id).first()
    if not project:
        return json_error("Проект не найден", status=404, code="not_found")

    if request.method == "GET":
        return JsonResponse({"goals": [serialize_goal(item) for item in project.goals.select_related("assignee").all()]})

    denied = require_project_write(request, project)
    if denied:
        return denied
    payload = read_payload(request)
    if payload is None:
        return json_error("Некорректный JSON")
    title = (payload.get("title") or "").strip()
    if not title:
        return json_error("Укажите название цели")
    assignee = None
    if payload.get("assignee_id"):
        assignee = User.objects.filter(id=payload["assignee_id"]).filter(
            Q(project_participations__project=project, project_participations__is_active=True) | Q(id=project.owner_id)
        ).first()
    parent = None
    if payload.get("parent_id"):
        parent = project.goals.filter(id=payload["parent_id"]).first()
        if not parent:
            return json_error("Родительская цель не найдена", status=404, code="not_found")
    goal = ProjectGoal.objects.create(
        project=project,
        parent=parent,
        title=title,
        description=(payload.get("description") or "").strip(),
        assignee=assignee,
        created_by=request.user,
        due_date=parse_date(payload.get("due_date", "")) if payload.get("due_date") else None,
        status=payload.get("status", ProjectGoal.TODO),
        priority=payload.get("priority", ProjectGoal.NORMAL),
        sequence=int(request_value(payload, "sequence", 10)),
    )
    return JsonResponse({"goal": serialize_goal(goal), "project": project_payload(project, request.user)}, status=201)


@api_endpoint(["PATCH"])
def project_goal_detail(request, project_id, goal_id):
    project = project_queryset(request).filter(id=project_id).first()
    if not project:
        return json_error("Проект не найден", status=404, code="not_found")
    goal = project.goals.filter(id=goal_id).first()
    if not goal:
        return json_error("Цель не найдена", status=404, code="not_found")
    if goal.assignee_id != request.user.id:
        denied = require_project_write(request, project)
        if denied:
            return denied
    payload = read_payload(request)
    if payload is None:
        return json_error("Некорректный JSON")
    for field in ("title", "description", "status", "priority", "sequence"):
        if field in payload:
            setattr(goal, field, payload[field])
    if "due_date" in payload:
        goal.due_date = parse_date(payload.get("due_date", "")) if payload.get("due_date") else None
    if "parent_id" in payload and can_write_project(request.user, project):
        if payload["parent_id"]:
            if int(payload["parent_id"]) == goal.id:
                return json_error("Цель не может быть своим подпунктом")
            parent = project.goals.filter(id=payload["parent_id"]).first()
            if not parent:
                return json_error("Родительская цель не найдена", status=404, code="not_found")
            goal.parent = parent
        else:
            goal.parent = None
    if "assignee_id" in payload and can_write_project(request.user, project):
        goal.assignee = User.objects.filter(id=payload["assignee_id"]).first() if payload["assignee_id"] else None
    goal.save()
    return JsonResponse({"goal": serialize_goal(goal), "project": project_payload(project, request.user)})


def assignment_enterprise_for_user(user, project, role, payload):
    requested_enterprise_id = payload.get("assigned_enterprise_id")
    if requested_enterprise_id:
        membership = user.memberships.filter(
            enterprise_id=requested_enterprise_id,
            is_active=True,
            enterprise__is_active=True,
        ).select_related("enterprise").first()
        if not membership:
            return None, "Пользователь не состоит в выбранной компании"
        enterprise = membership.enterprise
    else:
        participant = project.participants.filter(user=user, is_active=True).select_related("enterprise").first()
        if participant and participant.enterprise:
            enterprise = participant.enterprise
        elif role in WORKING_PROJECT_ROLES:
            membership = user.memberships.filter(
                is_active=True,
                enterprise__is_active=True,
                enterprise__kind=Enterprise.COMPANY,
            ).select_related("enterprise").first()
            enterprise = membership.enterprise if membership else None
        else:
            membership = user.memberships.filter(
                enterprise=project.enterprise,
                is_active=True,
            ).select_related("enterprise").first()
            if not membership:
                membership = user.memberships.filter(is_active=True, enterprise__is_active=True).select_related("enterprise").first()
            enterprise = membership.enterprise if membership else None

    if role in WORKING_PROJECT_ROLES and (not enterprise or enterprise.kind != Enterprise.COMPANY):
        return None, "Для рабочей роли назначаемый пользователь должен состоять в компании"
    return enterprise, ""


@api_endpoint(["GET", "POST"])
def project_seats(request, project_id):
    project = project_queryset(request).filter(id=project_id).first()
    if not project:
        return json_error("Проект не найден", status=404, code="not_found")

    if request.method == "GET":
        return JsonResponse(
            {"seats": [serialize_seat(item) for item in project.seats.select_related("assigned_user", "assigned_enterprise").all()]}
        )

    denied = require_project_write(request, project)
    if denied:
        return denied
    payload = read_payload(request)
    if payload is None:
        return json_error("Некорректный JSON")
    title = (payload.get("title") or "").strip()
    if not title:
        return json_error("Укажите название места в команде")
    planned_role = payload.get("planned_role", ProjectParticipant.VIEWER)
    if planned_role not in dict(ProjectParticipant.ROLE_CHOICES):
        return json_error("Неизвестная роль")
    seat = ProjectSeat.objects.create(
        project=project,
        title=title,
        planned_role=planned_role,
        contact_name=(payload.get("contact_name") or "").strip(),
        contact_email=(payload.get("contact_email") or "").strip().lower(),
        contact_phone=(payload.get("contact_phone") or "").strip(),
        note=(payload.get("note") or "").strip(),
        created_by=request.user,
    )
    return JsonResponse({"seat": serialize_seat(seat), "project": project_payload(project, request.user)}, status=201)


@api_endpoint(["PATCH"])
def project_seat_detail(request, project_id, seat_id):
    project = project_queryset(request).filter(id=project_id).first()
    if not project:
        return json_error("Проект не найден", status=404, code="not_found")
    denied = require_project_write(request, project)
    if denied:
        return denied
    seat = project.seats.select_related("assigned_user", "assigned_enterprise").filter(id=seat_id).first()
    if not seat:
        return json_error("Место в команде не найдено", status=404, code="not_found")
    payload = read_payload(request)
    if payload is None:
        return json_error("Некорректный JSON")

    for field in ("title", "contact_name", "contact_email", "contact_phone", "note"):
        if field in payload:
            value = (payload.get(field) or "").strip()
            if field == "contact_email":
                value = value.lower()
            setattr(seat, field, value)
    if "planned_role" in payload:
        if payload["planned_role"] not in dict(ProjectParticipant.ROLE_CHOICES):
            return json_error("Неизвестная роль")
        seat.planned_role = payload["planned_role"]
    if "status" in payload:
        if payload["status"] not in dict(ProjectSeat.STATUS_CHOICES):
            return json_error("Неизвестный статус места")
        seat.status = payload["status"]
        if seat.status != ProjectSeat.ASSIGNED:
            seat.assigned_user = None
            seat.assigned_enterprise = None

    assigned_user = None
    if payload.get("assigned_user_id"):
        assigned_user = User.objects.filter(id=payload["assigned_user_id"], is_active=True).first()
    elif "assigned_user_email" in payload:
        email = (payload.get("assigned_user_email") or "").strip().lower()
        if email:
            assigned_user = User.objects.filter(email__iexact=email, is_active=True).first()
        elif payload.get("status") == ProjectSeat.OPEN:
            seat.assigned_user = None
            seat.assigned_enterprise = None
            seat.status = ProjectSeat.OPEN

    if (payload.get("assigned_user_id") or payload.get("assigned_user_email")) and not assigned_user:
        seat.save()
        return json_error("Пользователь с таким email не найден. Место сохранено как ожидающее.", status=404, code="not_found")

    if assigned_user:
        enterprise, assignment_error = assignment_enterprise_for_user(assigned_user, project, seat.planned_role, payload)
        if assignment_error:
            seat.save()
            return json_error(assignment_error)
        ProjectParticipant.objects.update_or_create(
            project=project,
            user=assigned_user,
            defaults={
                "enterprise": enterprise,
                "role": seat.planned_role,
                "is_active": True,
            },
        )
        seat.assigned_user = assigned_user
        seat.assigned_enterprise = enterprise
        seat.status = ProjectSeat.ASSIGNED
        if not seat.contact_name:
            seat.contact_name = display_user(assigned_user)
        if not seat.contact_email:
            seat.contact_email = assigned_user.email

    seat.save()
    return JsonResponse({"seat": serialize_seat(seat), "project": project_payload(project, request.user)})


@api_endpoint(["GET", "POST"])
def project_join_requests(request, project_id):
    project = Project.objects.filter(id=project_id).select_related("enterprise", "owner").first()
    if not project:
        return json_error("Проект не найден", status=404, code="not_found")

    if request.method == "GET":
        if not (can_manage_project(request.user, project) or project.participants.filter(user=request.user, is_active=True).exists()):
            return json_error("Нет доступа к заявкам проекта", status=403, code="forbidden")
        queryset = project.join_requests.select_related("project", "applicant", "applicant_enterprise")
        return JsonResponse({"join_requests": [serialize_join_request(item) for item in queryset]})

    payload = read_payload(request)
    if payload is None:
        return json_error("Некорректный JSON")
    requested_role = payload.get("requested_role", ProjectParticipant.VIEWER)
    if requested_role not in dict(ProjectParticipant.ROLE_CHOICES):
        return json_error("Неизвестная роль в проекте")
    if requested_role in {ProjectParticipant.FOREMAN, ProjectParticipant.BUILDER, ProjectParticipant.ESTIMATOR}:
        if request.enterprise.kind != Enterprise.COMPANY:
            return json_error("Для рабочей роли выберите компанию, в которой вы состоите")
    join_request = ProjectJoinRequest.objects.create(
        project=project,
        applicant=request.user,
        applicant_enterprise=request.enterprise,
        requested_role=requested_role,
        message=(payload.get("message") or "").strip(),
    )
    return JsonResponse({"join_request": serialize_join_request(join_request)}, status=201)


@api_endpoint(["PATCH"])
def project_join_request_detail(request, project_id, request_id):
    project = project_queryset(request).filter(id=project_id).first()
    if not project:
        return json_error("Проект не найден", status=404, code="not_found")
    denied = require_project_manager(request, project)
    if denied:
        return denied
    join_request = project.join_requests.select_related("applicant", "applicant_enterprise", "project").filter(id=request_id).first()
    if not join_request:
        return json_error("Заявка не найдена", status=404, code="not_found")
    payload = read_payload(request)
    if payload is None:
        return json_error("Некорректный JSON")
    status = payload.get("status")
    if status not in {ProjectJoinRequest.APPROVED, ProjectJoinRequest.REJECTED}:
        return json_error("Передайте решение: approved или rejected")
    role = payload.get("role") or join_request.requested_role
    if role not in dict(ProjectParticipant.ROLE_CHOICES):
        return json_error("Неизвестная роль")
    join_request.status = status
    join_request.decided_by = request.user
    join_request.decision_comment = (payload.get("decision_comment") or "").strip()
    join_request.save()
    if status == ProjectJoinRequest.APPROVED:
        ProjectParticipant.objects.update_or_create(
            project=project,
            user=join_request.applicant,
            defaults={
                "enterprise": join_request.applicant_enterprise,
                "role": role,
                "is_active": True,
            },
        )
    return JsonResponse({"join_request": serialize_join_request(join_request), "project": project_payload(project, request.user)})


@api_endpoint(["PATCH"])
def procurement_detail(request, procurement_id):
    projects = project_queryset(request)
    item = ProcurementPlan.objects.select_related("project", "material", "supplier").filter(
        id=procurement_id,
        project__in=projects,
    ).first()
    if not item:
        return json_error("Позиция закупки не найдена", status=404, code="not_found")
    denied = require_project_write(request, item.project)
    if denied:
        return denied
    payload = read_payload(request)
    if payload is None:
        return json_error("Некорректный JSON")
    status = payload.get("status")
    if status not in dict(ProcurementPlan.STATUS_CHOICES):
        return json_error("Неизвестный статус закупки")
    item.status = status
    item.save(update_fields=["status"])
    return JsonResponse({"procurement": serialize_procurement(item), "project": project_payload(item.project, request.user)})
