"""
Las pruebas corren contra una base PostgreSQL real (DATABASE_URL), ya migrada y con los datos de
desarrollo (`python -m app.arranque` + `python -m app.db.seeds.seeder`), igual que en CI.
Cada prueba que escribe lo hace dentro de una transacción que se descarta al final.
"""
import pytest
from httpx import ASGITransport, AsyncClient

from app.db.session import AsyncSessionLocal
from main import app


@pytest.fixture
async def db():
    async with AsyncSessionLocal() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture
async def tx():
    """
    Cliente cuyas peticiones comparten una sesión dentro de una transacción que se revierte al final:
    los `commit` de los endpoints solo liberan un savepoint. Entrega (cliente, sesión).
    """
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.db.session import engine, get_db

    async with engine.connect() as conn:
        trans = await conn.begin()
        session = AsyncSession(bind=conn, join_transaction_mode="create_savepoint", expire_on_commit=False)

        async def _get_db():
            yield session

        app.dependency_overrides[get_db] = _get_db
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                yield c, session
        finally:
            app.dependency_overrides.pop(get_db, None)
            await session.close()
            await trans.rollback()
