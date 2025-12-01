# app/agents/orchestrator.py

import json
import re
import logging
from typing import List, Dict, Any
from app.models.schemas import (
    DocumentInfo, ValidationResult, ValidationIssue, 
    ClaimDecision, BillData, DischargeSummaryData, IDCardData
)

class ClaimOrchestrator:
    """
    Orchestrates the entire claim processing workflow:
    1. Extract structured data from documents
    2. Validate cross-document consistency
    3. Make approval decision
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    async def process_claim(self, documents: List[Dict]) -> Dict[str, Any]:
        """
        Main orchestration method
        """
        self.logger.info(f"Processing {len(documents)} documents")
        
        # Step 1: Extract structured data from each document
        processed_docs = []
        bill_data = None
        discharge_data = None
        id_card_data = None
        
        for doc in documents:
            doc_type = self._identify_document_type(doc['text'], doc['file_name'])
            extracted = self._extract_structured_data(doc['text'], doc_type)
            
            doc_info = DocumentInfo(
                file_name=doc['file_name'],
                language=doc['language'],
                file_type=doc['file_type'],
                char_count=doc['char_count'],
                extracted_data={
                    'type': doc_type,
                    'data': extracted
                }
            )
            processed_docs.append(doc_info)
            
            # Store typed data for validation
            if doc_type == 'bill':
                bill_data = extracted
            elif doc_type == 'discharge_summary':
                discharge_data = extracted
            elif doc_type == 'id_card':
                id_card_data = extracted
        
        # Step 2: Validate cross-document consistency
        validation = self._validate_documents(bill_data, discharge_data, id_card_data)
        
        # Step 3: Make claim decision
        claim_decision = self._make_claim_decision(
            bill_data, discharge_data, id_card_data, validation
        )
        
        return {
            'documents': processed_docs,
            'validation': validation,
            'claim_decision': claim_decision
        }
    
    def _identify_document_type(self, text: str, filename: str) -> str:
        """
        Identify document type based on content and filename
        """
        text_lower = text.lower()
        filename_lower = filename.lower()
        
        # Check filename first for hints
        if 'discharge' in filename_lower or 'summary' in filename_lower:
            return 'discharge_summary'
        elif 'id' in filename_lower or 'card' in filename_lower or 'policy' in filename_lower:
            return 'id_card'
        elif 'bill' in filename_lower or 'invoice' in filename_lower:
            return 'bill'
        
        # Then check content - be more specific with keywords
        # Discharge summary keywords (most specific first)
        discharge_keywords = [
            'discharge summary', 'discharge date', 'admission date',
            'डिस्चार्ज सारांश', 'డిశ్చార్జ్ సారాంశం',
            'patient was admitted', 'diagnosis:', 'treatment given'
        ]
        if any(keyword in text_lower for keyword in discharge_keywords):
            return 'discharge_summary'
        
        # ID card keywords
        id_keywords = [
            'policy number', 'policyholder', 'member id', 'insurance id',
            'पॉलिसी नंबर', 'पॉलिसीधारक', 'పాలసీ నంబర్',
            'coverage amount', 'validity period'
        ]
        if any(keyword in text_lower for keyword in id_keywords):
            return 'id_card'
        
        # Bill keywords (check last as it's most common)
        bill_keywords = [
            'hospital bill', 'medical bill', 'invoice', 'receipt',
            'अस्पताल बिल', 'चिकित्सा बिल', 'ఆసుపత్రి బిల్లు',
            'total amount', 'bill number'
        ]
        if any(keyword in text_lower for keyword in bill_keywords):
            return 'bill'
        
        # Pharmacy bill
        pharmacy_keywords = ['pharmacy', 'दवा', 'మందు', 'medicines', 'prescription']
        if any(keyword in text_lower for keyword in pharmacy_keywords):
            return 'pharmacy_bill'
        
        self.logger.warning(f"Could not identify document type for content: {text[:100]}")
        return 'unknown'
    
    def _extract_structured_data(self, text: str, doc_type: str) -> Dict[str, Any]:
        """
        Extract structured data based on document type
        Uses regex and pattern matching (can be replaced with LLM later)
        """
        data = {}
        
        if doc_type == 'bill':
            data = self._extract_bill_data(text)
        elif doc_type == 'discharge_summary':
            data = self._extract_discharge_data(text)
        elif doc_type == 'id_card':
            data = self._extract_id_card_data(text)
        
        return data
    
    def _extract_bill_data(self, text: str) -> Dict[str, Any]:
        """Extract data from hospital bill"""
        if not text or len(text.strip()) < 10:
            self.logger.warning("Text too short or empty for bill extraction")
            return {
                'bill_number': None,
                'patient_name': None,
                'hospital_name': None,
                'total_amount': None,
                'date': None
            }
        
        data = {
            'bill_number': None,
            'patient_name': None,
            'hospital_name': None,
            'total_amount': None,
            'date': None
        }
        
        # Extract bill number
        bill_patterns = [
            r'bill\s*(?:number|no|संख्या|నంబర్)[:\s]*([A-Z0-9/-]+)',
            r'बिल\s*संख्या[:\s]*([A-Z0-9/-]+)',
            r'బిల్లు\s*నంబర్[:\s]*([A-Z0-9/-]+)'
        ]
        for pattern in bill_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                data['bill_number'] = match.group(1).strip()
                break
        
        # Extract patient name
        name_patterns = [
            r'patient\s*name[:\s]*([^\n]+)',
            r'मरीज\s*का\s*नाम[:\s]*([^\n]+)',
            r'రోగి\s*పేరు[:\s]*([^\n]+)'
        ]
        for pattern in name_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                data['patient_name'] = match.group(1).strip()
                break
        
        # Extract total amount
        amount_patterns = [
            r'total\s*(?:amount|राशि|మొత్తం)[:\s]*(?:₹|Rs\.?)\s*([\d,]+)',
            r'कुल\s*राशि[:\s]*₹\s*([\d,]+)',
            r'మొత్తం\s*మొత్తం[:\s]*₹\s*([\d,]+)'
        ]
        for pattern in amount_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amount_str = match.group(1).replace(',', '')
                data['total_amount'] = float(amount_str)
                break
        
        # Extract date
        date_patterns = [
            r'date[:\s]*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
            r'तारीख[:\s]*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
            r'తేదీ[:\s]*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})'
        ]
        for pattern in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                data['date'] = match.group(1).strip()
                break
        
        # Extract hospital name (first line often contains it)
        lines = text.split('\n')
        for line in lines[:5]:
            if len(line.strip()) > 5 and not any(char.isdigit() for char in line):
                data['hospital_name'] = line.strip()
                break
        
        return data
    
    def _extract_discharge_data(self, text: str) -> Dict[str, Any]:
        """Extract data from discharge summary"""
        if not text or len(text.strip()) < 10:
            self.logger.warning("Text too short or empty for discharge summary extraction")
            return {
                'patient_name': None,
                'diagnosis': None,
                'admission_date': None,
                'discharge_date': None
            }
        
        data = {
            'patient_name': None,
            'diagnosis': None,
            'admission_date': None,
            'discharge_date': None
        }
        
        # Extract patient name
        name_patterns = [
            r'patient\s*name[:\s]*([^\n]+)',
            r'मरीज\s*का\s*नाम[:\s]*([^\n]+)',
            r'రోగి\s*పేరు[:\s]*([^\n]+)'
        ]
        for pattern in name_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                data['patient_name'] = match.group(1).strip()
                break
        
        # Extract diagnosis
        diag_patterns = [
            r'diagnosis[:\s]*([^\n]+)',
            r'निदान[:\s]*([^\n]+)',
            r'నిర్ధారణ[:\s]*([^\n]+)'
        ]
        for pattern in diag_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                data['diagnosis'] = match.group(1).strip()
                break
        
        return data
    
    def _extract_id_card_data(self, text: str) -> Dict[str, Any]:
        """Extract data from insurance ID card"""
        if not text or len(text.strip()) < 10:
            self.logger.warning("Text too short or empty for ID card extraction")
            return {
                'policy_number': None,
                'patient_name': None,
                'insurance_company': None,
                'coverage_amount': None
            }
        
        data = {
            'policy_number': None,
            'patient_name': None,
            'insurance_company': None,
            'coverage_amount': None
        }
        
        # Extract policy number
        policy_patterns = [
            r'policy\s*(?:number|no|संख्या|నంబర్)[:\s]*([A-Z0-9/-]+)',
            r'पॉलिसी\s*नंबर[:\s]*([A-Z0-9/-]+)',
            r'పాలసీ\s*నంబర్[:\s]*([A-Z0-9/-]+)'
        ]
        for pattern in policy_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                data['policy_number'] = match.group(1).strip()
                break
        
        # Extract patient name
        name_patterns = [
            r'name[:\s]*([^\n]+)',
            r'नाम[:\s]*([^\n]+)',
            r'పేరు[:\s]*([^\n]+)'
        ]
        for pattern in name_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                data['patient_name'] = match.group(1).strip()
                break
        
        # Extract insurance company
        company_patterns = [
            r'insurance\s*company[:\s]*([^\n]+)',
            r'बीमा\s*कंपनी[:\s]*([^\n]+)',
            r'బీమా\s*కంపెనీ[:\s]*([^\n]+)'
        ]
        for pattern in company_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                data['insurance_company'] = match.group(1).strip()
                break
        
        return data
    
    def _validate_documents(self, bill_data, discharge_data, id_card_data) -> ValidationResult:
        """
        Cross-validate data across documents
        """
        issues = []
        cross_checks = {
            'name_match': False,
            'policy_exists': False,
            'amount_within_coverage': False,
            'required_docs_present': False
        }
        
        # Check if all required documents are present
        if bill_data and discharge_data and id_card_data:
            cross_checks['required_docs_present'] = True
        else:
            issues.append(ValidationIssue(
                field="documents",
                issue="Missing required documents (Bill, Discharge Summary, or ID Card)",
                severity="critical"
            ))
        
        # Validate name consistency
        if bill_data and discharge_data and id_card_data:
            bill_name = (bill_data.get('patient_name') or '').lower().strip()
            discharge_name = (discharge_data.get('patient_name') or '').lower().strip()
            id_name = (id_card_data.get('patient_name') or '').lower().strip()
            
            # Check if names match (allowing for partial matches)
            if bill_name and discharge_name and id_name:
                if (bill_name in discharge_name or discharge_name in bill_name) and \
                   (bill_name in id_name or id_name in bill_name):
                    cross_checks['name_match'] = True
                else:
                    issues.append(ValidationIssue(
                        field="patient_name",
                        issue=f"Name mismatch: Bill='{bill_name}', Discharge='{discharge_name}', ID='{id_name}'",
                        severity="critical"
                    ))
            else:
                missing = []
                if not bill_name:
                    missing.append("Bill")
                if not discharge_name:
                    missing.append("Discharge")
                if not id_name:
                    missing.append("ID Card")
                issues.append(ValidationIssue(
                    field="patient_name",
                    issue=f"Patient name missing in: {', '.join(missing)}",
                    severity="warning"
                ))
        
        # Check policy number exists
        if id_card_data and id_card_data.get('policy_number'):
            cross_checks['policy_exists'] = True
        else:
            issues.append(ValidationIssue(
                field="policy_number",
                issue="Policy number not found in ID card",
                severity="critical"
            ))
        
        # Check amount within coverage
        if bill_data and id_card_data:
            bill_amount = bill_data.get('total_amount') or 0
            coverage = id_card_data.get('coverage_amount') or 0
            
            if bill_amount > 0 and coverage > 0:
                if bill_amount <= coverage:
                    cross_checks['amount_within_coverage'] = True
                else:
                    issues.append(ValidationIssue(
                        field="amount",
                        issue=f"Bill amount ₹{bill_amount:,.2f} exceeds coverage ₹{coverage:,.2f}",
                        severity="critical"
                    ))
            elif bill_amount > 0 and coverage == 0:
                issues.append(ValidationIssue(
                    field="coverage_amount",
                    issue="Coverage amount not found in ID card",
                    severity="warning"
                ))
            elif bill_amount == 0:
                issues.append(ValidationIssue(
                    field="total_amount",
                    issue="Total amount not found in bill",
                    severity="critical"
                ))
        
        is_valid = all(cross_checks.values()) and not any(
            issue.severity == "critical" for issue in issues
        )
        
        return ValidationResult(
            is_valid=is_valid,
            issues=issues,
            cross_check_results=cross_checks
        )
    
    def _make_claim_decision(self, bill_data, discharge_data, id_card_data, 
                            validation: ValidationResult) -> ClaimDecision:
        """
        Make final claim approval decision based on validation
        """
        reasons = []
        status = "Pending Review"
        confidence = 0.0
        approved_amount = None
        recommendations = []
        
        # Decision logic
        if validation.is_valid:
            status = "Approved"
            confidence = 0.95
            
            if bill_data and bill_data.get('total_amount'):
                approved_amount = bill_data['total_amount']
                reasons.append(f"All validations passed")
                reasons.append(f"Cross-document verification successful")
                reasons.append(f"Amount ₹{approved_amount:,.2f} approved")
            
        else:
            # Check severity of issues
            critical_issues = [i for i in validation.issues if i.severity == "critical"]
            
            if critical_issues:
                status = "Rejected"
                confidence = 0.90
                reasons.append(f"Found {len(critical_issues)} critical issues")
                for issue in critical_issues:
                    reasons.append(f"❌ {issue.field}: {issue.issue}")
                recommendations.append("Submit complete documentation")
                recommendations.append("Verify patient name consistency across all documents")
            else:
                status = "Pending Review"
                confidence = 0.60
                reasons.append("Minor validation issues detected")
                for issue in validation.issues:
                    reasons.append(f"⚠️ {issue.field}: {issue.issue}")
                recommendations.append("Manual review recommended")
        
        return ClaimDecision(
            status=status,
            confidence=confidence,
            approved_amount=approved_amount,
            reasons=reasons,
            recommendations=recommendations if recommendations else None
        )