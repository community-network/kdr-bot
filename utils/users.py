import csv
import datetime
import io

import discord
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from database.dto.users import User
from database.error_handling import is_unique_violation

async def get_csv(session: AsyncSession, server_id: int) -> tuple[int, discord.File]:
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
        return (total, discord.File(data_stream, filename="users.csv"))
    
async def import_csv(session: AsyncSession, server_id: int, file: discord.Attachment):
    if file.filename.endswith(".csv"):
        res = await file.read()
        test = io.StringIO(res.decode("utf-8"))
        data = list(csv.reader(test, delimiter=','))
        for i in data[1:]:
            try:
                user = User().import_user(i, data[0])
                user.server_id = server_id
                user.created_at = datetime.datetime.now()
                user.updated_at = datetime.datetime.now()
                session.add(user)
                await session.commit()
            except IntegrityError as ex:
                await session.rollback()
                if is_unique_violation(ex):
                    continue # user already exists
                else:
                    print(ex)