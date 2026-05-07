from django.urls import path

from .views import LoginView, LogoutView, SignupView, TokenRefreshView


urlpatterns = [
    # Industry-standard-ish structure (REST + trailing slashes)
    path("api/auth/register/", SignupView.as_view(), name="auth-register"),
    path("api/auth/login/", LoginView.as_view(), name="auth-login"),
    path("api/auth/logout/", LogoutView.as_view(), name="auth-logout"),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="auth-token-refresh"),

    # Backward-compatible paths matching the existing repo routes
    path("api/signup", SignupView.as_view(), name="signup"),
    path("api/login", LoginView.as_view(), name="login"),
    path("api/logout", LogoutView.as_view(), name="logout"),
]

