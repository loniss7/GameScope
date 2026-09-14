from datetime import date, datetime

from sqlalchemy import (
    JSON,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

game_genres = Table(
    "game_genres",
    Base.metadata,
    Column("game_id", ForeignKey("games.id", ondelete="CASCADE"), primary_key=True),
    Column("genre_id", ForeignKey("genres.id", ondelete="CASCADE"), primary_key=True),
)

game_platforms = Table(
    "game_platforms",
    Base.metadata,
    Column("game_id", ForeignKey("games.id", ondelete="CASCADE"), primary_key=True),
    Column(
        "platform_id", ForeignKey("platforms.id", ondelete="CASCADE"), primary_key=True
    ),
)


class GameRecord(Base):
    __tablename__ = "games"
    __table_args__ = (Index("ix_games_title", "title"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    slug: Mapped[str] = mapped_column(String(350), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    release_date: Mapped[date | None] = mapped_column(Date)
    developers: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    publishers: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    categories: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    price: Mapped[dict | None] = mapped_column(JSON)
    is_free: Mapped[bool | None] = mapped_column()
    achievement_count: Mapped[int | None] = mapped_column(Integer)
    system_requirements: Mapped[dict | None] = mapped_column(JSON)
    image_url: Mapped[str | None] = mapped_column(Text)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    external_ids: Mapped[list["ExternalGameId"]] = relationship(
        back_populates="game", cascade="all, delete-orphan", lazy="selectin"
    )
    ratings: Mapped[list["GameRatingRecord"]] = relationship(
        back_populates="game", cascade="all, delete-orphan", lazy="selectin"
    )
    genres: Mapped[list["GenreRecord"]] = relationship(
        secondary=game_genres, back_populates="games", lazy="selectin"
    )
    platforms: Mapped[list["PlatformRecord"]] = relationship(
        secondary=game_platforms, back_populates="games", lazy="selectin"
    )


class ExternalGameId(Base):
    __tablename__ = "game_external_ids"
    __table_args__ = (
        UniqueConstraint(
            "provider", "external_id", name="uq_game_external_provider_id"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    game_id: Mapped[int] = mapped_column(
        ForeignKey("games.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    external_id: Mapped[str] = mapped_column(String(120), nullable=False)
    external_url: Mapped[str | None] = mapped_column(Text)
    game: Mapped[GameRecord] = relationship(back_populates="external_ids")


class GameRatingRecord(Base):
    __tablename__ = "game_ratings"
    __table_args__ = (
        UniqueConstraint("game_id", "source", name="uq_game_rating_source"),
        Index("ix_game_ratings_game_id", "game_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    game_id: Mapped[int] = mapped_column(
        ForeignKey("games.id", ondelete="CASCADE"), nullable=False
    )
    source: Mapped[str] = mapped_column(String(80), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    max_score: Mapped[float] = mapped_column(Float, nullable=False)
    rating_count: Mapped[int | None] = mapped_column(Integer)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    game: Mapped[GameRecord] = relationship(back_populates="ratings")


class GenreRecord(Base):
    __tablename__ = "genres"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    games: Mapped[list[GameRecord]] = relationship(
        secondary=game_genres, back_populates="genres"
    )


class PlatformRecord(Base):
    __tablename__ = "platforms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    games: Mapped[list[GameRecord]] = relationship(
        secondary=game_platforms, back_populates="platforms"
    )
