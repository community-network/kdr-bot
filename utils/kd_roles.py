from sqlalchemy import func, select
import collections
from database.dto.kd_roles import KDRole
from sqlalchemy.ext.asyncio import AsyncSession


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
