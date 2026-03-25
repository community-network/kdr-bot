import datetime
from typing import Optional
from sqlalchemy import BigInteger, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from database.connection import Base


class ServerSetting(Base):
    __tablename__ = "server_settings"
    server_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    log_channel_id: Mapped[Optional[int]] = mapped_column(BigInteger)
    category_id: Mapped[Optional[int]] = mapped_column(BigInteger)
    server_name: Mapped[str]
    mode: Mapped[str] = mapped_column(default="Redsec")
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
