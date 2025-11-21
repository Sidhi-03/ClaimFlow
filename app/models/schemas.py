from pydantic import BaseModel
from typing import List, Dict, Any

class ProcessedDocument(BaseModel):
    file_name: str
    document_type: str
    extracted_data: Dict[str, Any]
    raw_text: str

class ValidationResult(BaseModel):
    missing_documents: List[str]
    discrepancies: List[str]
    is_valid: bool

class ClaimDecision(BaseModel):
    status: str
    reason: str
    confidence: float

class ClaimProcessingResponse(BaseModel):
    documents: List[ProcessedDocument]
    validation: ValidationResult
    claim_decision: ClaimDecision
    processing_time_seconds: float
