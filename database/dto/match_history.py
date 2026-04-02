import datetime
from sqlalchemy import JSON, BigInteger, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from database.connection import Base

class MatchHistory(Base):
    __tablename__ = "match_histories"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    discord_id: Mapped[int] = mapped_column(BigInteger)
    player_id: Mapped[int] = mapped_column(BigInteger)
    user_id: Mapped[int] = mapped_column(BigInteger)
    data: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )