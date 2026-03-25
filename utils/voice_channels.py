from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from database.dto.voice_channels import VoiceChannel

async def get_voice_channels(session: AsyncSession, server_id: int) -> list[int]:
    stmt = (
        select(VoiceChannel.id)
        .filter(VoiceChannel.server_id == server_id)
    )
    res = (await session.execute(stmt)).all()
    return [channel[0] for channel in res]

async def get_role_voice_channels(session: AsyncSession, server_id: int, role_id: int) -> list[int] | None:
    stmt = (
        select(VoiceChannel.id)
        .filter(VoiceChannel.server_id == server_id)
        .filter(VoiceChannel.kdr_role_id == role_id)
    )
    res = (await session.execute(stmt)).all()
    return [channel[0] for channel in res]


async def get_voice_channel(session: AsyncSession, server_id: int, channel_id: int) -> VoiceChannel | None:
    stmt = (
        select(VoiceChannel)
        .filter(VoiceChannel.id == channel_id)
        .filter(VoiceChannel.server_id == server_id)
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()

async def add_voice_channel(session: AsyncSession, server_id: int, channel_id: int, kdr_role_id: int):
    channel = dict(server_id=server_id, id=channel_id, kdr_role_id=kdr_role_id)
    stmt = insert(VoiceChannel).values(channel)
    try:
        await session.execute(stmt)
        await session.commit()
    except IntegrityError:
        pass

async def update_voice_channel(session: AsyncSession, channel_id: int, changes: dict):
    stmt = (
        update(VoiceChannel).where(VoiceChannel.id == channel_id).values(changes)
    )
    await session.execute(stmt)
    await session.commit()

async def remove_voice_channel(session: AsyncSession,server_id: int, channel_id: int):
    voice_channel = await get_voice_channel(session, server_id, channel_id)
    await session.delete(voice_channel)
    await session.commit()