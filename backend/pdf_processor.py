import PyPDF2
import io
from typing import Optional

def extract_text_from_pdf(file_path: str) -> str:
    """
    Extract text content from a PDF file
    
    Args:
        file_path: Path to the PDF file
        
    Returns:
        Extracted text content as string
        
    Raises:
        Exception: If PDF cannot be read or text extraction fails
    """
    try:
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            
            # Check if PDF is encrypted
            if pdf_reader.is_encrypted:
                raise Exception("PDF is encrypted and cannot be processed")
            
            text_content = ""
            
            # Extract text from all pages
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text_content += page.extract_text() + "\n"
            
            # Clean up the text
            text_content = text_content.strip()
            
            if not text_content:
                raise Exception("No text content found in PDF")
            
            return text_content
            
    except Exception as e:
        raise Exception(f"Failed to extract text from PDF: {str(e)}")

def validate_pdf(file_path: str) -> bool:
    """
    Validate if a file is a valid PDF
    
    Args:
        file_path: Path to the file to validate
        
    Returns:
        True if valid PDF, False otherwise
    """
    try:
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            return len(pdf_reader.pages) > 0
    except:
        return False
