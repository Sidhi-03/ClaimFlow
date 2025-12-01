# app/models/schemas.py

from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

# Document Models
class DocumentInfo(BaseModel):
    file_name: str
    language: str
    file_type: str
    char_count: int
    extracted_data: Optional[Dict[str, Any]] = None

# Validation Models
class ValidationIssue(BaseModel):
    field: str
    issue: str
    severity: str  # "critical", "warning", "info"

class ValidationResult(BaseModel):
    is_valid: bool
    issues: List[ValidationIssue]
    cross_check_results: Dict[str, bool]

# Claim Decision Models
class ClaimDecision(BaseModel):
    status: str  # "Approved", "Rejected", "Pending Review"
    confidence: float  # 0.0 to 1.0
    approved_amount: Optional[float] = None
    reasons: List[str]
    recommendations: Optional[List[str]] = None
    
# Main Response Model
class ClaimProcessingResponse(BaseModel):
    documents: List[DocumentInfo]
    validation: ValidationResult
    claim_decision: ClaimDecision
    processing_time_seconds: float
    timestamp: str = datetime.now().isoformat()

# Extracted Data Schemas
class BillData(BaseModel):
    bill_number: Optional[str] = None
    patient_name: Optional[str] = None
    hospital_name: Optional[str] = None
    total_amount: Optional[float] = None
    date: Optional[str] = None
    items: Optional[List[Dict[str, Any]]] = None

class DischargeSummaryData(BaseModel):
    patient_name: Optional[str] = None
    diagnosis: Optional[str] = None
    admission_date: Optional[str] = None
    discharge_date: Optional[str] = None
    doctor_name: Optional[str] = None
    treatment_summary: Optional[str] = None

class IDCardData(BaseModel):
    policy_number: Optional[str] = None
    patient_name: Optional[str] = None
    insurance_company: Optional[str] = None
    coverage_amount: Optional[float] = None
    validity: Optional[str] = None