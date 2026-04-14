"""Утилиты для теребления с бустами и нормализацией весов."""
import random
from datetime import datetime, timedelta
from models import MAX_BOX_COUNT, BOX_REFILL_HOURS, RarityEnum

BOOSTED_RARITIES = {RarityEnum.EPIC, RarityEnum.LEGENDARY}


async def update_user_boxes(user) -> None:
    now = datetime.utcnow()
    if user.box_count >= MAX_BOX_COUNT:
        user.last_refill_at = now
        return
    refill_hours = user.get_refill_hours()
    elapsed = (now - user.last_refill_at).total_seconds()
    refill_seconds = refill_hours * 3600

    if refill_seconds <= 0:
        return

    new_boxes = int(elapsed // refill_seconds)
    if new_boxes > 0:
        user.box_count = min(MAX_BOX_COUNT, user.box_count + new_boxes)
        user.last_refill_at += timedelta(seconds=new_boxes * refill_seconds)
        if user.box_count >= MAX_BOX_COUNT:
            user.last_refill_at = now
    elif elapsed >= refill_seconds:
        # Страховка: если elapsed >= refill_seconds но int дал 0
        user.box_count = min(MAX_BOX_COUNT, user.box_count + 1)
        user.last_refill_at = now


def get_time_until_next_box(last_refill_at: datetime, refill_hours: int = BOX_REFILL_HOURS) -> tuple[int, int]:
    now = datetime.utcnow()
    elapsed = (now - last_refill_at).total_seconds()
    refill_seconds = refill_hours * 3600

    if refill_seconds <= 0:
        return 0, 0

    remaining = refill_seconds - elapsed
    if remaining <= 0:
        return 0, 0
    return int(remaining // 3600), int((remaining % 3600) // 60)


def get_weighted_random_item(items: list, multiplier: float = 1.0):
    """
    random.choices с нормализацией весов при бусте.
    """
    if not items:
        return None

    if multiplier <= 1.0:
        weights = [item.drop_chance for item in items]
    else:
        boosted_total = sum(it.drop_chance for it in items if it.rarity in BOOSTED_RARITIES)
        normal_total = sum(it.drop_chance for it in items if it.rarity not in BOOSTED_RARITIES)
        original_total = boosted_total + normal_total

        if original_total <= 0 or boosted_total <= 0:
            weights = [item.drop_chance for item in items]
        else:
            new_boosted_total = boosted_total * multiplier
            if new_boosted_total >= original_total * 0.95:
                new_boosted_total = original_total * 0.5
            new_normal_total = original_total - new_boosted_total
            normal_scale = new_normal_total / normal_total if normal_total > 0 else 1.0
            boosted_scale = new_boosted_total / boosted_total if boosted_total > 0 else 1.0

            weights = []
            for item in items:
                if item.rarity in BOOSTED_RARITIES:
                    weights.append(item.drop_chance * boosted_scale)
                else:
                    weights.append(item.drop_chance * normal_scale)

    total = sum(weights)
    if total <= 0:
        return random.choice(items)
    return random.choices(items, weights=weights, k=1)[0]