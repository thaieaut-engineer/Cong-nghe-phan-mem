from __future__ import annotations

from app.repositories.activity_log_repository import ActivityLogRepository


class ActivityLogService:
    """Helper ghi log hoạt động (audit). Best-effort: lỗi DB không làm app crash."""

    def __init__(self, repo: ActivityLogRepository) -> None:
        self._repo = repo

    def log(
        self,
        user: dict | None,
        action: str,
        target_type: str | None = None,
        target_id: int | None = None,
        detail: str | None = None,
    ) -> None:
        user_id = None
        username = None
        if user is not None:
            user_id = user.get("id")
            username = user.get("username")
        try:
            self._repo.log(
                user_id=user_id,
                username=username,
                action=action,
                target_type=target_type,
                target_id=target_id,
                detail=detail,
            )
        except Exception:
            # Audit log không được phá flow nghiệp vụ.
            pass
