from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from databases.users_db import Base


class Business(Base):
    __tablename__ = "businesses"

    inn: Mapped[str] = mapped_column(String(12), primary_key=True)
    name: Mapped[str] = mapped_column(String(500))
    subject_type: Mapped[str] = mapped_column(String(2))
    category: Mapped[int] = mapped_column(Integer)
    ogrn: Mapped[str] = mapped_column(String(15))
    main_activity_code: Mapped[str] = mapped_column(String(20))
    main_activity_name: Mapped[str] = mapped_column(String(500))
    region_code: Mapped[str] = mapped_column(String(10))
    is_new: Mapped[bool] = mapped_column(Boolean)
    date_registered: Mapped[str] = mapped_column(String(20))
    date_excluded: Mapped[str | None] = mapped_column(String(20), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    website: Mapped[str | None] = mapped_column(String(255), nullable=True)
    has_licenses: Mapped[bool] = mapped_column(Boolean)
    is_hitech: Mapped[bool] = mapped_column(Boolean)
    is_partnership: Mapped[bool] = mapped_column(Boolean)
    is_social: Mapped[bool] = mapped_column(Boolean)


class UserBusiness(Base):
    """Связь многие-ко-многим: у пользователя может быть несколько ИНН, один ИНН — у нескольких пользователей."""

    __tablename__ = "user_businesses"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    inn: Mapped[str] = mapped_column(String(12), ForeignKey("businesses.inn"), primary_key=True, index=True)
