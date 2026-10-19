import json
from pydantic import BaseModel, ConfigDict, Field


class EstimateArgs(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)
    input_mb: float = Field(gt=0, le=1000)
    bandwidth_mbps: float = Field(gt=0, le=100000)
    queue_ms: float = Field(ge=0, le=100000)
    service_ms: float = Field(gt=0, le=100000)
    deadline_ms: float = Field(gt=0, le=100000)


class SearchArgs(BaseModel):
    model_config = ConfigDict(extra='forbid')
    query: str = Field(min_length=1, max_length=2000)


class ToolExecutor:
    def __init__(self, retriever):
        self.retriever = retriever
        self.schemas = [
            {'type': 'function', 'function': {'name': 'estimate_offload', 'description': 'Estimate single-node upload + FIFO queue + service latency; no actual task dispatch.', 'parameters': EstimateArgs.model_json_schema()}},
            {'type': 'function', 'function': {'name': 'search_knowledge', 'description': 'Retrieve vehicular edge computing documentation.', 'parameters': SearchArgs.model_json_schema()}},
        ]

    def execute(self, name, arguments):
        try:
            if name == 'estimate_offload':
                a = EstimateArgs.model_validate(arguments)
                upload_ms = a.input_mb * 8 / a.bandwidth_mbps * 1000
                latency = upload_ms + a.queue_ms + a.service_ms
                return {'ok': True, 'estimated_ms': latency, 'upload_ms': upload_ms,
                        'deadline_met': latency <= a.deadline_ms, 'assumption': 'serial upload, FIFO queue, fixed service time'}
            if name == 'search_knowledge':
                a = SearchArgs.model_validate(arguments)
                return {'ok': True, 'matches': self.retriever.search(a.query)}
            return {'ok': False, 'error': 'unknown_tool'}
        except (ValueError, TypeError) as error:
            return {'ok': False, 'error': str(error)[:500]}

    def message(self, call):
        try:
            arguments = json.loads(call['function']['arguments'])
        except (KeyError, ValueError, TypeError):
            arguments = None
        result = self.execute(call['function']['name'], arguments)
        return {'role': 'tool', 'tool_call_id': call['id'], 'content': json.dumps(result, ensure_ascii=False)}, result
