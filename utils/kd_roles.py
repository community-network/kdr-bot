import collections
from typing import Optional
from database.dto.kd_roles import KDRole
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import literal_column, select, func, true, update, and_
from sqlalchemy.orm import aliased
from sqlalchemy.dialects.postgresql import JSONB

async def get_all_kd_roles(
    session: AsyncSession,
) -> dict[int, collections.OrderedDict[float, int]]:
    stmt = select(
        KDRole.server_id,
        func.jsonb_agg(
            func.jsonb_build_object(
                "kd_amount", KDRole.kd_amount, "role_id", KDRole.role_id
            )
        ).label("kd_roles"),
    ).group_by(KDRole.server_id)
    res = (await session.execute(stmt)).all()
    return {
        server[0]: collections.OrderedDict(
            sorted(
                {
                    kd_role["kd_amount"]: kd_role["role_id"] for kd_role in server[1]
                }.items()
            )
        )
        for server in res
    }

async def get_channel_kd_roles(
    session: AsyncSession, server_id: int, kd_role_id: Optional[int] = None
):
    R = aliased(KDRole)
    LR = aliased(KDRole)
    lower_roles_sub = (
        select(LR.role_id, LR.kd_amount)
        .where(
            LR.server_id == R.server_id,
            LR.kd_amount < R.kd_amount
        )
        .lateral()
        .alias("lr")
    )

    stmt = (
        select(
            R.server_id,
            R.role_id,
            R.kd_amount,
            R.channel_name,
            func.coalesce(
                func.jsonb_agg(
                    func.jsonb_build_object(
                        "role_id", lower_roles_sub.c.role_id,
                        "kd_amount", lower_roles_sub.c.kd_amount
                    )
                ).filter(lower_roles_sub.c.role_id.is_not(None)),
                literal_column("'[]'::jsonb")
            ).label("lower_roles")
        )
        .filter(R.server_id == server_id)
        .filter(R.channel_name.is_not(None))
        .outerjoin(lower_roles_sub, true())
        .group_by(R.server_id, R.role_id, R.kd_amount)
    )
    if kd_role_id is not None:
        stmt = stmt.filter(R.role_id == kd_role_id)

    rows = (await session.execute(stmt)).all()
    res = [{"server_id":row[0], "role_id": row[1], "kd_amount":row[2], "channel_name": row[3], "lower_roles": row[4]} for row in rows]

    if kd_role_id is None:
        return res
    
    if len(res) > 0:
        return res[0]
    return None


async def get_kd_roles(
    session: AsyncSession, server_id: int
) -> collections.OrderedDict[float, int]:
    stmt = (
        select(KDRole.kd_amount, KDRole.role_id)
        .filter(KDRole.server_id == server_id)
        .order_by(KDRole.kd_amount)
    )
    res = (await session.execute(stmt)).all()
    return collections.OrderedDict(
        sorted({kd_role.kd_amount: kd_role.role_id for kd_role in res}.items())
    )


async def get_kd_role(session: AsyncSession, server_id: int, role_id: int) -> KDRole | None:
    stmt = (
        select(KDRole)
        .filter(
            and_(
                KDRole.server_id == server_id,
                KDRole.role_id == role_id,
            )
        )
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def has_kd_role(session: AsyncSession, server_id: int, role_id: int) -> bool | None:
    exists_criteria = (
        select(KDRole.server_id)
        .filter(KDRole.server_id == server_id)
        .filter(KDRole.role_id == role_id)
        .exists()
    )
    stmt = select(exists_criteria)
    return await session.scalar(stmt)


async def update_kd_role(session: AsyncSession, server_id: int, role_id: int, changes: dict):
    stmt = (
        update(KDRole).where(KDRole.server_id == server_id).where(KDRole.role_id == role_id).values(changes)
    )
    await session.execute(stmt)
    await session.commit()

