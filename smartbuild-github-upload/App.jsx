import {
  ArrowRight,
  BadgeRussianRuble,
  BarChart3,
  Boxes,
  Building2,
  CalendarDays,
  Check,
  ChevronDown,
  ClipboardList,
  FilePlus2,
  Factory,
  HardHat,
  Home,
  Info,
  LayoutGrid,
  List,
  LogOut,
  Menu,
  PackageCheck,
  Plus,
  RefreshCw,
  Replace,
  Save,
  Search,
  Send,
  ShieldCheck,
  ShoppingCart,
  SlidersHorizontal,
  Target,
  Truck,
  UserCheck,
  UserPlus,
  UserCog,
  UserRound,
  UsersRound,
  WalletCards,
  X
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

const API_BASE = "/api";

const objectTypes = [
  ["house", "Жилой дом"],
  ["apartment", "Квартира"],
  ["office", "Офис"],
  ["retail", "Торговое помещение"],
  ["auxiliary", "Вспомогательное сооружение"]
];

const materialGroupLabels = {
  foundation_concrete: "Фундамент и бетон",
  wall_blocks: "Стеновые материалы",
  roofing: "Кровельные материалы",
  facade_finish: "Фасадная отделка",
  interior_finish: "Внутренняя отделка",
  engineering_set: "Инженерные комплекты",
  custom: "Своя группа"
};

const projectRoleLabels = {
  developer: "Застройщик",
  foreman: "Прораб",
  builder: "Исполнитель",
  estimator: "Сметчик",
  viewer: "Наблюдатель"
};

const projectImages = [
  "https://images.unsplash.com/photo-1541888946425-d81bb19240f5?auto=format&fit=crop&w=900&q=80",
  "https://images.unsplash.com/photo-1503387762-592deb58ef4e?auto=format&fit=crop&w=900&q=80",
  "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=900&q=80",
  "https://images.unsplash.com/photo-1494526585095-c41746248156?auto=format&fit=crop&w=900&q=80",
  "https://images.unsplash.com/photo-1518005020951-eccb494ad742?auto=format&fit=crop&w=900&q=80"
];

const tabs = [
  ["projects", "Проекты", Building2],
  ["account", "Кабинет", UserRound]
];

const workOrder = ["foundation", "walls", "roof", "facade", "interior", "engineering"];

const emptyProject = {
  name: "",
  object_type: "house",
  address: "",
  length: "",
  width: "",
  height: "",
  floors: "",
  area: "",
  start_date: "",
  workers: "",
  contingency_percent: ""
};

const emptyGoal = {
  title: "",
  description: "",
  assignee_id: "",
  due_date: "",
  priority: "normal"
};

const emptySeat = {
  title: "",
  planned_role: "foreman",
  contact_name: "",
  contact_email: "",
  contact_phone: "",
  note: ""
};

function todayIso() {
  return new Date().toISOString().slice(0, 10);
}

function formatMoney(value) {
  return new Intl.NumberFormat("ru-RU", {
    style: "currency",
    currency: "RUB",
    maximumFractionDigits: 0
  }).format(Number(value || 0));
}

function formatNumber(value, digits = 1) {
  return new Intl.NumberFormat("ru-RU", { maximumFractionDigits: digits }).format(Number(value || 0));
}

function projectImage(project) {
  return projectImages[Number(project?.id || 0) % projectImages.length];
}

function userDisplayName(user) {
  return [user?.first_name, user?.last_name].filter(Boolean).join(" ") || user?.email || user?.username || "";
}

function normalizeOrder(order, defaults) {
  const known = Array.isArray(order) ? order.filter((item) => defaults.includes(item)) : [];
  return [...known, ...defaults.filter((item) => !known.includes(item))];
}

function useBlockOrder(storageKey, defaults) {
  const [order, setOrder] = useState(() => {
    try {
      return normalizeOrder(JSON.parse(localStorage.getItem(storageKey) || "[]"), defaults);
    } catch {
      return defaults;
    }
  });
  const [draggingId, setDraggingId] = useState("");
  const [dragOverId, setDragOverId] = useState("");

  function moveBlock(sourceId, targetId) {
    if (!sourceId || !targetId || sourceId === targetId) return;
    setOrder((current) => {
      const normalized = normalizeOrder(current, defaults).filter((item) => item !== sourceId);
      const targetIndex = normalized.indexOf(targetId);
      const next = [...normalized];
      next.splice(targetIndex < 0 ? next.length : targetIndex, 0, sourceId);
      localStorage.setItem(storageKey, JSON.stringify(next));
      return next;
    });
  }

  function dragHandleProps(id) {
    return {
      draggable: true,
      onDragStart: (event) => {
        setDraggingId(id);
        event.dataTransfer.effectAllowed = "move";
        event.dataTransfer.setData("text/plain", id);
      },
      onDragEnd: () => {
        setDraggingId("");
        setDragOverId("");
      }
    };
  }

  function dropTargetProps(id) {
    return {
      onDragOver: (event) => {
        const sourceId = event.dataTransfer.getData("text/plain") || draggingId;
        if (sourceId && sourceId !== id) {
          event.preventDefault();
          event.dataTransfer.dropEffect = "move";
          setDragOverId(id);
        }
      },
      onDrop: (event) => {
        event.preventDefault();
        const sourceId = event.dataTransfer.getData("text/plain") || draggingId;
        moveBlock(sourceId, id);
        setDraggingId("");
        setDragOverId("");
      },
      onDragLeave: () => {
        if (dragOverId === id) setDragOverId("");
      }
    };
  }

  function blockClassName(id, className) {
    return [
      className,
      draggingId === id ? "dragging-block" : "",
      dragOverId === id ? "drag-over-block" : ""
    ].filter(Boolean).join(" ");
  }

  return { order: normalizeOrder(order, defaults), dragHandleProps, dropTargetProps, blockClassName };
}

function Logo({ large = false }) {
  return (
    <div className={large ? "brand logo large" : "brand logo"}>
      <div className="logo-symbol">
        <Building2 size={22} />
        <span>SB</span>
      </div>
      <div>
        <strong>SmartBuild</strong>
        <span>строительное планирование</span>
      </div>
    </div>
  );
}

function storageSetAuth(token, user) {
  localStorage.setItem("smartbuild_token", token);
  const firstEnterprise = user.memberships?.[0]?.enterprise_id || "";
  localStorage.setItem("smartbuild_enterprise", String(firstEnterprise));
  return String(firstEnterprise);
}

export default function App() {
  const [token, setToken] = useState(() => localStorage.getItem("smartbuild_token") || "");
  const [user, setUser] = useState(null);
  const [enterpriseId, setEnterpriseId] = useState(() => localStorage.getItem("smartbuild_enterprise") || "");
  const [activeTab, setActiveTab] = useState("projects");
  const [dashboard, setDashboard] = useState(null);
  const [projects, setProjects] = useState([]);
  const [selectedProjectId, setSelectedProjectId] = useState("");
  const [projectDetail, setProjectDetail] = useState(null);
  const [materials, setMaterials] = useState([]);
  const [suppliers, setSuppliers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [navOpen, setNavOpen] = useState(false);

  const activeEnterprise = useMemo(() => {
    return user?.memberships?.find((item) => String(item.enterprise_id) === String(enterpriseId));
  }, [user, enterpriseId]);

  async function api(path, options = {}) {
    const headers = {
      "Content-Type": "application/json",
      ...(options.headers || {})
    };
    if (token) headers.Authorization = `Token ${token}`;
    if (enterpriseId) headers["X-Enterprise-ID"] = enterpriseId;

    const response = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers,
      body: options.body ? JSON.stringify(options.body) : undefined
    });
    const contentType = response.headers.get("content-type") || "";
    const data = contentType.includes("application/json") ? await response.json() : {};
    if (!response.ok) {
      if (response.status === 401) handleLogout();
      throw new Error(data?.error?.message || "Запрос не выполнен");
    }
    return data;
  }

  function handleLogout() {
    localStorage.removeItem("smartbuild_token");
    localStorage.removeItem("smartbuild_enterprise");
    setToken("");
    setUser(null);
    setDashboard(null);
    setProjects([]);
    setProjectDetail(null);
    setSelectedProjectId("");
  }

  async function loadMe(currentToken = token) {
    if (!currentToken) return;
    try {
      const response = await fetch(`${API_BASE}/auth/me/`, {
        headers: { Authorization: `Token ${currentToken}` }
      });
      if (!response.ok) throw new Error("auth");
      const data = await response.json();
      setUser(data.user);
      const firstEnterprise = data.user.memberships?.[0]?.enterprise_id;
      const known = data.user.memberships?.some((item) => String(item.enterprise_id) === String(enterpriseId));
      if (!enterpriseId || !known) {
        setEnterpriseId(String(firstEnterprise || ""));
        localStorage.setItem("smartbuild_enterprise", String(firstEnterprise || ""));
      }
    } catch {
      handleLogout();
    }
  }

  async function loadWorkspace(focusProjectId = selectedProjectId) {
    if (!token || !enterpriseId) return;
    setLoading(true);
    setError("");
    try {
      const [dash, projectList, materialList, supplierList] = await Promise.all([
        api("/dashboard/"),
        api("/projects/"),
        api("/materials/"),
        api("/suppliers/")
      ]);
      setDashboard(dash);
      setProjects(projectList.projects || []);
      setMaterials(materialList.materials || []);
      setSuppliers(supplierList.suppliers || []);
      const nextProjectId = focusProjectId || projectList.projects?.[0]?.id || "";
      setSelectedProjectId(String(nextProjectId || ""));
      if (nextProjectId) {
        await loadProject(nextProjectId);
      } else {
        setProjectDetail(null);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function loadProject(projectId) {
    if (!projectId) return;
    const data = await api(`/projects/${projectId}/calculate/`);
    setProjectDetail(data);
  }

  useEffect(() => {
    loadMe();
  }, []);

  useEffect(() => {
    if (token && enterpriseId) loadWorkspace();
  }, [token, enterpriseId]);

  async function login(username, password) {
    setLoading(true);
    setError("");
    try {
      const response = await fetch(`${API_BASE}/auth/login/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password })
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data?.error?.message || "Вход не выполнен");
      const firstEnterprise = storageSetAuth(data.token, data.user);
      setToken(data.token);
      setUser(data.user);
      setEnterpriseId(firstEnterprise);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function register(payload) {
    setLoading(true);
    setError("");
    try {
      const response = await fetch(`${API_BASE}/auth/register/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data?.error?.message || "Регистрация не выполнена");
      const firstEnterprise = storageSetAuth(data.token, data.user);
      setToken(data.token);
      setUser(data.user);
      setEnterpriseId(firstEnterprise);
      setMessage("Аккаунт создан. Можно добавлять первый проект.");
      setActiveTab("projects");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function logout() {
    try {
      if (token) await api("/auth/logout/", { method: "POST" });
    } finally {
      handleLogout();
    }
  }

  async function createProject(payload) {
    setLoading(true);
    setError("");
    try {
      const data = await api("/projects/", { method: "POST", body: payload });
      setMessage("Проект создан и рассчитан");
      setSelectedProjectId(String(data.project.id));
      setProjectDetail(data);
      await loadWorkspace(data.project.id);
      setActiveTab("project");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function saveProject(payload) {
    if (!selectedProjectId) return;
    setLoading(true);
    setError("");
    try {
      const data = await api(`/projects/${selectedProjectId}/`, { method: "PATCH", body: payload });
      setProjectDetail(data);
      setMessage("Параметры сохранены, расчёт обновлён");
      await loadWorkspace(selectedProjectId);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function saveWorks(works) {
    if (!selectedProjectId) return;
    setLoading(true);
    setError("");
    try {
      const data = await api(`/projects/${selectedProjectId}/works/`, {
        method: "PATCH",
        body: { works }
      });
      setProjectDetail(data);
      setMessage("Состав работ обновлён");
      await loadWorkspace(selectedProjectId);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function replaceMaterial(workType, materialId) {
    if (!selectedProjectId) return;
    setLoading(true);
    setError("");
    try {
      const data = await api(`/projects/${selectedProjectId}/alternatives/`, {
        method: "POST",
        body: { work_type: workType, material_id: materialId }
      });
      setProjectDetail(data);
      setMessage("Материал заменён, смета и график пересчитаны");
      await loadWorkspace(selectedProjectId);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function createGoal(payload) {
    if (!selectedProjectId) return;
    setLoading(true);
    setError("");
    try {
      const data = await api(`/projects/${selectedProjectId}/goals/`, { method: "POST", body: payload });
      setProjectDetail(data.project);
      setMessage("Цель добавлена в проект");
      await loadWorkspace(selectedProjectId);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function updateGoal(goalId, payload) {
    if (!selectedProjectId) return;
    setLoading(true);
    setError("");
    try {
      const data = await api(`/projects/${selectedProjectId}/goals/${goalId}/`, { method: "PATCH", body: payload });
      setProjectDetail(data.project);
      setMessage("Цель обновлена");
      await loadWorkspace(selectedProjectId);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function createSeat(payload) {
    if (!selectedProjectId) return;
    setLoading(true);
    setError("");
    try {
      const data = await api(`/projects/${selectedProjectId}/seats/`, { method: "POST", body: payload });
      setProjectDetail(data.project);
      setMessage("Место в команде добавлено");
      await loadWorkspace(selectedProjectId);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function updateSeat(seatId, payload) {
    if (!selectedProjectId) return;
    setLoading(true);
    setError("");
    try {
      const data = await api(`/projects/${selectedProjectId}/seats/${seatId}/`, { method: "PATCH", body: payload });
      setProjectDetail(data.project);
      setMessage(payload.status === "open" ? "Место снова ожидает участника" : "Место в команде обновлено");
      await loadWorkspace(selectedProjectId);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function updateProcurement(itemId, status) {
    setLoading(true);
    setError("");
    try {
      const data = await api(`/procurement/${itemId}/`, { method: "PATCH", body: { status } });
      setProjectDetail(data.project);
      setMessage(status === "ordered" ? "Позиция отмечена как заказанная" : "Статус закупки обновлён");
      await loadWorkspace(selectedProjectId);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function createMaterial(payload) {
    setLoading(true);
    setError("");
    try {
      await api("/materials/", { method: "POST", body: payload });
      setMessage("Материал добавлен в справочник");
      await loadWorkspace(selectedProjectId);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  if (!token || !user) {
    return (
      <PublicShell
        onLogin={login}
        onRegister={register}
        loading={loading}
        error={error}
        clearError={() => setError("")}
      />
    );
  }

  return (
    <div className="app-shell">
      <aside className={navOpen ? "sidebar open" : "sidebar"}>
        <div className="brand-row">
          <Logo />
          <button className="menu-button" onClick={() => setNavOpen(!navOpen)} title="Меню">
            {navOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>

        <nav className="app-nav">
          {tabs.map(([key, label, Icon]) => (
            <button
              key={key}
              className={activeTab === key || (activeTab === "project" && key === "projects") ? "nav-item active" : "nav-item"}
              onClick={() => {
                setActiveTab(key);
                setNavOpen(false);
              }}
            >
              <Icon size={18} />
              <span>{label}</span>
            </button>
          ))}
        </nav>

        <div className="sidebar-footer">
          <div>
            <strong>{user.first_name || user.username}</strong>
            <span>{activeEnterprise?.role_label}</span>
          </div>
          <button className="icon-button" onClick={logout} title="Выйти">
            <LogOut size={18} />
          </button>
        </div>
      </aside>

      <main className="workspace">
        <header className="topbar">
          <div>
            <p className="eyebrow">{activeTab === "project" ? "Открытый проект" : "SmartBuild"}</p>
            <h1>{activeTab === "project" ? projectDetail?.project?.name || "Проект" : tabs.find(([key]) => key === activeTab)?.[1]}</h1>
          </div>
          <div className="topbar-actions">
            <ProjectSelect
              projects={projects}
              value={selectedProjectId}
              onChange={async (id) => {
                setSelectedProjectId(String(id));
                await loadProject(id);
                setActiveTab("project");
              }}
            />
            <button className="ghost-button" onClick={() => loadWorkspace()} disabled={loading}>
              <RefreshCw size={18} />
              <span>Обновить</span>
            </button>
          </div>
        </header>

        {(error || message) && (
          <div className={error ? "notice error" : "notice success"}>
            {error || message}
            <button onClick={() => (error ? setError("") : setMessage(""))}>x</button>
          </div>
        )}

        {activeTab === "account" && (
          <AccountView
            dashboard={dashboard}
            user={user}
            activeEnterprise={activeEnterprise}
            enterpriseId={enterpriseId}
            memberships={user.memberships}
            projects={projects}
            api={api}
            onEnterpriseChange={(id) => {
              setEnterpriseId(id);
              localStorage.setItem("smartbuild_enterprise", id);
              setSelectedProjectId("");
              setProjectDetail(null);
            }}
            onOpenProject={(id) => {
              setSelectedProjectId(String(id));
              loadProject(id);
              setActiveTab("project");
            }}
            onCreateFirst={() => setActiveTab("projects")}
          />
        )}
        {activeTab === "projects" && (
          <ProjectsView
            projects={projects}
            selectedProject={projectDetail?.project}
            onCreate={createProject}
            onSelect={(id) => {
              setSelectedProjectId(String(id));
              loadProject(id);
              setActiveTab("project");
            }}
          />
        )}
        {activeTab === "project" && (
          projectDetail ? (
            <ProjectWorkspace
              detail={projectDetail}
              user={user}
              materials={materials}
              suppliers={suppliers}
              activeEnterprise={activeEnterprise}
              onSaveProject={saveProject}
              onSaveWorks={saveWorks}
              onReplaceMaterial={replaceMaterial}
              onCreateGoal={createGoal}
              onUpdateGoal={updateGoal}
              onCreateSeat={createSeat}
              onUpdateSeat={updateSeat}
              onOrder={updateProcurement}
              onCreateMaterial={createMaterial}
              api={api}
            />
          ) : (
            <EmptyState title="Создайте проект, чтобы получить смету" action="Создать проект" onAction={() => setActiveTab("projects")} />
          )
        )}
      </main>
    </div>
  );
}

function PublicShell({ onLogin, onRegister, loading, error, clearError }) {
  const [view, setView] = useState("home");

  function switchView(next) {
    clearError();
    setView(next);
  }

  if (view === "login") {
    return (
      <AuthScreen
        title="Вход в SmartBuild"
        subtitle="Продолжите работу с проектами, сметами и графиками."
        onBack={() => switchView("home")}
      >
        <LoginForm onLogin={onLogin} loading={loading} error={error} onRegister={() => switchView("register")} />
      </AuthScreen>
    );
  }

  if (view === "register") {
    return (
      <AuthScreen
        title="Создание аккаунта"
        subtitle="Выберите личное пространство или рабочее пространство компании."
        onBack={() => switchView("home")}
      >
        <RegisterForm onRegister={onRegister} loading={loading} error={error} onLogin={() => switchView("login")} />
      </AuthScreen>
    );
  }

  return <LandingPage onLogin={() => switchView("login")} onRegister={() => switchView("register")} />;
}

function LandingPage({ onLogin, onRegister }) {
  const features = [
    ["Сметы", "Расчёт материалов, работ, потерь и резерва бюджета.", WalletCards],
    ["Календарь", "График этапов с технологическими перерывами и бригадой.", CalendarDays],
    ["Закупки", "Даты заказа материалов с учётом сроков поставщиков.", Truck],
    ["Замены", "Сравнение альтернатив по стоимости и срокам.", Replace]
  ];

  return (
    <div className="landing">
      <header className="landing-header">
        <Logo />
        <div className="landing-actions">
          <button className="ghost-button" onClick={onLogin}>
            <ShieldCheck size={18} />
            <span>Войти</span>
          </button>
          <button className="primary-button" onClick={onRegister}>
            <UserPlus size={18} />
            <span>Регистрация</span>
          </button>
        </div>
      </header>

      <main className="landing-hero">
        <section className="hero-copy">
          <p className="eyebrow">Для частных проектов и строительных компаний</p>
          <h1>Планируйте стройку от сметы до поставки материалов</h1>
          <p>
            SmartBuild объединяет расчёт материалов, календарный график работ,
            анализ замен и логистику закупок в одном веб-интерфейсе.
          </p>
          <div className="hero-actions">
            <button className="primary-button" onClick={onRegister}>
              <span>Начать работу</span>
              <ArrowRight size={18} />
            </button>
            <button className="ghost-button" onClick={onLogin}>
              <span>Открыть демо</span>
            </button>
          </div>
          <div className="hero-badges">
            <span>Личные проекты</span>
            <span>Командная работа</span>
            <span>PostgreSQL + Docker</span>
          </div>
        </section>

        <section className="hero-visual" aria-label="Пример интерфейса SmartBuild">
          <div className="visual-topline">
            <span>Коттедж Сосновый</span>
            <strong>14 820 000 ₽</strong>
          </div>
          <div className="visual-grid">
            <div className="visual-card teal">
              <CalendarDays size={22} />
              <span>График</span>
              <strong>86 дней</strong>
            </div>
            <div className="visual-card amber">
              <Truck size={22} />
              <span>Закупки</span>
              <strong>12 заказов</strong>
            </div>
            <div className="visual-card slate">
              <Boxes size={22} />
              <span>Материалы</span>
              <strong>28 позиций</strong>
            </div>
          </div>
          <div className="visual-timeline">
            <div style={{ width: "42%" }}>Фундамент</div>
            <div style={{ width: "62%" }}>Стены</div>
            <div style={{ width: "34%" }}>Кровля</div>
            <div style={{ width: "75%" }}>Отделка</div>
          </div>
        </section>
      </main>

      <section className="feature-band">
        {features.map(([title, text, Icon]) => (
          <article className="feature-item" key={title}>
            <Icon size={24} />
            <h2>{title}</h2>
            <p>{text}</p>
          </article>
        ))}
      </section>

      <section className="photo-band">
        {projectImages.slice(0, 4).map((image, index) => (
          <div key={image} style={{ backgroundImage: `url(${image})` }}>
            <span>{["Монолит", "Планирование", "Коммерция", "Жильё"][index]}</span>
          </div>
        ))}
      </section>

      <section className="supplier-lead-section">
        <div>
          <p className="eyebrow">Для поставщиков</p>
          <h2>Хотите добавить свои материалы в SmartBuild?</h2>
          <p>Оставьте заявку на сотрудничество. После одобрения поставщик сможет войти в личный аккаунт и управлять каталогом материалов.</p>
        </div>
        <SupplierLeadForm />
      </section>
    </div>
  );
}

function SupplierLeadForm() {
  const [form, setForm] = useState({
    company_name: "",
    contact_name: "",
    email: "",
    phone: "",
    city: "",
    materials: "",
    message: ""
  });
  const [state, setState] = useState("");

  function setField(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function submit(event) {
    event.preventDefault();
    setState("");
    const response = await fetch(`${API_BASE}/supplier-applications/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(form)
    });
    setState(response.ok ? "Заявка отправлена" : "Не удалось отправить заявку");
    if (response.ok) {
      setForm({ company_name: "", contact_name: "", email: "", phone: "", city: "", materials: "", message: "" });
    }
  }

  return (
    <form className="supplier-lead-form" onSubmit={submit} autoComplete="off">
      <div className="form-grid compact">
        <input autoComplete="off" value={form.company_name} onChange={(event) => setField("company_name", event.target.value)} placeholder="Компания" required />
        <input autoComplete="off" value={form.contact_name} onChange={(event) => setField("contact_name", event.target.value)} placeholder="Контактное лицо" required />
      </div>
      <div className="form-grid compact">
        <input autoComplete="off" type="email" value={form.email} onChange={(event) => setField("email", event.target.value)} placeholder="Email" required />
        <input autoComplete="off" value={form.phone} onChange={(event) => setField("phone", event.target.value)} placeholder="Телефон" />
      </div>
      <input autoComplete="off" value={form.city} onChange={(event) => setField("city", event.target.value)} placeholder="Город" />
      <input autoComplete="off" value={form.materials} onChange={(event) => setField("materials", event.target.value)} placeholder="Категории материалов" />
      <textarea value={form.message} onChange={(event) => setField("message", event.target.value)} placeholder="Коротко о поставках и условиях" />
      {state && <div className="form-state">{state}</div>}
      <button className="primary-button">
        <Send size={18} />
        <span>Отправить заявку</span>
      </button>
    </form>
  );
}

function AuthScreen({ title, subtitle, onBack, children }) {
  return (
    <div className="auth-screen">
      <button className="back-link" onClick={onBack}>
        <Home size={18} />
        <span>На главную</span>
      </button>
      <section className="auth-card">
        <div className="auth-copy">
          <Logo large />
          <h1>{title}</h1>
          <p>{subtitle}</p>
        </div>
        {children}
      </section>
    </div>
  );
}

function LoginForm({ onLogin, loading, error, onRegister }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  return (
    <form
      className="auth-form"
      onSubmit={(event) => {
        event.preventDefault();
        onLogin(username, password);
      }}
      autoComplete="off"
    >
      <label>
        <span>Email</span>
        <input value={username} onChange={(event) => setUsername(event.target.value)} autoComplete="off" />
      </label>
      <label>
        <span>Пароль</span>
        <input
          type="password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          autoComplete="off"
        />
      </label>
      {error && <div className="form-error">{error}</div>}
      <button className="primary-button" disabled={loading}>
        <ShieldCheck size={18} />
        <span>Войти</span>
      </button>
      <button className="text-button" type="button" onClick={onRegister}>
        Создать новый аккаунт
      </button>
    </form>
  );
}

function RegisterForm({ onRegister, loading, error, onLogin }) {
  const [form, setForm] = useState({
    account_type: "personal",
    first_name: "",
    last_name: "",
    email: "",
    password: "",
    company_name: "",
    supplier_name: "",
    inn: "",
    phone: "",
    address: "",
    lead_time_days: ""
  });

  function setField(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  return (
    <form
      className="auth-form"
      onSubmit={(event) => {
        event.preventDefault();
        onRegister(form);
      }}
      autoComplete="off"
    >
      <div className="account-switch">
        <button
          type="button"
          className={form.account_type === "personal" ? "active" : ""}
          onClick={() => setField("account_type", "personal")}
        >
          <UserRound size={18} />
          <span>Лично</span>
        </button>
        <button
          type="button"
          className={form.account_type === "company" ? "active" : ""}
          onClick={() => setField("account_type", "company")}
        >
          <Factory size={18} />
          <span>Компания</span>
        </button>
        <button
          type="button"
          className={form.account_type === "supplier" ? "active" : ""}
          onClick={() => setField("account_type", "supplier")}
        >
          <Truck size={18} />
          <span>Поставщик</span>
        </button>
      </div>
      <div className="form-grid compact">
        <label>
          <span>Имя</span>
          <input autoComplete="off" value={form.first_name} onChange={(event) => setField("first_name", event.target.value)} />
        </label>
        <label>
          <span>Фамилия</span>
          <input autoComplete="off" value={form.last_name} onChange={(event) => setField("last_name", event.target.value)} />
        </label>
      </div>
      <label>
        <span>Email</span>
        <input
          type="email"
          value={form.email}
          onChange={(event) => setField("email", event.target.value)}
          autoComplete="off"
          required
        />
      </label>
      <label>
        <span>Пароль</span>
        <input
          type="password"
          value={form.password}
          onChange={(event) => setField("password", event.target.value)}
          autoComplete="off"
          minLength={8}
          required
        />
      </label>
      {form.account_type === "company" && (
        <>
          <label>
            <span>Название компании</span>
            <input autoComplete="off" value={form.company_name} onChange={(event) => setField("company_name", event.target.value)} required />
          </label>
          <div className="form-grid compact">
            <label>
              <span>ИНН</span>
              <input autoComplete="off" value={form.inn} onChange={(event) => setField("inn", event.target.value)} />
            </label>
            <label>
              <span>Телефон</span>
              <input autoComplete="off" value={form.phone} onChange={(event) => setField("phone", event.target.value)} />
            </label>
          </div>
          <label>
            <span>Адрес</span>
            <input autoComplete="off" value={form.address} onChange={(event) => setField("address", event.target.value)} />
          </label>
        </>
      )}
      {form.account_type === "supplier" && (
        <>
          <label>
            <span>Название поставщика</span>
            <input autoComplete="off" value={form.supplier_name} onChange={(event) => setField("supplier_name", event.target.value)} required />
          </label>
          <div className="form-grid compact">
            <label>
              <span>ИНН</span>
              <input autoComplete="off" value={form.inn} onChange={(event) => setField("inn", event.target.value)} />
            </label>
            <label>
              <span>Срок поставки, дней</span>
              <input autoComplete="off" type="number" min="1" value={form.lead_time_days} onChange={(event) => setField("lead_time_days", event.target.value)} />
            </label>
          </div>
          <label>
            <span>Телефон</span>
            <input autoComplete="off" value={form.phone} onChange={(event) => setField("phone", event.target.value)} />
          </label>
          <label>
            <span>Адрес склада</span>
            <input autoComplete="off" value={form.address} onChange={(event) => setField("address", event.target.value)} />
          </label>
        </>
      )}
      {form.account_type === "personal" && (
        <label>
          <span>Телефон</span>
          <input autoComplete="off" value={form.phone} onChange={(event) => setField("phone", event.target.value)} />
        </label>
      )}
      {error && <div className="form-error">{error}</div>}
      <button className="primary-button" disabled={loading}>
        <UserPlus size={18} />
        <span>Зарегистрироваться</span>
      </button>
      <button className="text-button" type="button" onClick={onLogin}>
        Уже есть аккаунт
      </button>
    </form>
  );
}

function ProjectSelect({ projects, value, onChange }) {
  return (
    <label className="project-select">
      <select value={value || ""} onChange={(event) => onChange(event.target.value)} disabled={!projects.length}>
        {projects.length ? (
          projects.map((project) => (
            <option key={project.id} value={project.id}>
              {project.name}
            </option>
          ))
        ) : (
          <option value="">Нет проектов</option>
        )}
      </select>
      <ChevronDown size={16} />
    </label>
  );
}

function AccountView({
  dashboard,
  user,
  activeEnterprise,
  enterpriseId,
  memberships,
  projects,
  api,
  onEnterpriseChange,
  onOpenProject,
  onCreateFirst
}) {
  const cards = [
    ["Проекты", dashboard?.cards?.projects || 0, Building2],
    ["Материалы", dashboard?.cards?.materials || 0, Boxes],
    ["Поставщики", dashboard?.cards?.suppliers || 0, Truck],
    ["Мои цели", dashboard?.cards?.my_goals || 0, Target]
  ];

  return (
    <div className="screen-grid">
      <section className="panel profile-panel wide">
        <div className="profile-photo" style={{ backgroundImage: `url(${projectImages[1]})` }} />
        <div className="profile-copy">
          <p className="eyebrow">Личный кабинет</p>
          <h2>{userDisplayName(user)}</h2>
          <p>
            Здесь собраны ваши проекты, назначенные цели, заявки на участие и рабочие роли в разных объектах.
          </p>
        </div>
      </section>

      {memberships?.length > 1 && (
        <section className="panel workspace-switch-panel wide">
          <div>
            <p className="eyebrow">Рабочая область</p>
            <h2>Данные для расчётов и проектов</h2>
          </div>
          <label className="workspace-switcher">
            <select value={enterpriseId} onChange={(event) => onEnterpriseChange(event.target.value)}>
              {memberships.map((membership) => (
                <option key={membership.enterprise_id} value={membership.enterprise_id}>
                  {membership.enterprise_kind_label}: {membership.enterprise_name}
                </option>
              ))}
            </select>
            <ChevronDown size={16} />
          </label>
        </section>
      )}

      <section className="metric-grid">
        {cards.map(([label, value, Icon]) => (
          <article className="metric-card" key={label}>
            <Icon size={22} />
            <span>{label}</span>
            <strong>{value}</strong>
          </article>
        ))}
      </section>

      <section className="panel finance-panel">
        <div className="section-title">
          <div>
            <p className="eyebrow">Финансы</p>
            <h2>Портфель</h2>
          </div>
          <BadgeRussianRuble size={22} />
        </div>
        <div className="finance-row">
          <span>Материалы</span>
          <strong>{formatMoney(dashboard?.totals?.material_cost)}</strong>
        </div>
        <div className="finance-row">
          <span>Работы</span>
          <strong>{formatMoney(dashboard?.totals?.labor_cost)}</strong>
        </div>
        <div className="finance-row total">
          <span>Итого</span>
          <strong>{formatMoney(dashboard?.totals?.direct_cost)}</strong>
        </div>
      </section>

      <section className="panel wide">
        <div className="section-title">
          <div>
            <p className="eyebrow">Объекты</p>
            <h2>Активные проекты</h2>
          </div>
          <button className="ghost-button compact-button" onClick={onCreateFirst}>
            <Plus size={17} />
            <span>Новый</span>
          </button>
        </div>
        {projects.length ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Название</th>
                  <th>Тип</th>
                  <th>Старт</th>
                  <th>Стоимость</th>
                  <th>Статус</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {projects.map((project) => (
                  <tr key={project.id}>
                    <td>{project.name}</td>
                    <td>{project.object_type_label}</td>
                    <td>{project.start_date}</td>
                    <td>{formatMoney(project.totals?.grand_total)}</td>
                    <td><span className="status-pill">{project.project_role_label || project.status_label}</span></td>
                    <td>
                      <button className="icon-button" onClick={() => onOpenProject(project.id)} title="Открыть">
                        <Check size={16} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState title="Проектов пока нет" action="Создать первый проект" onAction={onCreateFirst} compact />
        )}
      </section>

      <section className="panel">
        <div className="section-title">
          <div>
            <p className="eyebrow">Сроки</p>
            <h2>Мои цели</h2>
          </div>
          <Target size={22} />
        </div>
        <div className="compact-list">
          {(dashboard?.my_goals || []).length ? (
            dashboard.my_goals.map((item) => (
              <div className="compact-item" key={item.id}>
                <strong>{item.title}</strong>
                <span>{item.due_date ? `до ${item.due_date}` : "без даты"} · {item.priority_label}</span>
              </div>
            ))
          ) : (
            <div className="muted-box">Назначенные задачи появятся после добавления целей в проекте.</div>
          )}
        </div>
      </section>

      <section className="panel">
        <div className="section-title">
          <div>
            <p className="eyebrow">Участие в чужом проекте</p>
            <h2>Подать заявку</h2>
          </div>
          <UserCog size={22} />
        </div>
        <JoinProjectForm api={api} activeEnterprise={activeEnterprise} />
      </section>
    </div>
  );
}

function JoinProjectForm({ api, activeEnterprise }) {
  const [form, setForm] = useState({ project_id: "", requested_role: "viewer", message: "" });
  const [state, setState] = useState("");

  function setField(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function submit(event) {
    event.preventDefault();
    setState("");
    try {
      await api(`/projects/${form.project_id}/join-requests/`, {
        method: "POST",
        body: { requested_role: form.requested_role, message: form.message }
      });
      setState("Заявка отправлена владельцу проекта");
      setForm({ project_id: "", requested_role: "viewer", message: "" });
    } catch (err) {
      setState(err.message);
    }
  }

  const workRoleDisabled = activeEnterprise?.enterprise_kind !== "company";

  return (
    <form className="form-grid" autoComplete="off" onSubmit={submit}>
      <label>
        <span>ID проекта</span>
        <input autoComplete="off" value={form.project_id} onChange={(event) => setField("project_id", event.target.value)} required />
      </label>
      <label>
        <span>Роль</span>
        <select value={form.requested_role} onChange={(event) => setField("requested_role", event.target.value)}>
          <option value="viewer">Наблюдатель</option>
          <option value="developer">Застройщик</option>
          <option value="foreman" disabled={workRoleDisabled}>Прораб</option>
          <option value="builder" disabled={workRoleDisabled}>Исполнитель</option>
          <option value="estimator" disabled={workRoleDisabled}>Сметчик</option>
        </select>
      </label>
      <label className="wide-field">
        <span>Комментарий <HelpTip text="Для рабочих ролей нужно выбрать пространство компании, чтобы владелец видел, от какой организации пришёл участник." /></span>
        <textarea value={form.message} onChange={(event) => setField("message", event.target.value)} />
      </label>
      {state && <div className="form-state wide-field">{state}</div>}
      <button className="primary-button wide-field">
        <Send size={18} />
        <span>Отправить заявку</span>
      </button>
    </form>
  );
}

function ProjectsView({ projects, selectedProject, onCreate, onSelect }) {
  const [draft, setDraft] = useState(emptyProject);
  const [showCreate, setShowCreate] = useState(false);

  return (
    <div className="screen-grid">
      <section className="panel wide projects-hero">
        <div>
          <p className="eyebrow">Мои объекты и участие</p>
          <h2>Проекты</h2>
          <p>Здесь собраны личные проекты, объекты компании и проекты, где пользователь принят в команду.</p>
        </div>
        <button className="primary-button" onClick={() => setShowCreate((value) => !value)}>
          <FilePlus2 size={18} />
          <span>{showCreate ? "Скрыть форму" : "Создать проект"}</span>
        </button>
      </section>

      {showCreate && (
      <section className="panel wide">
        <div className="section-title">
          <div>
            <p className="eyebrow">Создание</p>
            <h2>Новый объект</h2>
          </div>
          <Plus size={22} />
        </div>
        <ProjectForm
          value={draft}
          onChange={setDraft}
          submitLabel="Создать"
          onSubmit={() => {
            onCreate(draft);
            setDraft(emptyProject);
            setShowCreate(false);
          }}
        />
      </section>
      )}

      <section className="panel wide">
        <div className="section-title">
          <div>
            <p className="eyebrow">{projects.length} карточек</p>
            <h2>Список проектов</h2>
          </div>
          <LayoutGrid size={22} />
        </div>
        <div className="project-card-grid">
          {projects.length ? projects.map((project) => (
            <article className={selectedProject?.id === project.id ? "project-card active" : "project-card"} key={project.id}>
              <div className="project-card-image" style={{ backgroundImage: `url(${projectImage(project)})` }}>
                <span>{project.object_type_label}</span>
              </div>
              <div className="project-card-body">
                <div>
                  <p className="eyebrow">{project.enterprise_name}</p>
                  <h3>{project.name}</h3>
                </div>
                <div className="project-card-meta">
                  <span>{project.start_date}</span>
                  <strong>{formatMoney(project.totals?.grand_total)}</strong>
                </div>
                <div className="hero-badges compact">
                  <span>{project.project_role_label || "Доступ"}</span>
                  <span>{project.status_label}</span>
                </div>
                <button className="primary-button" onClick={() => onSelect(project.id)}>
                  <ArrowRight size={18} />
                  <span>Открыть</span>
                </button>
              </div>
            </article>
          )) : <div className="muted-box">После создания проекта он появится в этом списке.</div>}
        </div>
      </section>

    </div>
  );
}

function HelpTip({ text }) {
  return (
    <span className="help-tip" tabIndex="0">
      <Info size={14} />
      <small>{text}</small>
    </span>
  );
}

function ProjectForm({ value, onChange, onSubmit, submitLabel }) {
  function setField(field, nextValue) {
    onChange({ ...value, [field]: nextValue });
  }

  return (
    <form className="form-grid" onSubmit={(event) => {
      event.preventDefault();
      onSubmit();
    }} autoComplete="off">
      <label>
        <span>Название</span>
        <input autoComplete="off" value={value.name || ""} onChange={(event) => setField("name", event.target.value)} required />
      </label>
      <label>
        <span>Тип объекта</span>
        <select value={value.object_type || "house"} onChange={(event) => setField("object_type", event.target.value)}>
          {objectTypes.map(([key, label]) => <option key={key} value={key}>{label}</option>)}
        </select>
      </label>
      <label className="wide-field">
        <span>Адрес</span>
        <input autoComplete="off" value={value.address || ""} onChange={(event) => setField("address", event.target.value)} />
      </label>
      <label>
        <span>Длина, м <HelpTip text="Габарит объекта по длинной стороне. Если оставить пустым, система применит базовое значение для первичного расчёта." /></span>
        <input autoComplete="off" type="number" step="0.1" value={value.length || ""} onChange={(event) => setField("length", event.target.value)} />
      </label>
      <label>
        <span>Ширина, м <HelpTip text="Используется вместе с длиной для расчёта площади, кровли и фундамента." /></span>
        <input autoComplete="off" type="number" step="0.1" value={value.width || ""} onChange={(event) => setField("width", event.target.value)} />
      </label>
      <label>
        <span>Высота, м <HelpTip text="Высота этажа влияет на площадь стен и фасадных работ." /></span>
        <input autoComplete="off" type="number" step="0.1" value={value.height || ""} onChange={(event) => setField("height", event.target.value)} />
      </label>
      <label>
        <span>Этажей</span>
        <input autoComplete="off" type="number" min="1" value={value.floors || ""} onChange={(event) => setField("floors", event.target.value)} />
      </label>
      <label>
        <span>Площадь, м2 <HelpTip text="Можно указать вручную для квартир, офисов и объектов нестандартной формы." /></span>
        <input autoComplete="off" type="number" step="0.1" value={value.area || ""} onChange={(event) => setField("area", event.target.value)} />
      </label>
      <label>
        <span>Старт</span>
        <input autoComplete="off" type="date" value={value.start_date || ""} onChange={(event) => setField("start_date", event.target.value)} />
      </label>
      <label>
        <span>Рабочих <HelpTip text="Количество людей в бригаде влияет на длительность этапов и календарный график." /></span>
        <input autoComplete="off" type="number" min="1" value={value.workers || ""} onChange={(event) => setField("workers", event.target.value)} />
      </label>
      <label>
        <span>Резерв, % <HelpTip text="Финансовый запас на рост цен, дополнительные работы и непредвиденные расходы." /></span>
        <input autoComplete="off" type="number" min="0" step="0.5" value={value.contingency_percent || ""} onChange={(event) => setField("contingency_percent", event.target.value)} />
      </label>
      <button className="primary-button wide-field">
        <Save size={18} />
        <span>{submitLabel}</span>
      </button>
    </form>
  );
}

function ProjectWorkspace({
  detail,
  user,
  materials,
  suppliers,
  activeEnterprise,
  onSaveProject,
  onSaveWorks,
  onReplaceMaterial,
  onCreateGoal,
  onUpdateGoal,
  onCreateSeat,
  onUpdateSeat,
  onOrder,
  onCreateMaterial,
  api
}) {
  const [section, setSection] = useState("overview");
  const sections = [
    ["overview", "Обзор", BarChart3],
    ["calculation", "Расчёт", BadgeRussianRuble],
    ["schedule", "График", CalendarDays],
    ["procurement", "Закупки", Truck],
    ["materials", "Материалы", Boxes],
    ["goals", "Цели", Target],
    ["team", "Команда", UsersRound]
  ];

  useEffect(() => {
    setSection("overview");
  }, [detail.project.id]);

  return (
    <div className="project-workspace">
      <section className="project-cover" style={{ backgroundImage: `url(${projectImage(detail.project)})` }}>
        <div>
          <p className="eyebrow">{detail.project.enterprise_name}</p>
          <h2>{detail.project.name}</h2>
          <div className="hero-badges compact">
            <span>{detail.project.object_type_label}</span>
            <span>{detail.project.project_role_label || "Участник"}</span>
            <span>{formatMoney(detail.project.totals?.grand_total)}</span>
          </div>
        </div>
      </section>

      <div className="project-section-tabs">
        {sections.map(([key, label, Icon]) => (
          <button key={key} className={section === key ? "active" : ""} onClick={() => setSection(key)}>
            <Icon size={17} />
            <span>{label}</span>
          </button>
        ))}
      </div>

      {section === "overview" && (
        <ProjectOverview detail={detail} onSaveProject={onSaveProject} />
      )}
      {section === "calculation" && (
        <EstimateView
          detail={detail}
          user={user}
          materials={materials}
          onSaveProject={onSaveProject}
          onSaveWorks={onSaveWorks}
          onReplaceMaterial={onReplaceMaterial}
          api={api}
        />
      )}
      {section === "schedule" && <ScheduleView detail={detail} onCreateGoal={onCreateGoal} onUpdateGoal={onUpdateGoal} />}
      {section === "procurement" && <ProcurementView detail={detail} user={user} onOrder={onOrder} />}
      {section === "materials" && (
        <MaterialsView
          materials={materials}
          suppliers={suppliers}
          activeEnterprise={activeEnterprise}
          onCreateMaterial={onCreateMaterial}
        />
      )}
      {section === "goals" && <GoalsView detail={detail} onCreateGoal={onCreateGoal} onUpdateGoal={onUpdateGoal} />}
      {section === "team" && <TeamView detail={detail} user={user} api={api} onCreateSeat={onCreateSeat} onUpdateSeat={onUpdateSeat} />}
    </div>
  );
}

function ProjectOverview({ detail, onSaveProject }) {
  const [projectDraft, setProjectDraft] = useState(detail.project);
  const total = detail.project.totals || {};

  useEffect(() => {
    setProjectDraft({ ...detail.project, area: detail.project.area || "" });
  }, [detail.project.id, detail.project.updated_at]);

  return (
    <div className="screen-grid">
      <section className="panel wide">
        <div className="total-strip">
          <div><span>Материалы</span><strong>{formatMoney(total.material_cost)}</strong></div>
          <div><span>Работы</span><strong>{formatMoney(total.labor_cost)}</strong></div>
          <div><span>Резерв</span><strong>{formatMoney(total.contingency)}</strong></div>
          <div><span>Итого</span><strong>{formatMoney(total.grand_total)}</strong></div>
        </div>
      </section>
      <section className="panel">
        <div className="section-title">
          <div>
            <p className="eyebrow">Редактирование</p>
            <h2>Параметры объекта</h2>
          </div>
          <SlidersHorizontal size={22} />
        </div>
        <ProjectForm value={projectDraft} onChange={setProjectDraft} submitLabel="Сохранить и пересчитать" onSubmit={() => onSaveProject(projectDraft)} />
      </section>
      <section className="panel">
        <div className="section-title">
          <div>
            <p className="eyebrow">Ответственность</p>
            <h2>Ближайшие цели</h2>
          </div>
          <Target size={22} />
        </div>
        <div className="compact-list">
          {(detail.goals || []).slice(0, 5).map((goal) => (
            <div className="compact-item" key={goal.id}>
              <strong>{goal.title}</strong>
              <span>{goal.assignee_name || "без исполнителя"} · {goal.due_date || "без даты"}</span>
            </div>
          ))}
          {!(detail.goals || []).length && <div className="muted-box">Цели и дедлайны можно добавить во вкладке «Цели».</div>}
        </div>
      </section>
    </div>
  );
}

function EstimateView({ detail, user, materials, onSaveProject, onSaveWorks, onReplaceMaterial, api }) {
  const [projectDraft, setProjectDraft] = useState(detail.project);
  const [workDrafts, setWorkDrafts] = useState(detail.works || []);
  const [selectedWorkType, setSelectedWorkType] = useState(detail.works?.[0]?.work_type || "foundation");
  const [alternatives, setAlternatives] = useState([]);

  useEffect(() => {
    setProjectDraft({ ...detail.project, area: detail.project.area || "" });
    setWorkDrafts(detail.works || []);
    setSelectedWorkType(detail.works?.[0]?.work_type || "foundation");
  }, [detail.project.id, detail.project.updated_at]);

  useEffect(() => {
    async function loadAlternatives() {
      if (!detail?.project?.id || !selectedWorkType) return;
      const response = await api(`/projects/${detail.project.id}/alternatives/?work_type=${selectedWorkType}`);
      setAlternatives(response.alternatives || []);
    }
    loadAlternatives().catch(() => setAlternatives([]));
  }, [detail.project.id, selectedWorkType, detail.project.updated_at]);

  const total = detail.project.totals || {};
  const estimateBlocks = ["summary", "object", "works", "estimate", "alternatives"];
  const {
    order: blockOrder,
    dragHandleProps,
    dropTargetProps,
    blockClassName
  } = useBlockOrder(`smartbuild_estimate_blocks_${user?.id || "guest"}_${detail.project.id}`, estimateBlocks);
  const blockStyle = (id) => ({ order: blockOrder.indexOf(id) });

  function updateWork(index, field, value) {
    const next = workDrafts.map((work, currentIndex) =>
      currentIndex === index ? { ...work, [field]: value } : work
    );
    setWorkDrafts(next);
  }

  return (
    <div className="screen-grid">
      <section className={blockClassName("summary", "panel wide compact-panel")} style={blockStyle("summary")} {...dropTargetProps("summary")}>
        <div className="section-title draggable-title" title="Перетащить блок" {...dragHandleProps("summary")}>
          <div>
            <p className="eyebrow">{detail.project.object_type_label}</p>
            <h2>{detail.project.name}</h2>
          </div>
          <BadgeRussianRuble size={22} />
        </div>
        <div className="total-strip">
          <div><span>Материалы</span><strong>{formatMoney(total.material_cost)}</strong></div>
          <div><span>Работы</span><strong>{formatMoney(total.labor_cost)}</strong></div>
          <div><span>Резерв</span><strong>{formatMoney(total.contingency)}</strong></div>
          <div><span>Итого</span><strong>{formatMoney(total.grand_total)}</strong></div>
        </div>
      </section>

      <section className={blockClassName("object", "panel compact-panel")} style={blockStyle("object")} {...dropTargetProps("object")}>
        <div className="section-title draggable-title" title="Перетащить блок" {...dragHandleProps("object")}>
          <div>
            <p className="eyebrow">Параметры</p>
            <h2>Объект</h2>
          </div>
          <SlidersHorizontal size={22} />
        </div>
        <ProjectForm
          value={projectDraft}
          onChange={setProjectDraft}
          submitLabel="Пересчитать"
          onSubmit={() => onSaveProject(projectDraft)}
        />
      </section>

      <section className={blockClassName("works", "panel compact-panel")} style={blockStyle("works")} {...dropTargetProps("works")}>
        <div className="section-title draggable-title" title="Перетащить блок" {...dragHandleProps("works")}>
          <div>
            <p className="eyebrow">Состав</p>
            <h2>Виды работ</h2>
          </div>
          <ClipboardList size={22} />
        </div>
        <div className="work-list">
          {[...workDrafts]
            .map((work, index) => ({ work, index }))
            .sort((a, b) => workOrder.indexOf(a.work.work_type) - workOrder.indexOf(b.work.work_type))
            .map(({ work, index }) => {
              const groupMaterials = materials.filter((item) => item.alternative_group === work.material?.alternative_group);
              return (
                <article className={selectedWorkType === work.work_type ? "work-item active" : "work-item"} key={work.work_type}>
                  <button className="work-heading" onClick={() => setSelectedWorkType(work.work_type)} type="button">
                    <span>{work.work_label}</span>
                    <strong>{work.enabled ? "включено" : "выключено"}</strong>
                  </button>
                  <label className="toggle-row">
                    <input
                      type="checkbox"
                      checked={work.enabled}
                      onChange={(event) => updateWork(index, "enabled", event.target.checked)}
                    />
                    <span>Включить этап</span>
                  </label>
                  <label>
                    <span>Материал</span>
                    <select
                      value={work.material?.id || ""}
                      onChange={(event) => updateWork(index, "material", groupMaterials.find((item) => String(item.id) === event.target.value))}
                    >
                      {groupMaterials.map((material) => (
                        <option value={material.id} key={material.id}>{material.name}</option>
                      ))}
                    </select>
                  </label>
                  <div className="two-col">
                    <label>
                      <span>Коэффициент</span>
                      <input
                        type="number"
                        step="0.01"
                        min="0"
                        value={work.coefficient}
                        onChange={(event) => updateWork(index, "coefficient", event.target.value)}
                      />
                    </label>
                    <label>
                      <span>Бригада</span>
                      <input
                        type="number"
                        min="1"
                        value={work.workers_override || ""}
                        onChange={(event) => updateWork(index, "workers_override", event.target.value)}
                      />
                    </label>
                  </div>
                </article>
              );
            })}
        </div>
        <button
          className="primary-button"
          onClick={() =>
            onSaveWorks(workDrafts.map((work) => ({
              work_type: work.work_type,
              enabled: work.enabled,
              coefficient: work.coefficient,
              workers_override: work.workers_override || null,
              material_id: work.material?.id
            })))
          }
        >
          <Save size={18} />
          <span>Применить состав</span>
        </button>
      </section>

      <section className={blockClassName("estimate", "panel wide compact-panel")} style={blockStyle("estimate")} {...dropTargetProps("estimate")}>
        <div className="section-title draggable-title" title="Перетащить блок" {...dragHandleProps("estimate")}>
          <div>
            <p className="eyebrow">Расчёт</p>
            <h2>Смета</h2>
          </div>
          <RefreshCw size={22} />
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Этап</th>
                <th>Материал</th>
                <th>Количество</th>
                <th>Материалы</th>
                <th>Трудозатраты</th>
                <th>Работы</th>
                <th>Итого</th>
              </tr>
            </thead>
            <tbody>
              {detail.estimate.map((line) => (
                <tr key={line.id}>
                  <td>{line.work_label}</td>
                  <td>{line.material?.name}</td>
                  <td>{formatNumber(line.quantity, 2)} {line.unit}</td>
                  <td>{formatMoney(line.material_cost)}</td>
                  <td>{formatNumber(line.labor_hours, 0)} ч</td>
                  <td>{formatMoney(line.labor_cost)}</td>
                  <td><strong>{formatMoney(line.total_cost)}</strong></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className={blockClassName("alternatives", "panel compact-panel")} style={blockStyle("alternatives")} {...dropTargetProps("alternatives")}>
        <div className="section-title draggable-title" title="Перетащить блок" {...dragHandleProps("alternatives")}>
          <div>
            <p className="eyebrow">Анализ</p>
            <h2>Замена материала</h2>
          </div>
          <Replace size={22} />
        </div>
        <div className="segmented">
          {detail.works.map((work) => (
            <button
              key={work.work_type}
              className={selectedWorkType === work.work_type ? "active" : ""}
              onClick={() => setSelectedWorkType(work.work_type)}
            >
              {work.work_label}
            </button>
          ))}
        </div>
        <div className="alternative-list">
          {alternatives.map((item) => (
            <button
              key={item.material_id}
              className={item.is_current ? "alternative active" : "alternative"}
              onClick={() => onReplaceMaterial(selectedWorkType, item.material_id)}
              disabled={item.is_current}
            >
              <span>{item.name}</span>
              <strong>{formatMoney(item.total_cost)}</strong>
              <small>
                {item.cost_delta >= 0 ? "+" : ""}{formatMoney(item.cost_delta)} · {item.duration_delta >= 0 ? "+" : ""}{item.duration_delta} дн.
              </small>
            </button>
          ))}
        </div>
      </section>
    </div>
  );
}

function GoalsView({ detail, onCreateGoal, onUpdateGoal }) {
  const [draft, setDraft] = useState(emptyGoal);
  const participants = detail.participants || [];

  function setField(field, value) {
    setDraft((current) => ({ ...current, [field]: value }));
  }

  return (
    <div className="screen-grid">
      <section className="panel">
        <div className="section-title">
          <div>
            <p className="eyebrow">Дела и дедлайны</p>
            <h2>Новая цель</h2>
          </div>
          <Target size={22} />
        </div>
        <form className="form-grid" autoComplete="off" onSubmit={(event) => {
          event.preventDefault();
          onCreateGoal(draft);
          setDraft(emptyGoal);
        }}>
          <label className="wide-field">
            <span>Название</span>
            <input autoComplete="off" value={draft.title} onChange={(event) => setField("title", event.target.value)} required />
          </label>
          <label className="wide-field">
            <span>Описание</span>
            <textarea value={draft.description} onChange={(event) => setField("description", event.target.value)} />
          </label>
          <label>
            <span>Исполнитель</span>
            <select value={draft.assignee_id} onChange={(event) => setField("assignee_id", event.target.value)}>
              <option value="">Не назначен</option>
              {participants.map((item) => <option key={item.user_id} value={item.user_id}>{item.name} · {item.role_label}</option>)}
            </select>
          </label>
          <label>
            <span>Дедлайн</span>
            <input autoComplete="off" type="date" value={draft.due_date} onChange={(event) => setField("due_date", event.target.value)} />
          </label>
          <label className="wide-field">
            <span>Приоритет</span>
            <select value={draft.priority} onChange={(event) => setField("priority", event.target.value)}>
              <option value="normal">Обычный</option>
              <option value="high">Высокий</option>
              <option value="low">Низкий</option>
            </select>
          </label>
          <button className="primary-button wide-field">
            <Plus size={18} />
            <span>Добавить цель</span>
          </button>
        </form>
      </section>

      <section className="panel wide">
        <div className="section-title">
          <div>
            <p className="eyebrow">{detail.goals?.length || 0} пунктов</p>
            <h2>{detail.project.name}</h2>
          </div>
          <List size={22} />
        </div>
        <div className="goal-board">
          {(detail.goals || []).map((goal) => (
            <article className={`goal-card ${goal.priority}`} key={goal.id}>
              <div>
                <strong>{goal.title}</strong>
                <p>{goal.description}</p>
              </div>
              <div className="goal-meta">
                <span>{goal.assignee_name || "без исполнителя"}</span>
                <span>{goal.due_date || "без даты"}</span>
              </div>
              <select value={goal.status} onChange={(event) => onUpdateGoal(goal.id, { status: event.target.value })}>
                <option value="todo">К выполнению</option>
                <option value="in_progress">В работе</option>
                <option value="done">Готово</option>
                <option value="blocked">Заблокировано</option>
              </select>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}

function TeamView({ detail, user, api, onCreateSeat, onUpdateSeat }) {
  const [requests, setRequests] = useState(detail.join_requests || []);
  const [seatDraft, setSeatDraft] = useState(emptySeat);
  const [message, setMessage] = useState("");
  const teamBlocks = ["participants", "newSeat", "seats", "requests"];
  const {
    order: blockOrder,
    dragHandleProps,
    dropTargetProps,
    blockClassName
  } = useBlockOrder(`smartbuild_team_blocks_${user?.id || "guest"}_${detail.project.id}`, teamBlocks);
  const blockStyle = (id) => ({ order: blockOrder.indexOf(id) });

  useEffect(() => {
    setRequests(detail.join_requests || []);
  }, [detail.project.id, detail.join_requests?.length]);

  async function decide(requestId, status, role) {
    const response = await api(`/projects/${detail.project.id}/join-requests/${requestId}/`, {
      method: "PATCH",
      body: { status, role }
    });
    setRequests(response.project.join_requests || []);
    setMessage(status === "approved" ? "Заявка принята" : "Заявка отклонена");
  }

  function setSeatField(field, value) {
    setSeatDraft((current) => ({ ...current, [field]: value }));
  }

  return (
    <div className="screen-grid">
      <section className={blockClassName("participants", "panel compact-panel")} style={blockStyle("participants")} {...dropTargetProps("participants")}>
        <div className="section-title draggable-title" title="Перетащить блок" {...dragHandleProps("participants")}>
          <div>
            <p className="eyebrow">Команда проекта</p>
            <h2>Участники</h2>
          </div>
          <UsersRound size={22} />
        </div>
        <div className="compact-list">
          {(detail.participants || []).map((item) => (
            <div className="compact-item" key={item.id}>
              <strong>{item.name}</strong>
              <span>{item.role_label} · {item.enterprise_name || "лично"}</span>
            </div>
          ))}
        </div>
      </section>

      <section className={blockClassName("newSeat", "panel compact-panel")} style={blockStyle("newSeat")} {...dropTargetProps("newSeat")}>
        <div className="section-title draggable-title" title="Перетащить блок" {...dragHandleProps("newSeat")}>
          <div>
            <p className="eyebrow">Будущие участники</p>
            <h2>Новое место</h2>
          </div>
          <UserPlus size={22} />
        </div>
        <form className="form-grid compact" autoComplete="off" onSubmit={(event) => {
          event.preventDefault();
          onCreateSeat(seatDraft);
          setSeatDraft(emptySeat);
        }}>
          <label className="wide-field">
            <span>Место / ответственность</span>
            <input autoComplete="off" value={seatDraft.title} onChange={(event) => setSeatField("title", event.target.value)} placeholder="Например: прораб по кровле" required />
          </label>
          <label>
            <span>Роль</span>
            <select value={seatDraft.planned_role} onChange={(event) => setSeatField("planned_role", event.target.value)}>
              {Object.entries(projectRoleLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
            </select>
          </label>
          <label>
            <span>Имя или бригада</span>
            <input autoComplete="off" value={seatDraft.contact_name} onChange={(event) => setSeatField("contact_name", event.target.value)} />
          </label>
          <label>
            <span>Email, если уже известен</span>
            <input autoComplete="off" type="email" value={seatDraft.contact_email} onChange={(event) => setSeatField("contact_email", event.target.value)} />
          </label>
          <label>
            <span>Телефон</span>
            <input autoComplete="off" value={seatDraft.contact_phone} onChange={(event) => setSeatField("contact_phone", event.target.value)} />
          </label>
          <label className="wide-field">
            <span>Комментарий</span>
            <textarea value={seatDraft.note} onChange={(event) => setSeatField("note", event.target.value)} />
          </label>
          <button className="primary-button wide-field">
            <Plus size={18} />
            <span>Добавить место</span>
          </button>
        </form>
      </section>

      <section className={blockClassName("seats", "panel wide compact-panel")} style={blockStyle("seats")} {...dropTargetProps("seats")}>
        <div className="section-title draggable-title" title="Перетащить блок" {...dragHandleProps("seats")}>
          <div>
            <p className="eyebrow">{detail.seats?.length || 0} мест</p>
            <h2>План команды</h2>
          </div>
          <UserCog size={22} />
        </div>
        <div className="seat-grid">
          {(detail.seats || []).length ? (detail.seats || []).map((seat) => (
            <SeatCard key={seat.id} seat={seat} onUpdateSeat={onUpdateSeat} />
          )) : <div className="muted-box">Пока нет заранее созданных мест. Добавьте роль, даже если человек ещё не зарегистрирован.</div>}
        </div>
      </section>

      <section className={blockClassName("requests", "panel wide compact-panel")} style={blockStyle("requests")} {...dropTargetProps("requests")}>
        <div className="section-title draggable-title" title="Перетащить блок" {...dragHandleProps("requests")}>
          <div>
            <p className="eyebrow">Проверка заявок</p>
            <h2>Доступ к проекту</h2>
          </div>
          <UserCheck size={22} />
        </div>
        {message && <div className="notice success">{message}<button onClick={() => setMessage("")}>x</button></div>}
        <div className="request-list">
          {requests.length ? requests.map((request) => (
            <article className="request-card" key={request.id}>
              <div>
                <strong>{request.applicant_name}</strong>
                <span>{request.applicant_enterprise_name || "личное пространство"} · хочет роль: {request.requested_role_label}</span>
                <p>{request.message}</p>
              </div>
              <div className="request-actions">
                <button className="primary-button compact-button" onClick={() => decide(request.id, "approved", request.requested_role)}>
                  <Check size={16} />
                  <span>Принять</span>
                </button>
                <button className="ghost-button compact-button" onClick={() => decide(request.id, "rejected", request.requested_role)}>
                  <X size={16} />
                  <span>Отклонить</span>
                </button>
              </div>
            </article>
          )) : <div className="muted-box">Новых заявок нет. Рабочие роли принимаются с учётом компании пользователя.</div>}
        </div>
      </section>
    </div>
  );
}

function SeatCard({ seat, onUpdateSeat }) {
  const [assignEmail, setAssignEmail] = useState(seat.contact_email || "");
  const isAssigned = seat.status === "assigned";

  useEffect(() => {
    setAssignEmail(seat.contact_email || seat.assigned_user_email || "");
  }, [seat.id, seat.contact_email, seat.assigned_user_email, seat.status]);

  return (
    <article className={isAssigned ? "seat-card assigned" : "seat-card"}>
      <div className="seat-card-main">
        <div>
          <strong>{seat.title}</strong>
          <span>{seat.planned_role_label} · {seat.status_label}</span>
        </div>
        <span className="status-pill">{isAssigned ? "назначено" : "ожидает"}</span>
      </div>
      <p>{seat.assigned_user_name || seat.contact_name || "Контакт пока не указан"}</p>
      {(seat.assigned_user_email || seat.contact_email || seat.contact_phone) && (
        <div className="seat-contact">
          <span>{seat.assigned_user_email || seat.contact_email}</span>
          {seat.contact_phone && <span>{seat.contact_phone}</span>}
        </div>
      )}
      {seat.note && <small>{seat.note}</small>}
      <div className="seat-actions">
        <input
          autoComplete="off"
          type="email"
          value={assignEmail}
          onChange={(event) => setAssignEmail(event.target.value)}
          placeholder="email зарегистрированного пользователя"
        />
        <button className="primary-button compact-button" onClick={() => onUpdateSeat(seat.id, { assigned_user_email: assignEmail })}>
          <UserCheck size={16} />
          <span>Назначить</span>
        </button>
        {isAssigned && (
          <button className="ghost-button compact-button" onClick={() => onUpdateSeat(seat.id, { status: "open" })}>
            <X size={16} />
            <span>Освободить</span>
          </button>
        )}
      </div>
    </article>
  );
}

function ScheduleView({ detail, onCreate, onCreateGoal, onUpdateGoal }) {
  if (!detail) return <EmptyState title="Проект не выбран" action="Создать проект" onAction={onCreate} />;
  const tasks = detail.schedule || [];
  const goals = detail.goals || [];
  const rootGoals = goals.filter((goal) => !goal.parent_id);
  const subgoalsByParent = goals.reduce((acc, goal) => {
    if (goal.parent_id) {
      acc[goal.parent_id] = [...(acc[goal.parent_id] || []), goal];
    }
    return acc;
  }, {});
  const start = new Date(tasks[0]?.start_date || detail.project.start_date);
  const end = new Date(tasks[tasks.length - 1]?.end_date || detail.project.start_date);
  const totalDays = Math.max(1, Math.round((end - start) / 86400000) + 1);
  const [expandedTaskId, setExpandedTaskId] = useState(tasks[0]?.id || "");
  const [hoverInfo, setHoverInfo] = useState(null);
  const [taskDrafts, setTaskDrafts] = useState({});
  const [subgoalDrafts, setSubgoalDrafts] = useState({});

  useEffect(() => {
    setExpandedTaskId(tasks[0]?.id || "");
    setTaskDrafts({});
    setSubgoalDrafts({});
  }, [detail.project.id]);

  function dateInside(dueDate, task) {
    if (!dueDate) return false;
    return dueDate >= task.start_date && dueDate <= task.end_date;
  }

  function goalsForTask(task) {
    return rootGoals.filter((goal) => dateInside(goal.due_date, task));
  }

  function taskDraft(taskId) {
    return taskDrafts[taskId] || "";
  }

  function subgoalDraft(goalId) {
    return subgoalDrafts[goalId] || "";
  }

  function addTaskGoal(task) {
    const title = taskDraft(task.id).trim();
    if (!title) return;
    onCreateGoal({
      title,
      description: "",
      due_date: task.end_date,
      priority: "normal"
    });
    setTaskDrafts((current) => ({ ...current, [task.id]: "" }));
  }

  function addSubgoal(goal, task) {
    const title = subgoalDraft(goal.id).trim();
    if (!title) return;
    onCreateGoal({
      title,
      description: "",
      parent_id: goal.id,
      assignee_id: goal.assignee_id || "",
      due_date: goal.due_date || task.end_date,
      priority: goal.priority || "normal"
    });
    setSubgoalDrafts((current) => ({ ...current, [goal.id]: "" }));
  }

  function updateHover(event, taskId) {
    const rect = event.currentTarget.getBoundingClientRect();
    const ratio = Math.min(1, Math.max(0, (event.clientX - rect.left) / rect.width));
    const dayOffset = Math.round(ratio * Math.max(0, totalDays - 1));
    const date = new Date(start);
    date.setDate(start.getDate() + dayOffset);
    setHoverInfo({
      taskId,
      left: ratio * 100,
      label: date.toLocaleDateString("ru-RU", { day: "2-digit", month: "2-digit", year: "numeric" })
    });
  }

  return (
    <section className="panel wide">
      <div className="section-title">
        <div>
          <p className="eyebrow">{totalDays} дн.</p>
          <h2>{detail.project.name}</h2>
        </div>
        <CalendarDays size={22} />
      </div>
      <div className="timeline">
        {tasks.map((task) => {
          const taskStart = new Date(task.start_date);
          const taskEnd = new Date(task.end_date);
          const left = Math.max(0, Math.round((taskStart - start) / 86400000)) / totalDays * 100;
          const width = Math.max(5, (Math.round((taskEnd - taskStart) / 86400000) + 1) / totalDays * 100);
          const taskGoals = goalsForTask(task);
          const isExpanded = String(expandedTaskId) === String(task.id);
          return (
            <div className={isExpanded ? "timeline-item expanded" : "timeline-item"} key={task.id}>
              <div className="timeline-row">
                <div className="timeline-label">
                  <button className="timeline-toggle" type="button" onClick={() => setExpandedTaskId(isExpanded ? "" : task.id)}>
                    <ChevronDown size={16} />
                    <strong>{task.title}</strong>
                  </button>
                  <span>{task.start_date} - {task.end_date}</span>
                </div>
                <div
                  className="timeline-track"
                  onMouseMove={(event) => updateHover(event, task.id)}
                  onMouseLeave={() => setHoverInfo(null)}
                >
                  <div className="timeline-bar" style={{ left: `${left}%`, width: `${width}%` }}>
                    {task.work_days}+{task.tech_break_days}
                  </div>
                  {hoverInfo?.taskId === task.id && (
                    <div className="timeline-hover" style={{ left: `${hoverInfo.left}%` }}>
                      {hoverInfo.label}
                    </div>
                  )}
                </div>
                <div className="timeline-meta">
                  <UsersRound size={15} />
                  <span>{task.workers}</span>
                </div>
              </div>
              {isExpanded && (
                <div className="timeline-details">
                  <div className="timeline-goals">
                    {taskGoals.length ? taskGoals.map((goal) => (
                      <article className="timeline-goal" key={goal.id}>
                        <div className="timeline-goal-head">
                          <div>
                            <strong>{goal.title}</strong>
                            <span>{goal.due_date || task.end_date} · {goal.assignee_name || "без исполнителя"}</span>
                          </div>
                          <select value={goal.status} onChange={(event) => onUpdateGoal(goal.id, { status: event.target.value })}>
                            <option value="todo">К выполнению</option>
                            <option value="in_progress">В работе</option>
                            <option value="done">Готово</option>
                            <option value="blocked">Заблокировано</option>
                          </select>
                        </div>
                        <div className="subgoal-list">
                          {(subgoalsByParent[goal.id] || []).map((subgoal) => (
                            <div className="subgoal-item" key={subgoal.id}>
                              <span>{subgoal.title}</span>
                              <small>{subgoal.due_date || goal.due_date || task.end_date}</small>
                            </div>
                          ))}
                        </div>
                        <div className="inline-add">
                          <input
                            autoComplete="off"
                            value={subgoalDraft(goal.id)}
                            onChange={(event) => setSubgoalDrafts((current) => ({ ...current, [goal.id]: event.target.value }))}
                            placeholder="Подпункт"
                          />
                          <button className="ghost-button compact-button" type="button" onClick={() => addSubgoal(goal, task)}>
                            <Plus size={15} />
                            <span>Добавить</span>
                          </button>
                        </div>
                      </article>
                    )) : <div className="muted-box">На этом интервале пока нет целей. Добавьте пункт, и он сохранится в проекте.</div>}
                  </div>
                  <div className="inline-add">
                    <input
                      autoComplete="off"
                      value={taskDraft(task.id)}
                      onChange={(event) => setTaskDrafts((current) => ({ ...current, [task.id]: event.target.value }))}
                      placeholder="Пункт для этого этапа"
                    />
                    <button className="primary-button compact-button" type="button" onClick={() => addTaskGoal(task)}>
                      <Plus size={15} />
                      <span>Добавить пункт</span>
                    </button>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}

function ProcurementView({ detail, user, onCreate, onOrder }) {
  if (!detail) return <EmptyState title="Проект не выбран" action="Создать проект" onAction={onCreate} />;
  const procurementBlocks = ["summary", "orders"];
  const {
    order: blockOrder,
    dragHandleProps,
    dropTargetProps,
    blockClassName
  } = useBlockOrder(`smartbuild_procurement_blocks_${user?.id || "guest"}_${detail.project.id}`, procurementBlocks);
  const blockStyle = (id) => ({ order: blockOrder.indexOf(id) });
  const items = detail.procurement || [];
  const plannedCount = items.filter((item) => item.status === "planned").length;
  const orderedCount = items.filter((item) => item.status === "ordered").length;
  const deliveredCount = items.filter((item) => item.status === "delivered").length;
  const procurementTotal = items.reduce((sum, item) => sum + Number(item.estimated_cost || 0), 0);
  return (
    <div className="screen-grid">
      <section className={blockClassName("summary", "panel compact-panel")} style={blockStyle("summary")} {...dropTargetProps("summary")}>
        <div className="section-title draggable-title" title="Перетащить блок" {...dragHandleProps("summary")}>
          <div>
            <p className="eyebrow">{items.length} позиций</p>
            <h2>Сводка закупок</h2>
          </div>
          <PackageCheck size={22} />
        </div>
        <div className="mini-stats">
          <div><span>План</span><strong>{plannedCount}</strong></div>
          <div><span>Заказано</span><strong>{orderedCount}</strong></div>
          <div><span>Поставлено</span><strong>{deliveredCount}</strong></div>
          <div><span>Сумма</span><strong>{formatMoney(procurementTotal)}</strong></div>
        </div>
      </section>

      <section className={blockClassName("orders", "panel wide compact-panel")} style={blockStyle("orders")} {...dropTargetProps("orders")}>
        <div className="section-title draggable-title" title="Перетащить блок" {...dragHandleProps("orders")}>
          <div>
            <p className="eyebrow">Заказать до</p>
            <h2>{detail.project.name}</h2>
          </div>
          <Truck size={22} />
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Материал</th>
                <th>Поставщик</th>
                <th>Количество</th>
                <th>Дата заказа</th>
                <th>Нужно к</th>
                <th>Стоимость</th>
                <th>Статус</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id}>
                  <td>{item.material?.name}</td>
                  <td>{item.supplier?.name || "не выбран"}</td>
                  <td>{formatNumber(item.quantity, 2)} {item.unit}</td>
                  <td>{item.order_before}</td>
                  <td>{item.needed_by}</td>
                  <td>{formatMoney(item.estimated_cost)}</td>
                  <td><span className="status-pill">{item.status_label}</span></td>
                  <td>
                    {item.status === "planned" && (
                      <button className="ghost-button compact-button" onClick={() => onOrder(item.id, "ordered")}>
                        <ShoppingCart size={16} />
                        <span>Заказать</span>
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

function MaterialsView({ materials, suppliers, activeEnterprise, onCreateMaterial }) {
  const [search, setSearch] = useState("");
  const [group, setGroup] = useState("");
  const [viewMode, setViewMode] = useState("large");
  const [draft, setDraft] = useState({
    name: "",
    category: "Материалы",
    supplier_id: "",
    unit: "m2",
    price: "",
    waste_factor: "0.05",
    delivery_days: "",
    stock_level: "",
    alternative_group: "custom"
  });
  const groups = [...new Set(materials.map((item) => item.alternative_group))].sort();
  const filtered = materials.filter((item) => {
    const matchesSearch = !search || item.name.toLowerCase().includes(search.toLowerCase());
    const matchesGroup = !group || item.alternative_group === group;
    return matchesSearch && matchesGroup;
  });
  const canAdd = activeEnterprise?.role === "owner" || activeEnterprise?.role === "admin";

  function setField(field, value) {
    setDraft((current) => ({ ...current, [field]: value }));
  }

  return (
    <div className="screen-grid">
      <section className="panel wide">
        <div className="section-title">
          <div>
            <p className="eyebrow">{filtered.length} позиций</p>
            <h2>Справочник материалов</h2>
          </div>
          <Search size={22} />
        </div>
        <div className="filters">
          <label>
            <Search size={16} />
            <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Поиск" />
          </label>
          <select value={group} onChange={(event) => setGroup(event.target.value)}>
            <option value="">Все группы</option>
            {groups.map((item) => <option key={item} value={item}>{materialGroupLabels[item] || item}</option>)}
          </select>
          <div className="view-switch">
            <button className={viewMode === "large" ? "active" : ""} onClick={() => setViewMode("large")} title="Большие карточки"><LayoutGrid size={17} /></button>
            <button className={viewMode === "row" ? "active" : ""} onClick={() => setViewMode("row")} title="Строки"><List size={17} /></button>
            <button className={viewMode === "small" ? "active" : ""} onClick={() => setViewMode("small")} title="Маленькие карточки"><Boxes size={17} /></button>
          </div>
        </div>
        {viewMode === "row" ? (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Материал</th>
                <th>Категория</th>
                <th>Группа</th>
                <th>Ед.</th>
                <th>Цена</th>
                <th>Потери</th>
                <th>Поставка</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((material) => (
                <tr key={material.id}>
                  <td>{material.name}</td>
                  <td>{material.category}</td>
                  <td>{material.alternative_group_label || materialGroupLabels[material.alternative_group] || material.alternative_group}</td>
                  <td>{material.unit}</td>
                  <td>{formatMoney(material.price)}</td>
                  <td>{formatNumber(material.waste_factor * 100, 1)}%</td>
                  <td>{material.delivery_days} дн.</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        ) : (
          <div className={viewMode === "small" ? "material-card-grid small" : "material-card-grid"}>
            {filtered.map((material) => (
              <article className="material-card" key={material.id}>
                <div className="material-card-photo" style={{ backgroundImage: `url(${projectImages[material.id % projectImages.length]})` }} />
                <div>
                  <p className="eyebrow">{material.alternative_group_label || materialGroupLabels[material.alternative_group] || material.alternative_group}</p>
                  <h3>{material.name}</h3>
                </div>
                <div className="project-card-meta">
                  <span>{material.supplier?.name || "без поставщика"}</span>
                  <strong>{formatMoney(material.price)}</strong>
                </div>
                <span className="status-pill">поставка {material.delivery_days} дн.</span>
              </article>
            ))}
          </div>
        )}
      </section>
      <section className="panel">
        <div className="section-title">
          <div>
            <p className="eyebrow">{suppliers.length} контрагентов</p>
            <h2>Поставщики</h2>
          </div>
          <Truck size={22} />
        </div>
        <div className="compact-list">
          {suppliers.map((supplier) => (
            <div className="compact-item supplier-item" key={supplier.id}>
              <strong>{supplier.name}</strong>
              <span>{supplier.lead_time_days} дн. · надёжность {supplier.reliability_percent}%</span>
            </div>
          ))}
        </div>
      </section>
      {canAdd && (
      <section className="panel wide">
        <div className="section-title">
          <div>
            <p className="eyebrow">{activeEnterprise?.enterprise_kind_label}</p>
            <h2>Добавить материал</h2>
          </div>
          <Plus size={22} />
        </div>
        <form className="form-grid" autoComplete="off" onSubmit={(event) => {
          event.preventDefault();
          onCreateMaterial(draft);
          setDraft({ ...draft, name: "", price: "" });
        }}>
          <label>
            <span>Название</span>
            <input autoComplete="off" value={draft.name} onChange={(event) => setField("name", event.target.value)} required />
          </label>
          <label>
            <span>Категория</span>
            <input autoComplete="off" value={draft.category} onChange={(event) => setField("category", event.target.value)} />
          </label>
          <label>
            <span>Группа</span>
            <select value={draft.alternative_group} onChange={(event) => setField("alternative_group", event.target.value)}>
              <option value="foundation_concrete">Фундамент и бетон</option>
              <option value="wall_blocks">Стеновые материалы</option>
              <option value="roofing">Кровельные материалы</option>
              <option value="facade_finish">Фасадная отделка</option>
              <option value="interior_finish">Внутренняя отделка</option>
              <option value="engineering_set">Инженерные комплекты</option>
              <option value="custom">Своя группа</option>
            </select>
          </label>
          <label>
            <span>Поставщик</span>
            <select value={draft.supplier_id} onChange={(event) => setField("supplier_id", event.target.value)}>
              <option value="">Автоматически</option>
              {suppliers.map((supplier) => <option key={supplier.id} value={supplier.id}>{supplier.name}</option>)}
            </select>
          </label>
          <label>
            <span>Ед.</span>
            <select value={draft.unit} onChange={(event) => setField("unit", event.target.value)}>
              <option value="m3">м3</option>
              <option value="m2">м2</option>
              <option value="pcs">шт</option>
              <option value="kg">кг</option>
              <option value="bag">мешок</option>
              <option value="roll">рулон</option>
              <option value="set">комплект</option>
            </select>
          </label>
          <label>
            <span>Цена</span>
            <input autoComplete="off" type="number" min="0" value={draft.price} onChange={(event) => setField("price", event.target.value)} required />
          </label>
          <label>
            <span>Потери <HelpTip text="Процент материала, который закладывается на обрезки, бой, подгонку и технологический запас." /></span>
            <input autoComplete="off" type="number" step="0.01" min="0" value={draft.waste_factor} onChange={(event) => setField("waste_factor", event.target.value)} />
          </label>
          <label>
            <span>Поставка, дней</span>
            <input autoComplete="off" type="number" min="1" value={draft.delivery_days} onChange={(event) => setField("delivery_days", event.target.value)} />
          </label>
          <button className="primary-button wide-field">
            <Save size={18} />
            <span>Добавить материал</span>
          </button>
        </form>
      </section>
      )}
    </div>
  );
}

function EmptyState({ title, action, onAction, compact = false }) {
  return (
    <section className={compact ? "empty-state compact" : "empty-state"}>
      <HardHat size={compact ? 26 : 38} />
      <strong>{title}</strong>
      {action && (
        <button className="primary-button" onClick={onAction}>
          <Plus size={18} />
          <span>{action}</span>
        </button>
      )}
    </section>
  );
}
