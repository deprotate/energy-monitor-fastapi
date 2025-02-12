from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from api_v1.core.models.Energy import Energy


async def create_energy(session: AsyncSession, energy_data) -> Energy:
    energy = Energy(**energy_data.dict())
    session.add(energy)
    await session.commit()
    await session.refresh(energy)
    return energy


async def get_energy_list(session: AsyncSession) -> list:
    query = select(Energy)
    result = await session.execute(query)
    return list(result.scalars().all())


async def get_energy(session: AsyncSession, energy_id: int) -> Energy | None:
    query = select(Energy).where(Energy.id == energy_id)
    result = await session.execute(query)
    return result.scalars().first()


async def report(session: AsyncSession):
    query = select(
        func.sum(Energy.value).filter(Energy.type == 1),
        func.sum(Energy.value).filter(Energy.type == 2)
    )
    result = await session.execute(query)
    sum_type_1, sum_type_2 = result.fetchone()
    if sum_type_1 or 0 > sum_type_2 or 0:
        return {
            "1": sum_type_1 or 0,
            "2": sum_type_2 or 0,
            "3": sum_type_1 - sum_type_2,
            "4": 0

        }
    else:
        return {
            "1": sum_type_1 or 0,
            "2": sum_type_2 or 0,
            "3": 0,
            "4": sum_type_2 - sum_type_1

        }
