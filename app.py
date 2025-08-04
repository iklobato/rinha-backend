import asyncio
import os
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Tuple
from uuid import uuid4

import asyncpg
import redis.asyncio as redis
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.responses import JSONResponse
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel, Field, field_validator
import uvicorn
import orjson
from functools import lru_cache


class Settings:
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/rinha")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    DATABASE_POOL_MIN_SIZE: int = int(os.getenv("DATABASE_POOL_MIN_SIZE", "3"))
    DATABASE_POOL_MAX_SIZE: int = int(os.getenv("DATABASE_POOL_MAX_SIZE", "15"))
    REDIS_POOL_SIZE: int = int(os.getenv("REDIS_POOL_SIZE", "8"))
    CACHE_TTL: int = int(os.getenv("CACHE_TTL", "300"))
    CONNECTION_TIMEOUT: int = int(os.getenv("CONNECTION_TIMEOUT", "15"))
    COMMAND_TIMEOUT: int = int(os.getenv("COMMAND_TIMEOUT", "5"))
    MAX_CACHE_KEYS: int = int(os.getenv("MAX_CACHE_KEYS", "500"))


settings = Settings()


class TransactionRequest(BaseModel):
    model_config = {
        "validate_assignment": False,
        "extra": "forbid",
        "frozen": True
    }
    
    valor: int = Field(..., gt=0, description="Transaction value in cents")
    tipo: str = Field(..., pattern="^[cd]$", description="Transaction type: 'c' for credit, 'd' for debit")
    descricao: str = Field(..., min_length=1, max_length=10, description="Transaction description")

    @field_validator('valor')
    @classmethod
    def validate_valor(cls, v):
        if not isinstance(v, int) or v <= 0:
            raise ValueError('valor must be a positive integer')
        return v


class TransactionResponse(BaseModel):
    model_config = {"frozen": True, "extra": "forbid"}
    limite: int
    saldo: int


class BalanceInfo(BaseModel):
    model_config = {"frozen": True, "extra": "forbid"}
    total: int
    data_extrato: datetime
    limite: int


class TransactionInfo(BaseModel):
    model_config = {"frozen": True, "extra": "forbid"}
    valor: int
    tipo: str
    descricao: str
    realizada_em: datetime


class StatementResponse(BaseModel):
    model_config = {"frozen": True, "extra": "forbid"}
    saldo: BalanceInfo
    ultimas_transacoes: List[TransactionInfo]


