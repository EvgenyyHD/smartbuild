from django.urls import path

from . import views


urlpatterns = [
    path("health/", views.health),
    path("supplier-applications/", views.supplier_application),
    path("auth/login/", views.login),
    path("auth/register/", views.register),
    path("auth/logout/", views.logout),
    path("auth/me/", views.me),
    path("dashboard/", views.dashboard),
    path("suppliers/", views.suppliers),
    path("materials/", views.materials),
    path("labor-norms/", views.labor_norms),
    path("projects/", views.projects),
    path("projects/<int:project_id>/", views.project_detail),
    path("projects/<int:project_id>/calculate/", views.project_calculate),
    path("projects/<int:project_id>/works/", views.project_works),
    path("projects/<int:project_id>/alternatives/", views.project_alternatives),
    path("projects/<int:project_id>/goals/", views.project_goals),
    path("projects/<int:project_id>/goals/<int:goal_id>/", views.project_goal_detail),
    path("projects/<int:project_id>/seats/", views.project_seats),
    path("projects/<int:project_id>/seats/<int:seat_id>/", views.project_seat_detail),
    path("projects/<int:project_id>/join-requests/", views.project_join_requests),
    path("projects/<int:project_id>/join-requests/<int:request_id>/", views.project_join_request_detail),
    path("procurement/<int:procurement_id>/", views.procurement_detail),
]
