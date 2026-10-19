from contextlib import asynccontextmanager
import asyncio
import hmac
import json
from fastapi import FastAPI, Header, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import httpx
from .config import Settings
from .service import AgentService, ConflictError


class Query(BaseModel):
    question: str = Field(min_length=1, max_length=8000)
    session_id: str = Field(default='default', min_length=1, max_length=100)
    request_id: str | None = Field(default=None, min_length=1, max_length=100)
    use_cache: bool = True


def create_app(settings=None):
    settings = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(app):
        app.state.service = AgentService(settings)
        yield

    app = FastAPI(title='Vehicular Agent Infra', version='0.1.0', lifespan=lifespan)

    def auth(authorization: str = Header(default='')):
        if settings.api_key and not hmac.compare_digest(authorization, 'Bearer ' + settings.api_key):
            raise HTTPException(401, 'Invalid API key')

    @app.get('/health')
    def health():
        return {'status': 'ok', 'backend': settings.backend, 'model': settings.model}

    @app.get('/metrics', dependencies=[Depends(auth)])
    def metrics():
        return app.state.service.counters

    async def execute(query):
        try:
            return await app.state.service.run(**query.model_dump())
        except ConflictError as error:
            raise HTTPException(409, str(error)) from error
        except asyncio.TimeoutError as error:
            raise HTTPException(504, 'Request deadline exceeded') from error
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as error:
            raise HTTPException(502, 'Backend or protocol error; check backend logs') from error

    @app.post('/v1/agent', dependencies=[Depends(auth)])
    async def agent(query: Query):
        return await execute(query)

    @app.post('/v1/agent/events', dependencies=[Depends(auth)])
    async def events(query: Query):
        # Lifecycle SSE, not token-level streaming. Direct-model benchmark measures TTFT.
        async def generate():
            yield 'event: accepted\ndata: {}\n\n'
            try:
                result = await execute(query)
                for item in result['trace']:
                    yield 'event: trace\ndata: ' + json.dumps(item, ensure_ascii=False) + '\n\n'
                yield 'event: result\ndata: ' + json.dumps(result, ensure_ascii=False) + '\n\n'
            except HTTPException as error:
                yield 'event: error\ndata: ' + json.dumps({'status': error.status_code, 'detail': error.detail}) + '\n\n'
        return StreamingResponse(generate(), media_type='text/event-stream')

    return app
