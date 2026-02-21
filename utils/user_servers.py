from sqlalchemy import func, select
from database.dto.users import User
from dto.user_servers import ServerRef, UserServers
from sqlalchemy.dialects.postgresql import aggregate_order_by
from sqlalchemy.ext.asyncio import AsyncSession


def build_grouped_stmt():
    server_discord_obj = func.jsonb_build_object(
        "server_id",
        User.server_id,
        "discord_id",
        User.discord_id,
        "username",
        User.username,
        "kdr_role_id",
        User.kdr_role_id,
    )
    return (
        select(
            User.user_id,
            User.player_id,
            func.jsonb_agg(server_discord_obj).label("servers"),
        )
        .group_by(User.user_id, User.player_id)
        .order_by(User.user_id.asc(), User.player_id.asc())
    )


async def fetch_user_servers(session: AsyncSession) -> list[list[UserServers]]:
    stmt = build_grouped_stmt()
    chunks = (await session.execute(stmt)).partitions(10)

    return [
        [
            UserServers(
                user_id=row.user_id,
                player_id=row.player_id,
                servers=[ServerRef(**d) for d in (row.servers or [])],
            )
            for row in chunk
        ]
        for chunk in chunks
    ]
