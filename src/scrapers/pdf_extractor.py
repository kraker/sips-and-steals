#!/usr/bin/env python3
"""
PDF Text Extractor

Simple PDF text extraction using pypdf for integration with the universal
happy hour extraction system.
"""

import logging
from typing import Optional
from io import BytesIO
import pypdf

logger = logging.getLogger(__name__)


class PDFTextExtractor:
    """
    Simple PDF text extractor using pypdf.
    
    Extracts plain text from PDF content for processing by the universal
    happy hour extractor.
    """
    
    def __init__(self):
        """Initialize PDF text extractor."""
        pass
    
    def extract_text_from_bytes(self, pdf_bytes: bytes) -> Optional[str]:
        """
        Extract text from PDF bytes.
        
        Args:
            pdf_bytes: PDF file content as bytes
            
        Returns:
            Extracted text string or None if extraction fails
        """
        try:
            # Create a BytesIO object from the PDF bytes
            pdf_file = BytesIO(pdf_bytes)
            
            # Create PDF reader
            reader = pypdf.PdfReader(pdf_file)
            
            # Extract text from all pages
            text = ""
            for page_num, page in enumerate(reader.pages):
                try:
                    page_text = page.extract_text()
                    if page_text:
                        text += f"\n--- Page {page_num + 1} ---\n"
                        text += page_text
                        text += "\n"
                except Exception as e:
                    logger.warning(f"Failed to extract text from page {page_num + 1}: {e}")
                    continue
            
            if text.strip():
                logger.info(f"Successfully extracted {len(text)} characters from PDF with {len(reader.pages)} pages")
                return text.strip()
            else:
                logger.warning("No text could be extracted from PDF")
                return None
                
        except Exception as e:
            logger.error(f"Failed to extract text from PDF: {e}")
            return None
    
    def extract_text_from_url(self, pdf_content: bytes, source_url: str) -> Optional[str]:
        """
        Extract text from PDF content with source URL context.
        
        Args:
            pdf_content: PDF file content as bytes
            source_url: URL where PDF was downloaded from
            
        Returns:
            Extracted text string or None if extraction fails
        """
        logger.info(f"Extracting text from PDF: {source_url}")
        
        text = self.extract_text_from_bytes(pdf_content)
        
        if text:
            # Add source URL as context for the universal extractor
            text = f"PDF Source: {source_url}\n\n{text}"
            
        return text
    
    def is_pdf_content(self, content_bytes: bytes) -> bool:
        """
        Check if the given bytes represent a PDF file.
        
        Args:
            content_bytes: File content as bytes
            
        Returns:
            True if content appears to be a PDF file
        """
        if not content_bytes:
            return False
            
        # Check PDF file signature (magic bytes)
        if content_bytes.startswith(b'%PDF-'):
            return True
            
        return False
    
    def validate_pdf_accessibility(self, pdf_bytes: bytes) -> bool:
        """
        Check if a PDF can be read and processed.
        
        Args:
            pdf_bytes: PDF file content as bytes
            
        Returns:
            True if PDF can be processed successfully
        """
        try:
            pdf_file = BytesIO(pdf_bytes)
            reader = pypdf.PdfReader(pdf_file)
            
            # Check if we can access pages
            if len(reader.pages) == 0:
                logger.warning("PDF has no pages")
                return False
                
            # Try to extract text from first page
            first_page = reader.pages[0]
            test_text = first_page.extract_text()
            
            # PDF is accessible if we can read it (even if text is empty)
            return True
            
        except Exception as e:
            logger.warning(f"PDF validation failed: {e}")
            return False


# Test function for development
if __name__ == "__main__":
    import httpx
    
    # Test with a sample PDF URL
    extractor = PDFTextExtractor()
    
    # Example test (would need a real PDF URL)
    test_url = "https://jovanina.com/wp-content/uploads/2025/05/Happy-Hour-Menu-Card8.pdf"
    
    try:
        with httpx.Client() as client:
            response = client.get(test_url)
            
            if response.status_code == 200:
                if extractor.is_pdf_content(response.content):
                    text = extractor.extract_text_from_url(response.content, test_url)
                    
                    if text:
                        print(f"Extracted {len(text)} characters:")
                        print(text[:500] + "..." if len(text) > 500 else text)
                    else:
                        print("No text extracted")
                else:
                    print("Content is not a PDF")
            else:
                print(f"Failed to fetch PDF: {response.status_code}")
                
    except Exception as e:
        print(f"Test failed: {e}")