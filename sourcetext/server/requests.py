from fastapi_camelcase import CamelModel


class PingResponse(CamelModel):
    message: str
    document_count: int