class DatabaseManager:
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
        self._prepared_statements: Dict[str, str] = {}
    
    async def initialize(self):
        max_retries = 3
        retry_delay = 1
        
        for attempt in range(max_retries):
            try:
                self.pool = await asyncpg.create_pool(
                    settings.DATABASE_URL,
                    min_size=settings.DATABASE_POOL_MIN_SIZE,
                    max_size=settings.DATABASE_POOL_MAX_SIZE,
                    command_timeout=settings.COMMAND_TIMEOUT,
                    server_settings={
                        'jit': 'off',
                        'work_mem': '1MB',
                        'maintenance_work_mem': '2MB'
                    }
                )
                return
            except Exception as e:
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    raise
    
    async def _setup_connection(self, conn: asyncpg.Connection):
        """Setup connection with prepared statements"""
        try:
            # Prepare all frequently used statements
            self._prepared_statements['get_client'] = await conn.prepare(
                "SELECT saldo, limite FROM clientes WHERE id = $1"
            )
            self._prepared_statements['get_client_for_update'] = await conn.prepare(
                "SELECT saldo, limite FROM clientes WHERE id = $1 FOR UPDATE"
            )
            self._prepared_statements['update_client_balance'] = await conn.prepare(
                "UPDATE clientes SET saldo = $1 WHERE id = $2"
            )
            self._prepared_statements['insert_transaction'] = await conn.prepare(
                "INSERT INTO transacoes (cliente_id, valor, tipo, descricao, realizada_em) VALUES ($1, $2, $3, $4, $5)"
            )
            self._prepared_statements['get_transactions'] = await conn.prepare(
                "SELECT valor, tipo, descricao, realizada_em FROM transacoes WHERE cliente_id = $1 ORDER BY realizada_em DESC LIMIT 10"
            )
        except Exception as e:
            raise
    
    async def close(self):
        if self.pool:
            await self.pool.close()
    
    async def execute_transaction(self, client_id: int, valor: int, tipo: str, descricao: str) -> Dict[str, Any]:
        try:
            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    client_record = await conn.fetchrow(
                        "SELECT saldo, limite FROM clientes WHERE id = $1 FOR UPDATE",
                        client_id
                    )
                    
                    if not client_record:
                        raise HTTPException(status_code=404, detail="Client not found")
                    
                    current_balance = client_record['saldo']
                    limit = client_record['limite']
                    
                    new_balance = current_balance + (valor if tipo == 'c' else -valor)
                    
                    if tipo == 'd' and new_balance < -limit:
                        raise HTTPException(status_code=422, detail="Insufficient balance")
                    
                    await conn.execute(
                        "UPDATE clientes SET saldo = $1 WHERE id = $2",
                        new_balance, client_id
                    )
                    await conn.execute(
                        "INSERT INTO transacoes (cliente_id, valor, tipo, descricao, realizada_em) VALUES ($1, $2, $3, $4, $5)",
                        client_id, valor, tipo, descricao, datetime.now(timezone.utc)
                    )
                    
                    return {"limite": limit, "saldo": new_balance}
        except Exception as e:
            raise
    
    async def get_statement(self, client_id: int) -> Dict[str, Any]:
        async with self.pool.acquire() as conn:
            client_record = await conn.fetchrow(
                "SELECT saldo, limite FROM clientes WHERE id = $1",
                client_id
            )
            
            if not client_record:
                raise HTTPException(status_code=404, detail="Client not found")
            
            transactions = await conn.fetch(
                "SELECT valor, tipo, descricao, realizada_em FROM transacoes WHERE cliente_id = $1 ORDER BY realizada_em DESC LIMIT 10",
                client_id
            )
            
            return {
                "saldo": {
                    "total": client_record['saldo'],
                    "data_extrato": datetime.now(timezone.utc),
                    "limite": client_record['limite']
                },
                "ultimas_transacoes": [
                    {
                        "valor": t['valor'],
                        "tipo": t['tipo'],
                        "descricao": t['descricao'],
                        "realizada_em": t['realizada_em']
                    }
                    for t in transactions
                ]
            }


