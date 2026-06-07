import uuid
from typing import Any, Generic, TypeVar

from fastapi import HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, func, delete as sa_delete, update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase

ModelType = TypeVar("ModelType", bound=DeclarativeBase)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    def __init__(self, model: type[ModelType]):
        self.model = model

    # ── create ──────────────────────────────────────────────────────

    async def create(
        self,
        db: AsyncSession,
        *,
        obj_in: CreateSchemaType,
        flush: bool = False,
    ) -> ModelType:
        obj = self.model(**obj_in.model_dump())
        db.add(obj)
        if flush:
            await db.flush()
        else:
            await db.commit()
            await db.refresh(obj)
        return obj

    # ── get ─────────────────────────────────────────────────────────

    async def get(
        self,
        db: AsyncSession,
        id: uuid.UUID | str,
    ) -> ModelType | None:
        result = await db.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()

    async def get_or_404(
        self,
        db: AsyncSession,
        id: uuid.UUID | str,
        detail: str | None = None,
    ) -> ModelType:
        obj = await self.get(db, id)
        if obj is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=detail or f"{self.model.__name__} not found",
            )
        return obj

    async def get_by(
        self,
        db: AsyncSession,
        **filters: Any,
    ) -> ModelType | None:
        stmt = select(self.model)
        for key, value in filters.items():
            stmt = stmt.where(getattr(self.model, key) == value)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    # ── list ────────────────────────────────────────────────────────

    async def list(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 50,
        **filters: Any,
    ) -> tuple[list[ModelType], int]:
        base = select(self.model)
        for key, value in filters.items():
            base = base.where(getattr(self.model, key) == value)

        total = await db.scalar(select(func.count()).select_from(base.subquery()))

        stmt = base.order_by(self.model.created_at.desc()).offset(skip).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all()), total

    # ── update ──────────────────────────────────────────────────────

    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: ModelType,
        obj_in: UpdateSchemaType | dict[str, Any],
    ) -> ModelType:
        update_data = (
            obj_in.model_dump(exclude_unset=True)
            if isinstance(obj_in, BaseModel)
            else obj_in
        )

        for field, value in update_data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)

        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    # ── delete ──────────────────────────────────────────────────────

    async def delete(
        self,
        db: AsyncSession,
        *,
        id: uuid.UUID | str,
    ) -> int:
        result = await db.execute(
            sa_delete(self.model).where(self.model.id == id)
        )
        await db.commit()
        return result.rowcount

    async def delete_obj(
        self,
        db: AsyncSession,
        *,
        db_obj: ModelType,
    ) -> None:
        await db.delete(db_obj)
        await db.flush()

    # ── helpers ─────────────────────────────────────────────────────

    async def exists(
        self,
        db: AsyncSession,
        id: uuid.UUID | str,
    ) -> bool:
        result = await db.execute(
            select(func.count()).select_from(self.model).where(self.model.id == id)
        )
        return result.scalar() > 0

    async def create_bulk(
        self,
        db: AsyncSession,
        *,
        objs_in: list[CreateSchemaType],
    ) -> list[ModelType]:
        objs = [self.model(**o.model_dump()) for o in objs_in]
        db.add_all(objs)
        await db.flush()
        return objs
