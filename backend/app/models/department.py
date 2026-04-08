from __future__ import annotations

from typing import Optional

from sqlalchemy import Column, ForeignKey, String, Table, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base
from backend.app.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin, UpdatedAtMixin

user_department_links = Table(
    'user_department_links',
    Base.metadata,
    Column('user_id', ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
    Column('department_id', ForeignKey('departments.id', ondelete='CASCADE'), primary_key=True),
)


class Department(UUIDPrimaryKeyMixin, CreatedAtMixin, UpdatedAtMixin, Base):
    __tablename__ = 'departments'

    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default='active', index=True)

    users = relationship('User', secondary=user_department_links, back_populates='departments')
    cycle_budgets = relationship('CycleDepartmentBudget', back_populates='department')
