import datetime

from sqlalchemy import delete, insert
from sqlalchemy.ext.asyncio import AsyncSession

from database.dto.match_history import MatchHistory

async def add_history_item(session: AsyncSession, discord_id: int, player_id: int, user_id: int, data: dict):
    channel = dict(discord_id=discord_id, player_id=player_id, user_id=user_id, data=data)
    stmt = insert(MatchHistory).values(channel)
    await session.execute(stmt)
    await session.commit()

async def remove_old_items(session: AsyncSession):
    current_time = datetime.datetime.now(datetime.timezone.utc)
    month_ago = current_time - datetime.timedelta(days=30)
    stmt = delete(MatchHistory).where(MatchHistory.created_at < month_ago)
    await session.execute(stmt)
    await session.commit()