from datetime import timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from core.calculations import WORK_CATALOG, default_material, ensure_project_works, recalculate_project
from core.models import (
    Enterprise,
    LaborNorm,
    Material,
    MaterialCategory,
    Membership,
    Project,
    ProjectGoal,
    ProjectJoinRequest,
    ProjectParticipant,
    ProjectSeat,
    Supplier,
    SupplierApplication,
    SupplierProfile,
)


PASSWORD = "SmartBuild2026!"


class Command(BaseCommand):
    help = "Seeds SmartBuild with enterprises, references, projects, schedules and procurement data."

    def add_arguments(self, parser):
        parser.add_argument("--noinput", action="store_true")

    def handle(self, *args, **options):
        enterprises = self.seed_enterprises()
        users = self.seed_users(enterprises)
        categories = self.seed_categories()
        suppliers = self.seed_suppliers(enterprises)
        self.seed_supplier_profiles(users, suppliers)
        self.seed_materials(categories, suppliers, enterprises)
        self.seed_labor_norms()
        self.seed_projects(enterprises, users)
        self.seed_supplier_applications()
        self.stdout.write(self.style.SUCCESS("SmartBuild demo data is ready."))

    def seed_enterprises(self):
        data = [
            {
                "name": "СеверСтрой Групп",
                "kind": Enterprise.COMPANY,
                "inn": "7701452301",
                "contact_email": "office@severstroy.local",
                "phone": "+7 495 100-20-30",
                "address": "Москва, ул. Строителей, 18",
            },
            {
                "name": "Городские Пространства",
                "kind": Enterprise.COMPANY,
                "inn": "7812459077",
                "contact_email": "projects@urban-spaces.local",
                "phone": "+7 812 700-14-22",
                "address": "Санкт-Петербург, Лиговский пр., 91",
            },
            {
                "name": "ДомПроект Юг",
                "kind": Enterprise.COMPANY,
                "inn": "2311124590",
                "contact_email": "hello@domproekt.local",
                "phone": "+7 861 250-77-11",
                "address": "Краснодар, ул. Российская, 41",
            },
            {
                "name": "Личное пространство: Михаил Соколов",
                "kind": Enterprise.PERSONAL,
                "inn": "",
                "contact_email": "client@personal.local",
                "phone": "+7 900 700-10-10",
                "address": "Московская область",
            },
            {
                "name": "Поставщик: Монолит Ресурс",
                "kind": Enterprise.SUPPLIER,
                "inn": "7722450012",
                "contact_email": "supplier@monolit-resource.local",
                "phone": "+7 495 600-10-01",
                "address": "Москва, промышленная зона Восток",
            },
            {
                "name": "Поставщик: Финиш Профи",
                "kind": Enterprise.SUPPLIER,
                "inn": "7802455510",
                "contact_email": "supplier@finish-pro.local",
                "phone": "+7 812 455-77-22",
                "address": "Санкт-Петербург, складской комплекс Парнас",
            },
        ]
        enterprises = {}
        for item in data:
            enterprise, _created = Enterprise.objects.update_or_create(
                name=item["name"],
                defaults=item,
            )
            enterprises[item["name"]] = enterprise
        return enterprises

    def seed_users(self, enterprises):
        users_data = [
            ("admin@smartbuild.local", "Админ", "Системы", True, True),
            ("owner@severstroy.local", "Анна", "Корнилова", False, False),
            ("foreman@severstroy.local", "Илья", "Захаров", False, False),
            ("builder@severstroy.local", "Олег", "Минаев", False, False),
            ("client@personal.local", "Михаил", "Соколов", False, False),
            ("estimator@urban-spaces.local", "Мария", "Романова", False, False),
            ("foreman@domproekt.local", "Сергей", "Белов", False, False),
            ("supplier@monolit-resource.local", "Павел", "Грачёв", False, False),
            ("supplier@finish-pro.local", "Елена", "Кравцова", False, False),
        ]
        users = {}
        for username, first_name, last_name, is_staff, is_superuser in users_data:
            user, _created = User.objects.get_or_create(
                username=username,
                defaults={"email": username, "first_name": first_name, "last_name": last_name},
            )
            user.email = username
            user.first_name = first_name
            user.last_name = last_name
            user.is_staff = is_staff
            user.is_superuser = is_superuser
            user.set_password(PASSWORD)
            user.save()
            users[username] = user

        memberships = [
            ("admin@smartbuild.local", "СеверСтрой Групп", Membership.OWNER),
            ("admin@smartbuild.local", "Городские Пространства", Membership.OWNER),
            ("admin@smartbuild.local", "ДомПроект Юг", Membership.OWNER),
            ("owner@severstroy.local", "СеверСтрой Групп", Membership.OWNER),
            ("foreman@severstroy.local", "СеверСтрой Групп", Membership.FOREMAN),
            ("builder@severstroy.local", "СеверСтрой Групп", Membership.VIEWER),
            ("client@personal.local", "Личное пространство: Михаил Соколов", Membership.OWNER),
            ("estimator@urban-spaces.local", "Городские Пространства", Membership.ESTIMATOR),
            ("foreman@domproekt.local", "ДомПроект Юг", Membership.FOREMAN),
            ("supplier@monolit-resource.local", "Поставщик: Монолит Ресурс", Membership.OWNER),
            ("supplier@finish-pro.local", "Поставщик: Финиш Профи", Membership.OWNER),
        ]
        for username, enterprise_name, role in memberships:
            Membership.objects.update_or_create(
                user=users[username],
                enterprise=enterprises[enterprise_name],
                defaults={"role": role, "is_active": True},
            )
        return users

    def seed_categories(self):
        data = {
            "Бетон и смеси": "Материалы для фундаментов, стяжек и монолитных работ",
            "Стеновые материалы": "Блоки, кирпич и панели для несущих и ограждающих конструкций",
            "Кровля": "Финишные кровельные покрытия и комплектующие",
            "Фасад": "Материалы внешней отделки",
            "Отделка": "Материалы внутренних работ",
            "Инженерные системы": "Комплекты для электрики, водоснабжения и отопления",
        }
        categories = {}
        for name, description in data.items():
            category, _created = MaterialCategory.objects.update_or_create(
                name=name,
                defaults={"description": description},
            )
            categories[name] = category
        return categories

    def seed_suppliers(self, enterprises):
        supplier_renames = {
            "БетонПоставка Центр": "Монолит Ресурс",
            "КирпичБлок Трейд": "Камень и Блок",
            "Кровля Маркет": "RoofLine Партнёр",
            "ОтделМатериалы": "Финиш Профи",
            "ИнженерКомплект": "Контур Инженерия",
            "СеверСтрой Склад": "Северный Склад",
            "Urban Supply": "Urban Materials",
            "ЮгСтройКомплект": "Южный Дом Снаб",
        }
        for old_name, new_name in supplier_renames.items():
            for supplier in Supplier.objects.filter(name=old_name):
                duplicate = Supplier.objects.filter(
                    enterprise=supplier.enterprise,
                    name=new_name,
                ).exclude(id=supplier.id).first()
                if duplicate:
                    supplier.materials.update(supplier=duplicate)
                    supplier.is_active = False
                    supplier.save(update_fields=["is_active"])
                else:
                    supplier.name = new_name
                    supplier.save(update_fields=["name"])

        global_suppliers = [
            ("Монолит Ресурс", 4, 97, "supply@monolit-resource.local", "+7 495 600-10-01"),
            ("Камень и Блок", 6, 94, "sales@stone-block.local", "+7 495 600-10-02"),
            ("RoofLine Партнёр", 5, 96, "order@roofline.local", "+7 495 600-10-03"),
            ("Финиш Профи", 3, 93, "team@finish-pro.local", "+7 495 600-10-04"),
            ("Контур Инженерия", 7, 95, "box@contour-engineering.local", "+7 495 600-10-05"),
        ]
        suppliers = {}
        for name, lead, reliability, email, phone in global_suppliers:
            supplier, _created = Supplier.objects.update_or_create(
                enterprise=None,
                name=name,
                defaults={
                    "lead_time_days": lead,
                    "reliability_percent": reliability,
                    "email": email,
                    "phone": phone,
                    "address": "Федеральный распределительный склад",
                },
            )
            suppliers[name] = supplier

        local_suppliers = [
            ("Северный Склад", "СеверСтрой Групп", 2, 98, "order@north-yard.local"),
            ("Urban Materials", "Городские Пространства", 4, 95, "order@urban-materials.local"),
            ("Южный Дом Снаб", "ДомПроект Юг", 3, 96, "order@south-home-supply.local"),
        ]
        for name, enterprise_name, lead, reliability, email in local_suppliers:
            supplier, _created = Supplier.objects.update_or_create(
                enterprise=enterprises[enterprise_name],
                name=name,
                defaults={
                    "lead_time_days": lead,
                    "reliability_percent": reliability,
                    "email": email,
                    "phone": "+7 900 000-00-00",
                    "address": enterprises[enterprise_name].address,
                },
            )
            suppliers[name] = supplier
        for old_name, new_name in supplier_renames.items():
            if new_name in suppliers:
                suppliers[old_name] = suppliers[new_name]
        return suppliers

    def seed_supplier_profiles(self, users, suppliers):
        profile_data = [
            ("supplier@monolit-resource.local", "Монолит Ресурс"),
            ("supplier@finish-pro.local", "Финиш Профи"),
        ]
        for username, supplier_name in profile_data:
            SupplierProfile.objects.update_or_create(
                user=users[username],
                defaults={"supplier": suppliers[supplier_name], "can_manage_catalog": True},
            )

    def seed_materials(self, categories, suppliers, enterprises):
        data = [
            ("Бетон B20 М250", "Бетон и смеси", "БетонПоставка Центр", "m3", 6100, 0.035, 4, "foundation_concrete", {"quantity_per_scope": 1, "installation_factor": 1.00}),
            ("Бетон B25 М350", "Бетон и смеси", "БетонПоставка Центр", "m3", 6900, 0.030, 4, "foundation_concrete", {"quantity_per_scope": 1, "installation_factor": 0.96}),
            ("Бетон B30 для нагруженных оснований", "Бетон и смеси", "БетонПоставка Центр", "m3", 7900, 0.030, 5, "foundation_concrete", {"quantity_per_scope": 1, "installation_factor": 1.02}),
            ("Фибробетон B25", "Бетон и смеси", "СеверСтрой Склад", "m3", 7600, 0.025, 2, "foundation_concrete", {"quantity_per_scope": 1, "installation_factor": 0.92}),
            ("Газобетон D500 600x300x200", "Стеновые материалы", "КирпичБлок Трейд", "pcs", 195, 0.070, 6, "wall_blocks", {"coverage_m2_per_unit": 0.18, "installation_factor": 0.88, "discrete": True}),
            ("Керамоблок 380 мм", "Стеновые материалы", "КирпичБлок Трейд", "pcs", 255, 0.060, 7, "wall_blocks", {"coverage_m2_per_unit": 0.15, "installation_factor": 1.00, "discrete": True}),
            ("Кирпич полнотелый М150", "Стеновые материалы", "КирпичБлок Трейд", "pcs", 34, 0.090, 6, "wall_blocks", {"coverage_m2_per_unit": 0.016, "installation_factor": 1.35, "discrete": True}),
            ("Силикатный блок 250 мм", "Стеновые материалы", "Urban Supply", "pcs", 142, 0.065, 4, "wall_blocks", {"coverage_m2_per_unit": 0.125, "installation_factor": 0.94, "discrete": True}),
            ("SIP-панель стеновая", "Стеновые материалы", "КирпичБлок Трейд", "m2", 2850, 0.045, 8, "wall_blocks", {"quantity_per_scope": 1, "installation_factor": 0.62}),
            ("Металлочерепица 0.5 мм", "Кровля", "Кровля Маркет", "m2", 820, 0.080, 5, "roofing", {"quantity_per_scope": 1, "installation_factor": 0.95}),
            ("Профнастил С21", "Кровля", "Кровля Маркет", "m2", 690, 0.070, 4, "roofing", {"quantity_per_scope": 1, "installation_factor": 0.88}),
            ("Гибкая черепица", "Кровля", "Кровля Маркет", "m2", 1120, 0.090, 6, "roofing", {"quantity_per_scope": 1, "installation_factor": 1.08}),
            ("Фальцевая кровля", "Кровля", "Кровля Маркет", "m2", 1480, 0.075, 7, "roofing", {"quantity_per_scope": 1, "installation_factor": 1.18}),
            ("ПВХ-мембрана кровельная", "Кровля", "Urban Supply", "m2", 980, 0.060, 4, "roofing", {"quantity_per_scope": 1, "installation_factor": 0.90}),
            ("Фасадная штукатурка 25 кг", "Фасад", "ОтделМатериалы", "bag", 620, 0.100, 3, "facade_finish", {"coverage_m2_per_unit": 4.5, "installation_factor": 1.00, "discrete": True}),
            ("Клинкерная плитка", "Фасад", "ОтделМатериалы", "m2", 1650, 0.120, 6, "facade_finish", {"quantity_per_scope": 1, "installation_factor": 1.28}),
            ("Виниловый сайдинг", "Фасад", "ОтделМатериалы", "m2", 890, 0.090, 4, "facade_finish", {"quantity_per_scope": 1, "installation_factor": 0.78}),
            ("Фиброцементные панели", "Фасад", "Urban Supply", "m2", 1420, 0.080, 5, "facade_finish", {"quantity_per_scope": 1, "installation_factor": 0.92}),
            ("Фасадная краска 10 л", "Фасад", "ОтделМатериалы", "bag", 2100, 0.070, 2, "facade_finish", {"coverage_m2_per_unit": 55, "installation_factor": 0.70, "discrete": True}),
            ("Гипсовая штукатурка 30 кг", "Отделка", "ОтделМатериалы", "bag", 480, 0.100, 3, "interior_finish", {"coverage_m2_per_unit": 3.2, "installation_factor": 1.00, "discrete": True}),
            ("Гипсокартон 12.5 мм", "Отделка", "ОтделМатериалы", "pcs", 420, 0.080, 3, "interior_finish", {"coverage_m2_per_unit": 3.0, "installation_factor": 0.82, "discrete": True}),
            ("Краска интерьерная 10 л", "Отделка", "ОтделМатериалы", "bag", 1650, 0.060, 2, "interior_finish", {"coverage_m2_per_unit": 75, "installation_factor": 0.68, "discrete": True}),
            ("Ламинат 33 класс", "Отделка", "Urban Supply", "m2", 1240, 0.070, 4, "interior_finish", {"quantity_per_scope": 1, "installation_factor": 0.74}),
            ("Керамогранит 60x60", "Отделка", "ОтделМатериалы", "m2", 1850, 0.090, 5, "interior_finish", {"quantity_per_scope": 1, "installation_factor": 1.16}),
            ("Комплект инженерии Базовый", "Инженерные системы", "ИнженерКомплект", "set", 92000, 0.020, 7, "engineering_set", {"quantity_per_scope": 1, "installation_factor": 1.00, "discrete": True}),
            ("Комплект инженерии Комфорт", "Инженерные системы", "ИнженерКомплект", "set", 132000, 0.020, 8, "engineering_set", {"quantity_per_scope": 1, "installation_factor": 0.96, "discrete": True}),
            ("Комплект инженерии Коммерческий", "Инженерные системы", "Urban Supply", "set", 178000, 0.030, 9, "engineering_set", {"quantity_per_scope": 1, "installation_factor": 1.18, "discrete": True}),
            ("Арматура А500С 12 мм", "Бетон и смеси", "БетонПоставка Центр", "kg", 82, 0.040, 4, "foundation_concrete", {"quantity_per_scope": 38, "installation_factor": 1.08}),
            ("Гидроизоляция рулонная", "Бетон и смеси", "БетонПоставка Центр", "roll", 2450, 0.080, 3, "foundation_concrete", {"coverage_m2_per_unit": 10, "installation_factor": 0.72, "discrete": True}),
            ("Кирпич облицовочный графит", "Стеновые материалы", "КирпичБлок Трейд", "pcs", 58, 0.080, 7, "wall_blocks", {"coverage_m2_per_unit": 0.018, "installation_factor": 1.22, "discrete": True}),
            ("Минеральная вата фасадная", "Фасад", "ОтделМатериалы", "m2", 510, 0.070, 4, "facade_finish", {"quantity_per_scope": 1, "installation_factor": 0.92}),
            ("Декоративная рейка интерьерная", "Отделка", "ОтделМатериалы", "m2", 2180, 0.100, 6, "interior_finish", {"quantity_per_scope": 1, "installation_factor": 1.18}),
            ("Тёплый пол водяной комплект", "Инженерные системы", "ИнженерКомплект", "set", 64000, 0.020, 6, "engineering_set", {"quantity_per_scope": 1, "installation_factor": 0.94, "discrete": True}),
        ]

        for name, category, supplier, unit, price, waste, delivery, group, props in data:
            Material.objects.update_or_create(
                enterprise=None,
                name=name,
                alternative_group=group,
                defaults={
                    "category": categories[category],
                    "supplier": suppliers[supplier],
                    "unit": unit,
                    "price": price,
                    "waste_factor": waste,
                    "delivery_days": delivery,
                    "stock_level": 250,
                    "properties": props,
                    "is_active": True,
                },
            )

        local_data = [
            ("Газобетон D400 локальный", "Стеновые материалы", "СеверСтрой Склад", "СеверСтрой Групп", "pcs", 182, 0.055, 2, "wall_blocks", {"coverage_m2_per_unit": 0.18, "installation_factor": 0.84, "discrete": True}),
            ("Металлочерепица локальная", "Кровля", "ЮгСтройКомплект", "ДомПроект Юг", "m2", 760, 0.075, 3, "roofing", {"quantity_per_scope": 1, "installation_factor": 0.92}),
            ("Комплект инженерии для офиса", "Инженерные системы", "Urban Supply", "Городские Пространства", "set", 158000, 0.025, 4, "engineering_set", {"quantity_per_scope": 1, "installation_factor": 1.04, "discrete": True}),
        ]
        for name, category, supplier, enterprise, unit, price, waste, delivery, group, props in local_data:
            Material.objects.update_or_create(
                enterprise=enterprises[enterprise],
                name=name,
                alternative_group=group,
                defaults={
                    "category": categories[category],
                    "supplier": suppliers[supplier],
                    "unit": unit,
                    "price": price,
                    "waste_factor": waste,
                    "delivery_days": delivery,
                    "stock_level": 180,
                    "properties": props,
                    "is_active": True,
                },
            )

    def seed_labor_norms(self):
        data = [
            (LaborNorm.WORK_FOUNDATION, "Монолитная плита", "m3", 2.8, 4.2, 7, 5, 920),
            (LaborNorm.WORK_WALLS, "Кладка и монтаж стен", "m2", 8.5, 1.35, 1, 6, 840),
            (LaborNorm.WORK_ROOF, "Монтаж кровельного покрытия", "m2", 12.0, 0.92, 0, 5, 870),
            (LaborNorm.WORK_FACADE, "Внешняя отделка фасада", "m2", 9.5, 1.08, 2, 5, 820),
            (LaborNorm.WORK_INTERIOR, "Внутренняя отделка", "m2", 13.5, 0.76, 2, 7, 790),
            (LaborNorm.WORK_ENGINEERING, "Монтаж инженерных систем", "set", 0.24, 58.0, 1, 4, 980),
        ]
        for work_type, name, unit, productivity, hours, break_days, crew, rate in data:
            LaborNorm.objects.update_or_create(
                enterprise=None,
                work_type=work_type,
                name=name,
                defaults={
                    "unit": unit,
                    "productivity_per_worker_day": productivity,
                    "base_labor_hours": hours,
                    "tech_break_days": break_days,
                    "recommended_crew_size": crew,
                    "labor_rate": rate,
                    "description": "Норматив используется для расчёта длительности, трудозатрат и стоимости работ.",
                },
            )

    def seed_projects(self, enterprises, users):
        today = timezone.localdate()
        project_data = [
            ("СеверСтрой Групп", "Коттедж Сосновый", Project.HOUSE, "Московская область, КП Сосновый", 14, 10, 3.1, 2, None, today + timedelta(days=10), 8, 8),
            ("СеверСтрой Групп", "Таунхаус Линия 4", Project.HOUSE, "Новая Москва, квартал 4", 18, 8, 3.0, 2, None, today + timedelta(days=22), 10, 7),
            ("СеверСтрой Групп", "Реконструкция офиса", Project.OFFICE, "Москва, Варшавское ш., 12", 24, 16, 3.4, 1, 384, today + timedelta(days=5), 9, 6),
            ("Городские Пространства", "Офисный блок Невский", Project.OFFICE, "Санкт-Петербург, Невский пр., 108", 30, 18, 3.6, 2, 1080, today + timedelta(days=15), 12, 9),
            ("Городские Пространства", "Кафе на первом этаже", Project.RETAIL, "Санкт-Петербург, ул. Рубинштейна, 7", 18, 12, 3.2, 1, 216, today + timedelta(days=8), 7, 6),
            ("Городские Пространства", "Апартаменты Лофт", Project.APARTMENT, "Санкт-Петербург, наб. Обводного канала, 62", 16, 10, 3.0, 1, 160, today + timedelta(days=30), 6, 5),
            ("ДомПроект Юг", "Дом у реки", Project.HOUSE, "Краснодарский край, пос. Южный", 12, 9, 3.0, 1, None, today + timedelta(days=12), 7, 7),
            ("ДомПроект Юг", "Магазин фермерских продуктов", Project.RETAIL, "Краснодар, ул. Восточная, 19", 22, 14, 3.4, 1, 308, today + timedelta(days=18), 8, 6),
            ("ДомПроект Юг", "Гостевой дом", Project.AUXILIARY, "Анапа, ул. Морская, 5", 10, 8, 2.8, 2, None, today + timedelta(days=26), 6, 8),
            ("Личное пространство: Михаил Соколов", "Личный дом Михаила", Project.HOUSE, "Истра, участок 42", 11, 9, 3.0, 1, None, today + timedelta(days=16), 5, 9),
        ]

        owner_by_enterprise = {
            "СеверСтрой Групп": users["owner@severstroy.local"],
            "Городские Пространства": users["estimator@urban-spaces.local"],
            "ДомПроект Юг": users["foreman@domproekt.local"],
            "Личное пространство: Михаил Соколов": users["client@personal.local"],
        }

        for row in project_data:
            (
                enterprise_name,
                name,
                object_type,
                address,
                length,
                width,
                height,
                floors,
                area,
                start_date,
                workers,
                contingency,
            ) = row
            enterprise = enterprises[enterprise_name]
            project, _created = Project.objects.update_or_create(
                enterprise=enterprise,
                name=name,
                defaults={
                    "owner": owner_by_enterprise[enterprise_name],
                    "object_type": object_type,
                    "address": address,
                    "length": length,
                    "width": width,
                    "height": height,
                    "floors": floors,
                    "area": area,
                    "start_date": start_date,
                    "workers": workers,
                    "contingency_percent": contingency,
                    "status": Project.DRAFT,
                },
            )
            ensure_project_works(project)
            self.assign_material_mix(project)
            recalculate_project(project, user=owner_by_enterprise[enterprise_name])
            self.seed_project_people(project, enterprise, users)
            self.seed_project_goals(project, users)

    def assign_material_mix(self, project):
        preferences = {
            "Коттедж Сосновый": {
                LaborNorm.WORK_WALLS: "Газобетон D400 локальный",
                LaborNorm.WORK_ROOF: "Металлочерепица 0.5 мм",
                LaborNorm.WORK_INTERIOR: "Гипсокартон 12.5 мм",
            },
            "Офисный блок Невский": {
                LaborNorm.WORK_WALLS: "SIP-панель стеновая",
                LaborNorm.WORK_ROOF: "ПВХ-мембрана кровельная",
                LaborNorm.WORK_ENGINEERING: "Комплект инженерии для офиса",
            },
            "Дом у реки": {
                LaborNorm.WORK_WALLS: "Керамоблок 380 мм",
                LaborNorm.WORK_ROOF: "Металлочерепица локальная",
                LaborNorm.WORK_FACADE: "Фиброцементные панели",
            },
        }
        project_preferences = preferences.get(project.name, {})
        for work_type, meta in WORK_CATALOG.items():
            work = project.works.filter(work_type=work_type).first()
            if not work:
                continue
            preferred_name = project_preferences.get(work_type)
            if preferred_name:
                material = Material.objects.filter(name=preferred_name).first()
            else:
                material = default_material(project.enterprise, meta["material_group"])
            if material:
                work.material = material
                work.sequence = meta["sequence"]
                work.save(update_fields=["material", "sequence"])

    def seed_project_people(self, project, enterprise, users):
        owner = project.owner
        if owner:
            ProjectParticipant.objects.update_or_create(
                project=project,
                user=owner,
                defaults={"enterprise": enterprise, "role": ProjectParticipant.DEVELOPER, "is_active": True},
            )

        assignments = {
            "Коттедж Сосновый": [
                ("foreman@severstroy.local", ProjectParticipant.FOREMAN),
                ("builder@severstroy.local", ProjectParticipant.BUILDER),
                ("client@personal.local", ProjectParticipant.DEVELOPER),
            ],
            "Реконструкция офиса": [
                ("foreman@severstroy.local", ProjectParticipant.FOREMAN),
                ("estimator@urban-spaces.local", ProjectParticipant.ESTIMATOR),
            ],
            "Личный дом Михаила": [
                ("foreman@severstroy.local", ProjectParticipant.FOREMAN),
                ("builder@severstroy.local", ProjectParticipant.BUILDER),
            ],
            "Офисный блок Невский": [
                ("foreman@severstroy.local", ProjectParticipant.FOREMAN),
                ("builder@severstroy.local", ProjectParticipant.BUILDER),
            ],
        }
        for username, role in assignments.get(project.name, []):
            participant_enterprise = users[username].memberships.filter(
                enterprise__kind=Enterprise.COMPANY,
                is_active=True,
            ).select_related("enterprise").first()
            if username == "client@personal.local":
                participant_enterprise = users[username].memberships.filter(is_active=True).select_related("enterprise").first()
            ProjectParticipant.objects.update_or_create(
                project=project,
                user=users[username],
                defaults={
                    "enterprise": participant_enterprise.enterprise if participant_enterprise else enterprise,
                    "role": role,
                    "is_active": True,
                },
            )

        seat_templates = {
            "Коттедж Сосновый": [
                ("Ответственный за фундамент", ProjectParticipant.FOREMAN, "foreman@severstroy.local", "", "", "Контроль приемки бетона и технологического перерыва."),
                ("Бригада отделки", ProjectParticipant.BUILDER, "", "Алексей Орлов", "finish-team@example.local", "Назначить после согласования стартовой даты."),
            ],
            "Реконструкция офиса": [
                ("Сметчик по инженерии", ProjectParticipant.ESTIMATOR, "estimator@urban-spaces.local", "", "", "Отдельно проверить инженерные комплекты."),
                ("Координатор поставок", ProjectParticipant.VIEWER, "", "Мария Ларионова", "logistics@example.local", "Пока не зарегистрирована, оставить как контакт."),
            ],
            "Личный дом Михаила": [
                ("Прораб по кровле", ProjectParticipant.FOREMAN, "", "Сергей Петров", "roof-foreman@example.local", "Планируется подключение перед монтажом кровли."),
                ("Исполнитель фасада", ProjectParticipant.BUILDER, "", "Бригада фасадчиков", "facade-team@example.local", "Можно назначить после регистрации бригадира."),
            ],
            "Дом у реки": [
                ("Прораб на старт работ", ProjectParticipant.FOREMAN, "", "Илья Захаров", "foreman@severstroy.local", "Ожидается заявка на участие."),
            ],
        }
        for title, role, assigned_username, contact_name, contact_email, note in seat_templates.get(project.name, []):
            assigned_user = users.get(assigned_username) if assigned_username else None
            participant = (
                project.participants.filter(user=assigned_user).select_related("enterprise").first()
                if assigned_user else None
            )
            ProjectSeat.objects.update_or_create(
                project=project,
                title=title,
                defaults={
                    "planned_role": role,
                    "contact_name": contact_name or (f"{assigned_user.first_name} {assigned_user.last_name}".strip() if assigned_user else ""),
                    "contact_email": contact_email or (assigned_user.email if assigned_user else ""),
                    "contact_phone": "",
                    "note": note,
                    "assigned_user": assigned_user,
                    "assigned_enterprise": participant.enterprise if participant else None,
                    "status": ProjectSeat.ASSIGNED if assigned_user and participant else ProjectSeat.OPEN,
                    "created_by": owner,
                },
            )

        if project.name == "Дом у реки":
            ProjectJoinRequest.objects.update_or_create(
                project=project,
                applicant=users["foreman@severstroy.local"],
                status=ProjectJoinRequest.PENDING,
                defaults={
                    "applicant_enterprise": users["foreman@severstroy.local"].memberships.filter(enterprise__kind=Enterprise.COMPANY).first().enterprise,
                    "requested_role": ProjectParticipant.FOREMAN,
                    "message": "Готов подключиться к контролю кровельных работ и сроков поставки.",
                },
            )

    def seed_project_goals(self, project, users):
        due_base = project.start_date
        goals = [
            ("Проверить исходные размеры объекта", project.owner, due_base - timedelta(days=3), ProjectGoal.HIGH),
            ("Согласовать поставщиков по ключевым материалам", project.owner, due_base - timedelta(days=1), ProjectGoal.NORMAL),
        ]
        foreman = project.participants.filter(role=ProjectParticipant.FOREMAN).select_related("user").first()
        builder = project.participants.filter(role=ProjectParticipant.BUILDER).select_related("user").first()
        if foreman:
            goals.append(("Разбить работы по бригаде на первую неделю", foreman.user, due_base + timedelta(days=2), ProjectGoal.HIGH))
        if builder:
            goals.append(("Подготовить площадку и складирование материалов", builder.user, due_base + timedelta(days=1), ProjectGoal.NORMAL))

        for index, (title, assignee, due_date, priority) in enumerate(goals, start=1):
            ProjectGoal.objects.update_or_create(
                project=project,
                title=title,
                defaults={
                    "description": "Задача добавлена для контроля сроков и ответственности внутри проекта.",
                    "assignee": assignee,
                    "created_by": project.owner,
                    "due_date": due_date,
                    "priority": priority,
                    "status": ProjectGoal.TODO,
                    "sequence": index * 10,
                },
            )

    def seed_supplier_applications(self):
        data = [
            {
                "company_name": "ТехноСнаб Регион",
                "contact_name": "Александр Лебедев",
                "email": "partner@technosnab.local",
                "phone": "+7 900 300-40-50",
                "city": "Казань",
                "materials": "Кровля, фасадные панели, утеплитель",
                "message": "Хотим подключить региональный склад и обновлять каталог материалов.",
            },
            {
                "company_name": "ЭкоДом Материалы",
                "contact_name": "Виктория Морозова",
                "email": "hello@ecodom-materials.local",
                "phone": "+7 901 500-22-11",
                "city": "Екатеринбург",
                "materials": "Отделочные материалы и инженерные комплекты",
                "message": "Готовы передавать цены и сроки поставки по API.",
            },
        ]
        for item in data:
            SupplierApplication.objects.update_or_create(
                email=item["email"],
                defaults=item,
            )
