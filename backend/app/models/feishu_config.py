from __future__ import annotations

import logging

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.core.database import Base
from backend.app.core.encryption import decrypt_value, encrypt_value
from backend.app.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin, UpdatedAtMixin

logger = logging.getLogger(__name__)


class FeishuConfig(UUIDPrimaryKeyMixin, CreatedAtMixin, UpdatedAtMixin, Base):
    """飞书连接配置模型 — 每条记录保存一个飞书应用的多维表格同步配置。"""

    __tablename__ = 'feishu_configs'

    app_id: Mapped[str] = mapped_column(String(128), nullable=False)
    encrypted_app_secret: Mapped[str] = mapped_column(String(512), nullable=False)
    bitable_app_token: Mapped[str] = mapped_column(String(128), nullable=False)
    bitable_table_id: Mapped[str] = mapped_column(String(128), nullable=False)
    field_mapping: Mapped[str] = mapped_column(Text, nullable=False, default='{}')
    sync_hour: Mapped[int] = mapped_column(Integer, nullable=False, default=6)
    sync_minute: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sync_timezone: Mapped[str] = mapped_column(String(64), nullable=False, default='Asia/Shanghai')
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    def set_app_secret(self, plaintext: str, encryption_key: str) -> None:
        """Encrypt and store the app_secret."""
        self.encrypted_app_secret = encrypt_value(plaintext, encryption_key)

    def get_app_secret(self, encryption_key: str) -> str:
        """Decrypt and return the app_secret."""
        return decrypt_value(self.encrypted_app_secret, encryption_key)

    def get_masked_secret(self) -> str:
        """Return a masked representation of the encrypted secret for display."""
        if not self.encrypted_app_secret:
            return '****'
        # Show only last 4 chars of the encrypted token for identification
        return '****' + self.encrypted_app_secret[-4:]
