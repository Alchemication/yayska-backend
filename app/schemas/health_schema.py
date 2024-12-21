from pydantic import BaseModel


class HealthCheck(BaseModel):
    status: str
    database_status: str 