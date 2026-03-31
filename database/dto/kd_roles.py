import datetime
from sqlalchemy import BigInteger, DateTime, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from database.connection import Base
from typing import Optional


class KDRole(Base):
    __tablename__ = "kd_roles"
    server_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    role_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    kd_amount: Mapped[float] = mapped_column()
    channel_name: Mapped[Optional[str]]
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    __table_args__ = (
        UniqueConstraint(server_id, role_id, kd_amount),
    )  # must be a tuple!

    def import_kdrole(self, row, header):
        import_data = dict(zip(header, row))
        self.server_id = int(import_data.get("server_id"))
        self.role_id = int(import_data.get("role_id"))
        self.kd_amount = float(import_data.get("kd_amount"))
        self.channel_name = import_data.get("channel_name")
        return self
