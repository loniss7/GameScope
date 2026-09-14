import re
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import (
    ExternalGameId,
    GameRatingRecord,
    GameRecord,
    GenreRecord,
    PlatformRecord,
)
from app.schemas import Game, GamePrice, GameRating, GameSystemRequirements


def _slug(title: str, external_ids: dict[str, str]) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", title.casefold()).strip("-") or "game"
    external_suffix = "-".join(
        f"{provider}-{external_id}"
        for provider, external_id in sorted(external_ids.items())
    )
    return f"{base[:250]}-{external_suffix}"[:350] if external_suffix else base[:350]


def to_game_schema(record: GameRecord) -> Game:
    return Game(
        id=str(record.id),
        title=record.title,
        description=record.description,
        release_date=record.release_date,
        developers=list(record.developers or []),
        publishers=list(record.publishers or []),
        genres=[genre.name for genre in record.genres],
        categories=list(record.categories or []),
        platforms=[platform.name for platform in record.platforms],
        ratings=[
            GameRating(
                source=rating.source,
                score=rating.score,
                max_score=rating.max_score,
                rating_count=rating.rating_count,
            )
            for rating in record.ratings
        ],
        price=GamePrice.model_validate(record.price) if record.price else None,
        is_free=record.is_free,
        achievement_count=record.achievement_count,
        system_requirements=(
            GameSystemRequirements.model_validate(record.system_requirements)
            if record.system_requirements
            else None
        ),
        image_url=record.image_url,
        external_ids={
            external.provider: external.external_id for external in record.external_ids
        },
    )


class GameRepository:
    """Persistence operations for normalized games; transaction ownership stays outside."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _loaded_query():
        return select(GameRecord).options(
            selectinload(GameRecord.external_ids),
            selectinload(GameRecord.ratings),
            selectinload(GameRecord.genres),
            selectinload(GameRecord.platforms),
        )

    async def get_by_id(self, game_id: int) -> Game | None:
        record = await self._session.scalar(
            self._loaded_query().where(GameRecord.id == game_id)
        )
        return to_game_schema(record) if record is not None else None

    async def get_record_by_id(self, game_id: int) -> GameRecord | None:
        return await self._session.scalar(
            self._loaded_query().where(GameRecord.id == game_id)
        )

    async def get_by_external_id(self, provider: str, external_id: str) -> Game | None:
        query = (
            self._loaded_query()
            .join(GameRecord.external_ids)
            .where(
                ExternalGameId.provider == provider,
                ExternalGameId.external_id == external_id,
            )
        )
        record = await self._session.scalar(query)
        return to_game_schema(record) if record is not None else None

    async def search(self, query: str, *, limit: int = 20) -> list[Game]:
        normalized_limit = max(1, min(limit, 100))
        statement = (
            self._loaded_query()
            .where(GameRecord.title.ilike(f"%{query.strip()}%"))
            .order_by(GameRecord.title)
            .limit(normalized_limit)
        )
        records = (await self._session.scalars(statement)).all()
        return [to_game_schema(record) for record in records]

    async def save(
        self,
        game: Game,
        *,
        synced_at: datetime | None = None,
        preserve_existing: bool = False,
    ) -> Game:
        record: GameRecord | None = None
        for provider, external_id in game.external_ids.items():
            record = await self._session.scalar(
                self._loaded_query()
                .join(GameRecord.external_ids)
                .where(
                    ExternalGameId.provider == provider,
                    ExternalGameId.external_id == external_id,
                )
            )
            if record is not None:
                break

        if record is None and game.id and game.id.isdigit():
            record = await self.get_record_by_id(int(game.id))

        if record is None:
            record = GameRecord(
                title=game.title,
                slug=_slug(game.title, game.external_ids),
                external_ids=[],
                ratings=[],
                genres=[],
                platforms=[],
            )
            self._session.add(record)

        record.title = game.title or record.title
        record.slug = _slug(game.title, game.external_ids)
        if game.description is not None or not preserve_existing:
            record.description = game.description
        if game.release_date is not None or not preserve_existing:
            record.release_date = game.release_date
        if game.developers or not preserve_existing:
            record.developers = list(game.developers)
        if game.publishers or not preserve_existing:
            record.publishers = list(game.publishers)
        if game.categories or not preserve_existing:
            record.categories = list(game.categories)
        if game.price is not None or not preserve_existing:
            record.price = game.price.model_dump(mode="json") if game.price else None
        if game.is_free is not None or not preserve_existing:
            record.is_free = game.is_free
        if game.achievement_count is not None or not preserve_existing:
            record.achievement_count = game.achievement_count
        if game.system_requirements is not None or not preserve_existing:
            record.system_requirements = (
                game.system_requirements.model_dump(mode="json")
                if game.system_requirements
                else None
            )
        if game.image_url is not None or not preserve_existing:
            record.image_url = game.image_url
        if synced_at is not None:
            record.last_synced_at = synced_at

        for provider, external_id in game.external_ids.items():
            existing_id = await self._session.scalar(
                select(ExternalGameId).where(
                    ExternalGameId.provider == provider,
                    ExternalGameId.external_id == external_id,
                )
            )
            if existing_id is not None and existing_id.game_id != record.id:
                raise ValueError(
                    "External provider ID is already linked to a different game."
                )
            if existing_id is None:
                record.external_ids.append(
                    ExternalGameId(provider=provider, external_id=external_id)
                )

        if game.genres or not preserve_existing:
            record.genres = [
                await self._get_or_create_genre(name) for name in game.genres
            ]
        if game.platforms or not preserve_existing:
            record.platforms = [
                await self._get_or_create_platform(name) for name in game.platforms
            ]
        if game.ratings or not preserve_existing:
            record.ratings.clear()
            record.ratings.extend(
                GameRatingRecord(
                    source=rating.source,
                    score=rating.score,
                    max_score=rating.max_score,
                    rating_count=rating.rating_count,
                )
                for rating in game.ratings
            )
        await self._session.flush()
        return await self.get_by_id(record.id)  # type: ignore[return-value]

    async def _get_or_create_genre(self, name: str) -> GenreRecord:
        existing = await self._session.scalar(
            select(GenreRecord).where(func.lower(GenreRecord.name) == name.casefold())
        )
        if existing is not None:
            return existing
        created = GenreRecord(name=name)
        self._session.add(created)
        await self._session.flush()
        return created

    async def _get_or_create_platform(self, name: str) -> PlatformRecord:
        existing = await self._session.scalar(
            select(PlatformRecord).where(
                func.lower(PlatformRecord.name) == name.casefold()
            )
        )
        if existing is not None:
            return existing
        created = PlatformRecord(name=name)
        self._session.add(created)
        await self._session.flush()
        return created
