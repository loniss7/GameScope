from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import GameRatingRecord


class RatingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_game(self, game_id: int) -> list[GameRatingRecord]:
        return list(
            (
                await self._session.scalars(
                    select(GameRatingRecord)
                    .where(GameRatingRecord.game_id == game_id)
                    .order_by(GameRatingRecord.source)
                )
            ).all()
        )