class CacheManager:
    def __init__(self):
        self.redis: Optional[redis.Redis] = None
        self._cache_hits = 0
        self._cache_misses = 0
    
    async def initialize(self):
        self.redis = redis.from_url(
            settings.REDIS_URL,
            max_connections=settings.REDIS_POOL_SIZE,
            decode_responses=True,
            socket_timeout=settings.CONNECTION_TIMEOUT,
            socket_connect_timeout=settings.CONNECTION_TIMEOUT,
            socket_keepalive=True,
            retry_on_timeout=True,
            health_check_interval=30
        )
    
    async def close(self):
        if self.redis:
            await self.redis.close()
    
    async def get_client_balance(self, client_id: int) -> Optional[Dict[str, Any]]:
        cache_key = f"balance:{client_id}"
        cached_data = await self.redis.get(cache_key)
        if cached_data:
            self._cache_hits += 1
            return orjson.loads(cached_data)
        self._cache_misses += 1
        return None
    
    async def set_client_balance(self, client_id: int, balance_data: Dict[str, Any]):
        cache_key = f"balance:{client_id}"
        serialized_data = orjson.dumps(balance_data, default=str)
        await self.redis.setex(cache_key, settings.CACHE_TTL, serialized_data)
    
    async def get_statement_cache(self, client_id: int) -> Optional[Dict[str, Any]]:
        cache_key = f"statement:{client_id}"
        cached_data = await self.redis.get(cache_key)
        if cached_data:
            self._cache_hits += 1
            return orjson.loads(cached_data)
        self._cache_misses += 1
        return None
    
    async def set_statement_cache(self, client_id: int, statement_data: Dict[str, Any]):
        cache_key = f"statement:{client_id}"
        serialized_data = orjson.dumps(statement_data, default=str)
        await self.redis.setex(cache_key, settings.CACHE_TTL * 2, serialized_data)
    
    async def invalidate_client_cache(self, client_id: int):
        balance_key = f"balance:{client_id}"
        await self.redis.delete(balance_key)
    
    async def invalidate_statement_cache(self, client_id: int):
        statement_key = f"statement:{client_id}"
        await self.redis.delete(statement_key)
    
    def get_cache_stats(self) -> Dict[str, int]:
        total = self._cache_hits + self._cache_misses
        hit_rate = (self._cache_hits / total * 100) if total > 0 else 0
        return {
            "hits": self._cache_hits,
            "misses": self._cache_misses,
            "hit_rate": round(hit_rate, 2)
        }


db_manager = DatabaseManager()
cache_manager = CacheManager()


@lru_cache(maxsize=1)
def get_db_manager() -> DatabaseManager:
    return db_manager


@lru_cache(maxsize=1)
def get_cache_manager() -> CacheManager:
    return cache_manager


from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await asyncio.gather(
            db_manager.initialize(),
            cache_manager.initialize()
        )
    except Exception as e:
        raise
    
    yield
    
    await asyncio.gather(
        db_manager.close(),
        cache_manager.close()
    )


app = FastAPI(
    title="Ultra-Performance Rinha Backend",
    description="Ultra-optimized backend for maximum performance on constrained hardware",
    version="3.0.0",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url=None
)

app.add_middleware(GZipMiddleware, minimum_size=500)


# Optimized API Endpoints
@app.post("/clientes/{client_id}/transacoes", response_model=TransactionResponse)
async def create_transaction(
    client_id: int,
    transaction: TransactionRequest,
    db: DatabaseManager = Depends(get_db_manager),
    cache: CacheManager = Depends(get_cache_manager)
):
    try:
        result = await db.execute_transaction(
            client_id, transaction.valor, transaction.tipo, transaction.descricao
        )
        
        await cache.invalidate_client_cache(client_id)
        await cache.invalidate_statement_cache(client_id)
        
        return TransactionResponse(**result)
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/clientes/{client_id}/extrato", response_model=StatementResponse)
async def get_statement(
    client_id: int,
    db: DatabaseManager = Depends(get_db_manager),
    cache: CacheManager = Depends(get_cache_manager)
):
    try:
        cached_statement = await cache.get_statement_cache(client_id)
        if cached_statement:
            return StatementResponse(**cached_statement)
        
        statement_data = await db.get_statement(client_id)
        
        await cache.set_statement_cache(client_id, statement_data)
        
        return StatementResponse(**statement_data)
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/health")
async def health_check():
    cache_stats = cache_manager.get_cache_stats()
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc),
        "cache_stats": cache_stats
    }


@app.get("/metrics")
async def metrics():
    return {
        "database_pool_size": db_manager.pool.get_size() if db_manager.pool else 0,
        "cache_stats": cache_manager.get_cache_stats(),
        "memory_usage": "optimized"
    }


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        media_type="application/json"
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
        media_type="application/json"
    )


if __name__ == "__main__":
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        workers=1,
        loop="asyncio",
        access_log=False,
        log_level="error",
        limit_concurrency=50,
        limit_max_requests=500,
        timeout_keep_alive=15,
        timeout_graceful_shutdown=5,
        backlog=20,
        use_colors=False
    )
