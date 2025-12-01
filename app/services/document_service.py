# app/services/document_service.py

import pdfplumber
from io import BytesIO
from typing import List, Tuple
from fastapi import UploadFile
import easyocr
from pdf2image import convert_from_bytes
from langdetect import detect, DetectorFactory
from PIL import Image
import logging
import re

# Fix langdetect randomness
DetectorFactory.seed = 0

# Initialize OCR reader once (supports English + major Indian languages)
# Note: Some languages like Telugu require being paired with English
logging.info("Initializing EasyOCR with Telugu and Hindi support...")

# Try different language combinations
ocr_reader = None
language_configs = [
    (['te', 'en'], "Telugu + English"),
    (['hi', 'en'], "Hindi + English"),
    (['en'], "English only (fallback)")
]

for lang_list, desc in language_configs:
    try:
        ocr_reader = easyocr.Reader(lang_list, gpu=False)
        logging.info(f"✅ OCR initialized with: {desc}")
        break
    except Exception as e:
        logging.warning(f"Failed to load {desc}: {e}")
        continue

if ocr_reader is None:
    logging.error("Critical: Failed to initialize OCR with any language configuration")
    raise RuntimeError("EasyOCR initialization failed")

class DocumentService:
    
    @staticmethod
    def detect_language_advanced(text: str) -> str:
        """
        Enhanced language detection for Indian languages
        Combines Unicode range detection + langdetect
        """
        if not text.strip():
            return "unknown"
        
        # Check for Telugu characters (Unicode range: 0C00-0C7F)
        telugu_pattern = re.compile(r'[\u0C00-\u0C7F]+')
        # Check for Hindi/Devanagari (Unicode range: 0900-097F)
        hindi_pattern = re.compile(r'[\u0900-\u097F]+')
        # Check for Kannada (0C80-0CFF)
        kannada_pattern = re.compile(r'[\u0C80-\u0CFF]+')
        # Check for Tamil (0B80-0BFF)
        tamil_pattern = re.compile(r'[\u0B80-\u0BFF]+')
        
        # Count characters for each language
        telugu_count = len(telugu_pattern.findall(text))
        hindi_count = len(hindi_pattern.findall(text))
        kannada_count = len(kannada_pattern.findall(text))
        tamil_count = len(tamil_pattern.findall(text))
        
        # Determine dominant language by character count
        lang_counts = {
            'te': telugu_count,
            'hi': hindi_count,
            'kn': kannada_count,
            'ta': tamil_count
        }
        
        max_lang = max(lang_counts, key=lang_counts.get)
        max_count = lang_counts[max_lang]
        
        # If significant Indian language characters found
        if max_count > 10:
            logging.info(f"Detected {max_lang} via Unicode ({max_count} chars)")
            return max_lang
        
        # Fallback to langdetect for English/mixed content
        try:
            detected = detect(text)
            logging.info(f"Detected {detected} via langdetect")
            return detected
        except:
            return "en"  # Default to English if detection fails

    @staticmethod
    def extract_text_from_pdf_bytes(content: bytes, filename: str) -> Tuple[str, str]:
        """
        Extract text from PDF bytes.
        First tries normal text extraction → if fails/empty → treats as scanned → OCR
        Returns (text, detected_language)
        """
        text = ""
        language = "unknown"
        
        # Step 1: Try normal text extraction (fast)
        try:
            with pdfplumber.open(BytesIO(content)) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            
            if text.strip():
                language = DocumentService.detect_language_advanced(text)
                logging.info(f"Text extracted normally from {filename} | Lang: {language}")
                return text.strip(), language
        except Exception as e:
            logging.warning(f"Normal extraction failed: {e}")
        
        # Step 2: If no text → it's a scanned/image PDF → use OCR
        logging.info(f"Falling back to OCR for {filename}")
        try:
            images = convert_from_bytes(content, dpi=200)
            ocr_text = ""
            for i, img in enumerate(images):
                result = ocr_reader.readtext(img, detail=0, paragraph=True)
                page_text = "\n".join(result)
                ocr_text += page_text + "\n"
            
            if ocr_text.strip():
                text = ocr_text.strip()
                language = DocumentService.detect_language_advanced(text)
                logging.info(f"OCR successful | Pages: {len(images)} | Lang: {language}")
                return text, language
            else:
                return "", "unknown"
                
        except Exception as e:
            logging.error(f"OCR failed for {filename}: {e}")
            return "", "unknown"

    @staticmethod
    def extract_text_from_image(content: bytes, filename: str) -> Tuple[str, str]:
        """
        Extract text from image files (JPG, PNG, etc.)
        Returns (text, detected_language)
        """
        try:
            # Open image
            img = Image.open(BytesIO(content))
            
            # Convert to RGB if needed
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            logging.info(f"Processing image {filename} | Size: {img.size}")
            
            # Run OCR
            result = ocr_reader.readtext(img, detail=0, paragraph=True)
            text = "\n".join(result)
            
            if text.strip():
                language = DocumentService.detect_language_advanced(text)
                logging.info(f"OCR successful on image | Lang: {language}")
                return text.strip(), language
            else:
                logging.warning(f"No text detected in {filename}")
                return "", "unknown"
                
        except Exception as e:
            logging.error(f"Image OCR failed for {filename}: {e}")
            return "", "unknown"

    @staticmethod
    async def process_multiple_files(files: List[UploadFile]) -> List[dict]:
        """
        Process multiple files (PDFs and Images)
        """
        results = []
        
        # Supported image formats
        image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.webp'}
        
        for file in files:
            filename_lower = file.filename.lower()
            
            # Determine file type
            is_pdf = filename_lower.endswith('.pdf')
            is_image = any(filename_lower.endswith(ext) for ext in image_extensions)
            
            if not (is_pdf or is_image):
                logging.warning(f"Skipping unsupported file: {file.filename}")
                continue
            
            content = await file.read()
            
            # Process based on file type
            if is_pdf:
                text, language = DocumentService.extract_text_from_pdf_bytes(content, file.filename)
                source_type = "pdf"
            else:
                text, language = DocumentService.extract_text_from_image(content, file.filename)
                source_type = "image"
            
            results.append({
                "file_name": file.filename,
                "text": text,
                "language": language,
                "size": len(text),
                "file_type": source_type,
                "char_count": len(text)
            })
            
            # Reset pointer for other uses
            await file.seek(0)
        
        return results