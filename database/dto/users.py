import datetime
from typing import Optional
from sqlalchemy import BigInteger, DateTime, UniqueConstraint, func, update
from sqlalchemy.orm import Mapped, mapped_column
from database.connection import Base
from sqlalchemy.ext.asyncio import AsyncSession


class User(Base):
    __tablename__ = "users"
    server_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    discord_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str]
    player_id: Mapped[int] = mapped_column(BigInteger)
    kdr_role_id: Mapped[Optional[int]] = mapped_column(BigInteger)
    user_id: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    __table_args__ = (
        UniqueConstraint(server_id, discord_id, player_id, user_id),
    )  # must be a tuple!

    async def update_kdr(self, session: AsyncSession, kdr_role_id: int | None):
        stmt = (
            update(User)
            .where(User.discord_id == self.discord_id)
            .values(kdr_role_id=kdr_role_id)
        )
        await session.execute(stmt)
        await session.commit()
