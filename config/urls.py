from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path


urlpatterns = [
    path("admin/", admin.site.urls),
    path("entrar/", auth_views.LoginView.as_view(template_name="core/login.html"), name="login"),
    path("sair/", auth_views.LogoutView.as_view(), name="logout"),
    path("api/", include("financas.api_urls")),
    path("api/", include("core.api_urls")),
    path("api-auth/", include("rest_framework.urls")),
    path("", include("core.urls")),
    path("", include("financas.urls")),
]
