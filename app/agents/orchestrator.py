import asyncio
from typing import List, Dict, Any
from app.services.llm_service import LLMService
from app.models.schemas import (
    ProcessedDocument, 
    ValidationResult, 
    ClaimDecision,
    ClaimProcessingResponse
)

class ClaimOrchestrator:
    def __init__(self):
        self.llm_service = LLMService()
    
    async def process_claim(self, documents: List[dict]) -> Dict[str, Any]:
        """Main orchestration logic for claim processing"""
        
        # Step 1: Classify all documents
        classified_docs = await self._classify_documents(documents)
        
        # Step 2: Extract structured data using specialized agents
        processed_docs = await self._extract_document_data(classified_docs)
        
        # Step 3: Validate documents
        validation = await self._validate_documents(processed_docs)
        
        # Step 4: Make claim decision
        decision = await self._make_decision(processed_docs, validation)
        
        # Build response
        return {
            "documents": processed_docs,
            "validation": validation,
            "claim_decision": decision
        }
    
    async def _classify_documents(self, documents: List[dict]) -> List[dict]:
        """Classify each document using LLM"""
        tasks = []
        
        for doc in documents:
            # Handle both 'file_name' and 'filename' keys
            fname = doc.get('file_name', doc.get('filename', 'unknown.pdf'))
            task = self.llm_service.classify_document(
                text=doc['text'], 
                filename=fname
            )
            tasks.append(task)
        
        classifications = await asyncio.gather(*tasks)
        
        # Merge classifications with documents
        for i, doc in enumerate(documents):
            doc['classification'] = classifications[i]
            doc['document_type'] = classifications[i].get('document_type', 'other')
        
        return documents
    
    async def _extract_document_data(self, documents: List[dict]) -> List[Dict]:
        """Extract structured data using specialized agents"""
        processed = []
        
        for doc in documents:
            doc_type = doc['document_type']
            text = doc['text']
            
            # Route to appropriate extraction agent
            if doc_type == 'bill':
                extracted = await self.llm_service.extract_bill_data(text)
            elif doc_type == 'discharge_summary':
                extracted = await self.llm_service.extract_discharge_data(text)
            elif doc_type == 'id_card':
                extracted = await self.llm_service.extract_id_card_data(text)
            elif doc_type == 'pharmacy_bill':
                extracted = await self.llm_service.extract_pharmacy_data(text)
            elif doc_type == 'claim_form':
                extracted = await self.llm_service.extract_claim_form_data(text)
            else:
                extracted = {}
            
            # Handle both key names
            fname = doc.get('file_name', doc.get('filename', 'unknown.pdf'))
            
            processed.append({
                "file_name": fname,
                "document_type": doc_type,
                "extracted_data": extracted,
                "raw_text": text[:500] + "..." if len(text) > 500 else text
            })
        
        return processed
    
    async def _validate_documents(self, documents: List[dict]) -> ValidationResult:
        """Validate documents for completeness and consistency"""
        
        validation_result = await self.llm_service.validate_documents(documents)
        
        return ValidationResult(
            missing_documents=validation_result.get('missing_documents', []),
            discrepancies=validation_result.get('discrepancies', []),
            is_valid=validation_result.get('is_valid', True)
        )
    
    async def _make_decision(self, documents: List[dict], validation: ValidationResult) -> ClaimDecision:
        """Make final claim decision using LLM"""
        
        decision_data = await self.llm_service.make_claim_decision(
            documents=documents,
            validation=validation.dict()
        )
        
        return ClaimDecision(
            status=decision_data.get('status', 'manual_review'),
            reason=decision_data.get('reason', 'Unable to determine'),
            confidence=decision_data.get('confidence', 0.5)
        )