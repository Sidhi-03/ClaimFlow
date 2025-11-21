from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import time
from dotenv import load_dotenv

from app.services.document_service import DocumentService
from app.agents.orchestrator import ClaimOrchestrator
from app.models.schemas import ClaimProcessingResponse

load_dotenv()

app = FastAPI(title="SuperClaims API",
              description="Medical Claim Processing System with LLM-powered agents",
              version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

document_service = DocumentService()
orchestrator = ClaimOrchestrator()

@app.get("/")
async def root():
    return {"message": "SuperClaims API is running", "status": "healthy"}

@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": time.time()}

@app.post("/process-claim", response_model=ClaimProcessingResponse)
async def process_claim(files: List[UploadFile] = File(...)):
    """
    Process multiple medical claim PDFs and return structured decision
    """
    
    start_time = time.time()
    
    try:
        # Validate files
        if not files:
            raise HTTPException(status_code=400, detail="No files provided")
        
        if len(files) > 10:
            raise HTTPException(status_code=400, detail="Maximum 10 files allowed")
        
        # Check file types
        for file in files:
            if not file.filename.lower().endswith('.pdf'):
                raise HTTPException(
                    status_code=400, 
                    detail=f"Only PDF files allowed. Invalid file: {file.filename}"
                )
        
        # Step 1: Extract text from all PDFs
        print(f"Processing {len(files)} files...")
        documents = await document_service.process_multiple_pdfs(files)
        
        if not documents:
            raise HTTPException(status_code=400, detail="No valid documents found")
        
        # Step 2: Orchestrate claim processing with AI
        print("Running AI agents...")
        result = await orchestrator.process_claim(documents)
        
        # Calculate processing time
        processing_time = time.time() - start_time
        
        # Build response
        response = ClaimProcessingResponse(
            documents=result['documents'],
            validation=result['validation'],
            claim_decision=result['claim_decision'],
            processing_time_seconds=round(processing_time, 2)
        )
        
        print(f"Processing complete in {processing_time:.2f}s")
        print(f"Decision: {response.claim_decision.status}")
        
        return response
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error processing claim: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/supported-documents")
async def supported_documents():
    return {
        "supported_types": [
            {"type": "bill", "description": "Hospital bill", "required": True},
            {"type": "discharge_summary", "description": "Discharge summary", "required": True},
            {"type": "id_card", "description": "Insurance ID", "required": True},
            {"type": "pharmacy_bill", "description": "Pharmacy receipt", "required": False},
            {"type": "claim_form", "description": "Claim form", "required": False}
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
