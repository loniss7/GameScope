from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import GameSummaryRecord
from app.schemas import GameSummary, SummarySentiment


def to_summary_schema(record: GameSummaryRecord) -> GameSummary:
    return GameSummary(
        summary=record.summary,
        pros=list(record.pros or []),
        cons=list(record.cons or []),
        sentiment=SummarySentiment.model_validate(record.sentiment or {}),
        reviews_analyzed=record.reviews_analyzed,
        reviews_total=record.reviews_total,
        model=record.model,
        source=record.source,
        language=record.language,
        generated_at=record.generated_at,
    )


class GameSummaryRepository:
    """Persistence operations for generated game summaries."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_latest(self, game_id: int) -> GameSummary | None:
        record = await self._session.scalar(
            select(GameSummaryRecord)
            .where(GameSummaryRecord.game_id == game_id)
            .order_by(GameSummaryRecord.updated_at.desc(), GameSummaryRecord.id.desc())
            .limit(1)
        )
        return to_summary_schema(record) if record is not None else None

    async def get_by_snapshot(
        self,
        game_id: int,
        *,
        source: str,
        model: str,
        language: str,
        reviews_hash: str,
    ) -> GameSummary | None:
        record = await self._session.scalar(
            select(GameSummaryRecord).where(
                GameSummaryRecord.game_id == game_id,
                GameSummaryRecord.source == source,
                GameSummaryRecord.model == model,
                GameSummaryRecord.language == language,
                GameSummaryRecord.reviews_hash == reviews_hash,
            )
        )
        return to_summary_schema(record) if record is not None else None

    async def save(
        self,
        game_id: int,
        summary: GameSummary,
        *,
        reviews_hash: str,
    ) -> GameSummary:
        record = await self._session.scalar(
            select(GameSummaryRecord).where(
                GameSummaryRecord.game_id == game_id,
                GameSummaryRecord.source == summary.source,
                GameSummaryRecord.model == summary.model,
                GameSummaryRecord.language == summary.language,
                GameSummaryRecord.reviews_hash == reviews_hash,
            )
        )
        values = {
            "source": summary.source,
            "model": summary.model,
            "language": summary.language,
            "reviews_hash": reviews_hash,
            "summary": summary.summary,
            "pros": list(summary.pros),
            "cons": list(summary.cons),
            "sentiment": summary.sentiment.model_dump(mode="json"),
            "reviews_analyzed": summary.reviews_analyzed,
            "reviews_total": summary.reviews_total,
            "generated_at": summary.generated_at or datetime.now(timezone.utc),
        }
        if record is None:
            record = GameSummaryRecord(game_id=game_id, **values)
            self._session.add(record)
        else:
            for field, value in values.items():
                setattr(record, field, value)
        await self._session.flush()
        return to_summary_schema(record)
