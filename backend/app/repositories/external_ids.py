from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ExternalGameId


class ExternalIdRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_game_id(self, provider: str, external_id: str) -> int | None:
        return await self._session.scalar(
            select(ExternalGameId.game_id).where(
                ExternalGameId.provider == provider,
                ExternalGameId.external_id == external_id,
            )
        )

    async def list_for_game(self, game_id: int) -> list[ExternalGameId]:
        return list(
            (
                await self._session.scalars(
                    select(ExternalGameId)
                    .where(ExternalGameId.game_id == game_id)
                    .order_by(ExternalGameId.provider)
                )
            ).all()
        )
