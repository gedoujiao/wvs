from pydantic import BaseModel, HttpUrl
from datetime import datetime
from typing import List, Optional

class ScanTaskCreate(BaseModel):
    url: HttpUrl

class ScanTaskResponse(BaseModel):
    id: str
    url: str
    status: str
    vulnerabilities_count: int
    created_at: datetime
    completed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class VulnerabilityResponse(BaseModel):
    id: str
    type: str
    payload: str
    location: str
    description: str
    severity: str
    
    class Config:
        from_attributes = True

class ScanReportResponse(BaseModel):
    id: str
    url: str
    status: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    vulnerabilities: List[VulnerabilityResponse]
