from django.utils import timezone

from .models import ApiAccessToken, Membership


def authenticate_token(request):
    header = request.META.get("HTTP_AUTHORIZATION", "")
    if not header.startswith("Token "):
        return None, None
    raw_key = header.replace("Token ", "", 1).strip()
    if not raw_key:
        return None, None

    token = (
        ApiAccessToken.objects.select_related("user")
        .filter(key_hash=ApiAccessToken.hash_key(raw_key))
        .first()
    )
    if not token or not token.is_active or not token.user.is_active:
        return None, None
    return token.user, token


def revoke_token(token):
    token.revoked_at = timezone.now()
    token.save(update_fields=["revoked_at"])


def membership_for_request(request, user):
    enterprise_id = request.META.get("HTTP_X_ENTERPRISE_ID") or request.GET.get("enterprise_id")
    queryset = Membership.objects.select_related("enterprise").filter(
        user=user,
        is_active=True,
        enterprise__is_active=True,
    )
    if enterprise_id:
        queryset = queryset.filter(enterprise_id=enterprise_id)
    return queryset.order_by("enterprise__name").first()

