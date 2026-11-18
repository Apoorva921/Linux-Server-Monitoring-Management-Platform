from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class LogEntryIngest(BaseModel):
    timestamp: Optional[datetime] = None
    severity: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    source: str = Field(default="syslog", max_length=128)
    hostname: str = Field(default="", max_length=255)
    message: str = Field(..., min_length=1, max_length=4096)
    raw_line: str = Field(default="", max_length=4096)


class LogBatchIngestRequest(BaseModel):
    server_id: Optional[str] = Field(default=None, max_length=36)
    entries: List[LogEntryIngest] = Field(..., min_length=1, max_length=500)
    is_demo: Optional[bool] = None


class LogBatchIngestResponse(BaseModel):
    status: str = "accepted"
    ingested_count: int
    server_id: str


class LogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    server_id: str
    server_name: str = ""
    timestamp: datetime
    severity: str
    source: str
    hostname: str
    message: str
    raw_line: str
    is_demo: bool
    created_at: datetime

