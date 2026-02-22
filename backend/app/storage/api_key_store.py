from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ApiKeyAuthMeta:
    tenant_id: str
    user_id: str
    department: str = "rd"
    allowed_departments: Optional[list[str]] = None


class ApiKeyStore:
    """Database-backed API key validation against public.api_keys + public.tenants."""

    def __init__(self, engine: AsyncEngine):
        self._engine = engine

    @staticmethod
    def hash_key(raw_key: str) -> str:
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    async def resolve(self, raw_key: str) -> Optional[ApiKeyAuthMeta]:
        key_hash = self.hash_key(raw_key)
        query = text(
            """
            select
              t.name as tenant_name,
              coalesce(k.user_id, 'unknown') as user_id
            from public.api_keys k
            join public.tenants t on t.id = k.tenant_id
            where k.key_hash = :key_hash
              and k.active = true
              and t.status = 'active'
            limit 1
            """
        )
        try:
            async with self._engine.connect() as conn:
                row = (await conn.execute(query, {"key_hash": key_hash})).mappings().first()
                if not row:
                    return None
                return ApiKeyAuthMeta(
                    tenant_id=str(row["tenant_name"]),
                    user_id=str(row["user_id"]),
                    department="rd",
                    allowed_departments=None,
                )
        except Exception as e:
            logger.warning("api_key_store_query_failed", error=str(e))
            return None

    async def health_check(self) -> bool:
        try:
            async with self._engine.connect() as conn:
                await conn.execute(text("select 1"))
            return True
        except Exception:
            return False
