from sqlalchemy import text

from app.infrastructure.database.session import get_engine


async def database_is_ready() -> bool:
    try:
        async with get_engine().connect() as connection:
            await connection.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001 - readiness must contain all driver/connectivity failures.
        return False
    return True
