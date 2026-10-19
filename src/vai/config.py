from dataclasses import dataclass
from pathlib import Path
import os


@dataclass(frozen=True)
class Settings:
    backend: str = 'mock'
    base_url: str = 'http://127.0.0.1:8001/v1'
    model: str = 'local-model'
    backend_key: str = ''
    api_key: str = ''
    database: str = 'runtime/agent.sqlite'
    documents: str = str(Path(__file__).parent / 'data')
    embedding_model: str = ''
    max_concurrency: int = 4
    timeout_s: float = 45.0
    cache_ttl_s: float = 60.0
    max_tool_rounds: int = 3

    def __post_init__(self):
        if self.backend not in {'mock', 'openai'}:
            raise ValueError('BACKEND must be mock or openai')
        if self.max_concurrency < 1 or self.timeout_s <= 0 or self.max_tool_rounds < 1:
            raise ValueError('Invalid resource limit')

    @classmethod
    def from_env(cls):
        return cls(backend=os.getenv('BACKEND', 'mock'),
                   base_url=os.getenv('LLM_BASE_URL', 'http://127.0.0.1:8001/v1').rstrip('/'),
                   model=os.getenv('LLM_MODEL', 'local-model'),
                   backend_key=os.getenv('LLM_API_KEY', ''), api_key=os.getenv('API_KEY', ''),
                   database=os.getenv('DATABASE', 'runtime/agent.sqlite'),
                   documents=os.getenv('DOCUMENTS', str(Path(__file__).parent / 'data')),
                   embedding_model=os.getenv('EMBEDDING_MODEL', ''),
                   max_concurrency=int(os.getenv('MAX_CONCURRENCY', '4')),
                   timeout_s=float(os.getenv('REQUEST_TIMEOUT_S', '45')),
                   cache_ttl_s=float(os.getenv('CACHE_TTL_S', '60')),
                   max_tool_rounds=int(os.getenv('MAX_TOOL_ROUNDS', '3')))
