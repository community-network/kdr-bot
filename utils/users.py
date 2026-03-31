import csv
import io

import discord
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.dto.users import User

async def get_users_csv(session: AsyncSession, server_id: int) -> tuple[int, discord.File]:
    stmt = (
        select(User)
        .filter(User.server_id == server_id)
    )
    res = (await session.execute(stmt)).all()
    total = len(res)
    with io.StringIO() as data_stream:
        outcsv = csv.writer(data_stream)
        outcsv.writerow(User.__table__.columns.keys())     
        for row in res:
            outcsv.writerow([row[0].server_id, row[0].discord_id, row[0].username, row[0].player_id, row[0].kdr_role_id, row[0].user_id, row[0].created_at, row[0].updated_at])
        data_stream.seek(0)
        return (total, discord.File(data_stream, filename="channel_names.csv"))