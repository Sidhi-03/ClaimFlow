import pdfplumber
from io import BytesIO
from typing import List
from fastapi import UploadFile

class DocumentService:
    
    @staticmethod
    async def extract_text_from_pdf(file: UploadFile) -> str:
        """Extract text from PDF file using pdfplumber"""
        try:
            # Read file content
            content = await file.read()
            pdf_file = BytesIO(content)
            
            # Extract text using pdfplumber
            text = ""
            with pdfplumber.open(pdf_file) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            
            # Reset file pointer
            await file.seek(0)
            
            return text.strip()
        except Exception as e:
            print(f"Error extracting text from {file.filename}: {str(e)}")
            return ""
    
    @staticmethod
    async def process_multiple_pdfs(files: List[UploadFile]) -> List[dict]:
        """Process multiple PDF files and extract text"""
        results = []
        
        for file in files:
            if not file.filename.lower().endswith('.pdf'):
                continue
            
            text = await DocumentService.extract_text_from_pdf(file)
            
            results.append({
                "filename": file.filename,
                "text": text,
                "size": len(text)
            })
        
        return results