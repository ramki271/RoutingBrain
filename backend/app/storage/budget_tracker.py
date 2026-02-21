from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Optional

import yaml
from redis.asyncio import Redis

from app.core.logging import get_logger
from app.models.policy import BudgetControls

logger = get_logger(__name__)


@dataclass
class ModelPrice:
    input_cost_per_mtok: float
    output_cost_per_mtok: float


TIER_FALLBACK_PRICE_PER_MTOK: Dict[str, float] = {
    "fast_cheap": 0.80,
    "balanced": 3.00,
    "powerful": 15.00,
    "local": 0.0,
}


class BudgetTracker:
    """
    Tracks daily spend in Redis and computes live budget usage percentages.
    Keys are day-scoped and expire after UTC midnight rollover.
    """

    def __init__(self, redis_url: str, models_config_path: str):
        self._redis = Redis.from_url(redis_url, decode_responses=True)
        self._prices = self._load_prices(models_config_path)

    def _load_prices(self, path: str) -> Dict[str, ModelPrice]:
        p = Path(path)
        if not p.exists():
            logger.warning("budget_tracker_models_config_missing", path=path)
            return {}

        try:
            with open(p) as f:
                data = yaml.safe_load(f) or {}
        except Exception as e:
            logger.warning("budget_tracker_models_load_failed", error=str(e))
            return {}

        prices: Dict[str, ModelPrice] = {}
        for m in data.get("models", []):
            model_id = m.get("model_id")
            if not model_id:
                continue
            prices[model_id] = ModelPrice(
                input_cost_per_mtok=float(m.get("input_cost_per_mtok", 0.0)),
                output_cost_per_mtok=float(m.get("output_cost_per_mtok", 0.0)),
            )
        logger.info("budget_tracker_prices_loaded", count=len(prices))
        return prices

    def _date_key(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y%m%d")

    def _seconds_until_midnight_utc(self) -> int:
        now = datetime.now(timezone.utc)
        midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        return int((midnight - now).total_seconds()) + 60

    def _tenant_key(self, tenant_id: str) -> str:
        return f"rb:budget:tenant:{tenant_id}:{self._date_key()}"

    def _user_key(self, tenant_id: str, user_id: str) -> str:
        return f"rb:budget:user:{tenant_id}:{user_id}:{self._date_key()}"

    async def get_budget_pct(
        self,
        tenant_id: str,
        user_id: str,
        controls: BudgetControls,
    ) -> float:
        if not controls.daily_limit_usd_per_tenant and not controls.daily_limit_usd_per_user:
            return 0.0

        t_key = self._tenant_key(tenant_id)
        u_key = self._user_key(tenant_id, user_id)
        try:
            tenant_val, user_val = await self._redis.mget(t_key, u_key)
            tenant_spend = float(tenant_val or 0.0)
            user_spend = float(user_val or 0.0)
        except Exception as e:
            logger.warning("budget_tracker_read_failed", error=str(e))
            return 0.0

        tenant_pct = 0.0
        user_pct = 0.0
        if controls.daily_limit_usd_per_tenant:
            tenant_pct = (tenant_spend / controls.daily_limit_usd_per_tenant) * 100.0
        if controls.daily_limit_usd_per_user:
            user_pct = (user_spend / controls.daily_limit_usd_per_user) * 100.0

        return max(tenant_pct, user_pct)

    async def get_spend(self, tenant_id: str, user_id: str) -> dict:
        """Return current UTC-day spend counters for tenant and user."""
        t_key = self._tenant_key(tenant_id)
        u_key = self._user_key(tenant_id, user_id)
        try:
            tenant_val, user_val = await self._redis.mget(t_key, u_key)
            return {
                "tenant_spend_usd": float(tenant_val or 0.0),
                "user_spend_usd": float(user_val or 0.0),
                "date_key": self._date_key(),
            }
        except Exception as e:
            logger.warning("budget_tracker_read_failed", error=str(e))
            return {
                "tenant_spend_usd": 0.0,
                "user_spend_usd": 0.0,
                "date_key": self._date_key(),
            }

    def estimate_cost_usd(
        self,
        model_id: str,
        prompt_tokens: int,
        completion_tokens: int,
        tier: str,
    ) -> float:
        price = self._prices.get(model_id)
        if price:
            input_cost = (prompt_tokens / 1_000_000) * price.input_cost_per_mtok
            output_cost = (completion_tokens / 1_000_000) * price.output_cost_per_mtok
            return round(input_cost + output_cost, 6)

        fallback = TIER_FALLBACK_PRICE_PER_MTOK.get(tier, 3.0)
        return round(((prompt_tokens + completion_tokens) / 1_000_000) * fallback, 6)

    async def record_spend(
        self,
        tenant_id: str,
        user_id: str,
        amount_usd: float,
    ) -> None:
        if amount_usd <= 0:
            return

        t_key = self._tenant_key(tenant_id)
        u_key = self._user_key(tenant_id, user_id)
        ttl = self._seconds_until_midnight_utc()
        try:
            pipe = self._redis.pipeline(transaction=True)
            pipe.incrbyfloat(t_key, amount_usd)
            pipe.expire(t_key, ttl)
            pipe.incrbyfloat(u_key, amount_usd)
            pipe.expire(u_key, ttl)
            await pipe.execute()
        except Exception as e:
            logger.warning("budget_tracker_write_failed", error=str(e))

    async def health_check(self) -> bool:
        try:
            pong = await self._redis.ping()
            return bool(pong)
        except Exception:
            return False
