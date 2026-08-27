#!/usr/bin/env python3
"""
Unani Books Processing Script
Processes PDF books from a folder, performs OCR, chunking, embedding, and indexing to ChromaDB.
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from typing import List, Dict, Any
import hashlib
import json
import re

# PDF processing
import PyPDF2
import pdf2image
from PIL import Image
import pytesseract

# Text processing
import tiktoken

# Embedding and Vector DB
import requests
import chromadb
from chromadb.config import Settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('book_processing.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class BookProcessor:
    def __init__(self, books_folder: str, collection_name: str):
        self.books_folder = Path(books_folder)
        self.collection_name = collection_name
        self.ollama_url = "http://localhost:11434/api/embed"
        self.embedding_model = "nomic-embed-text"
        self.chunk_size = 400  # Target tokens per chunk
        self.chunk_overlap = 50  # Overlap tokens between chunks
        
        # Initialize ChromaDB client
        self.chroma_client = chromadb.PersistentClient(path="./chroma_db")
        self.collection = self._get_or_create_collection()
        
        # Initialize tokenizer for chunking
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
        
        # Statistics
        self.stats = {
            'total_files': 0,
            'processed_files': 0,
            'failed_files': 0,
            'total_chunks': 0,
            'indexed_chunks': 0,
            'skipped_chunks': 0
        }
    
    def _get_or_create_collection(self):
        """Get or create ChromaDB collection with duplicate handling."""
        try:
            # Try to get existing collection
            collection = self.chroma_client.get_collection(name=self.collection_name)
            logger.info(f"Using existing collection: {self.collection_name}")
        except:
            # Create new collection
            collection = self.chroma_client.create_collection(
                name=self.collection_name,
                metadata={"description": "Unani medicine books collection"}
            )
            logger.info(f"Created new collection: {self.collection_name}")
        
        return collection
    
    def _generate_chunk_id(self, book_name: str, chunk_index: int, content: str) -> str:
        """Generate unique ID for a chunk based on book name, index, and content hash."""
        content_hash = hashlib.md5(content.encode()).hexdigest()[:8]
        return f"{book_name}_{chunk_index}_{content_hash}"
    
    def _extract_text_from_pdf(self, pdf_path: Path) -> tuple[str, bool]:
        """
        Extract text from PDF.
        Returns tuple of (text, is_image_based).
        """
        text = ""
        is_image_based = False
        
        try:
            # First try to extract text directly
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text_content = []
                
                for page_num, page in enumerate(pdf_reader.pages):
                    try:
                        page_text = page.extract_text()
                        if page_text and page_text.strip():
                            text_content.append(page_text)
                    except Exception as e:
                        logger.warning(f"Error extracting text from page {page_num}: {e}")
                
                text = "\n".join(text_content)
                
                # Check if extracted text is meaningful (not just garbage)
                if len(text.strip()) > 100 and self._is_meaningful_text(text):
                    logger.info(f"Extracted text directly from PDF: {len(text)} characters")
                    return text, False
        
        except Exception as e:
            logger.warning(f"Direct text extraction failed: {e}")
        
        # If direct extraction failed or produced poor results, use OCR
        logger.info(f"Using OCR for {pdf_path.name}")
        text = self._ocr_pdf(pdf_path)
        is_image_based = True
        
        return text, is_image_based
    
    def _is_meaningful_text(self, text: str) -> bool:
        """Check if extracted text is meaningful or just garbage."""
        # Remove whitespace and check for meaningful content
        clean_text = re.sub(r'\s+', '', text)
        
        # Check for reasonable character distribution
        if len(clean_text) < 50:
            return False
        
        # Check for Bengali and English characters
        bengali_chars = len(re.findall(r'[\u0980-\u09FF]', clean_text))
        english_chars = len(re.findall(r'[a-zA-Z]', clean_text))
        
        # If we have reasonable amount of meaningful characters
        return (bengali_chars + english_chars) / len(clean_text) > 0.3
    
    def _ocr_pdf(self, pdf_path: Path) -> str:
        """Perform OCR on PDF using Tesseract with Bengali and English."""
        try:
            # Convert PDF to images
            logger.info(f"Converting PDF to images for OCR: {pdf_path.name}")
            images = pdf2image.convert_from_path(
                str(pdf_path),
                dpi=300,
                fmt='jpeg'
            )
            
            full_text = []
            
            for page_num, image in enumerate(images):
                try:
                    # Perform OCR with Bengali and English
                    page_text = pytesseract.image_to_string(
                        image,
                        lang='ben+eng',
                        config='--psm 6 --oem 3'
                    )
                    
                    if page_text.strip():
                        full_text.append(f"--- Page {page_num + 1} ---\n{page_text}")
                        logger.info(f"OCR completed for page {page_num + 1}")
                
                except Exception as e:
                    logger.error(f"OCR failed for page {page_num}: {e}")
            
            return "\n".join(full_text)
        
        except Exception as e:
            logger.error(f"OCR failed for {pdf_path.name}: {e}")
            return ""
    
    def _extract_metadata(self, pdf_path: Path, chunk_start: int, chunk_end: int) -> Dict[str, Any]:
        """Extract metadata for a chunk."""
        book_name = pdf_path.stem
        # Try to extract chapter info from text or use position-based estimation
        estimated_page = (chunk_start // 2000) + 1  # Rough estimation
        
        return {
            "book_name": book_name,
            "file_name": pdf_path.name,
            "chunk_start": chunk_start,
            "chunk_end": chunk_end,
            "estimated_page": estimated_page,
            "total_chunks_in_book": 0  # Will be updated later
        }
    
    def _chunk_text(self, text: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Split text into chunks with metadata."""
        if not text or len(text.strip()) < 50:
            return []
        
        chunks = []
        tokens = self.tokenizer.encode(text)
        
        # Calculate chunk positions in original text
        token_to_char = {}
        char_position = 0
        for i, token in enumerate(tokens):
            decoded = self.tokenizer.decode([token])
            char_position += len(decoded)
            token_to_char[i] = char_position
        
        # Create chunks
        for i in range(0, len(tokens), self.chunk_size - self.chunk_overlap):
            chunk_tokens = tokens[i:i + self.chunk_size]
            chunk_text = self.tokenizer.decode(chunk_tokens)
            
            if len(chunk_text.strip()) < 20:  # Skip very small chunks
                continue
            
            start_char = token_to_char.get(i, 0)
            end_char = token_to_char.get(i + len(chunk_tokens), len(text))
            
            chunk_metadata = metadata.copy()
            chunk_metadata.update({
                "chunk_start": start_char,
                "chunk_end": end_char,
                "chunk_index": len(chunks),
                "token_count": len(chunk_tokens)
            })
            
            chunks.append({
                "text": chunk_text,
                "metadata": chunk_metadata
            })
        
        # Update total chunks count in metadata
        for chunk in chunks:
            chunk["metadata"]["total_chunks_in_book"] = len(chunks)
        
        return chunks
    
    def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding using Ollama nomic-embed-text."""
        try:
            response = requests.post(
                self.ollama_url,
                json={
                    "model": self.embedding_model,
                    "prompt": text
                },
                timeout=60
            )
            
            if response.status_code == 200:
                return response.json().get("embedding", [])
            else:
                logger.error(f"Embedding failed: {response.status_code} - {response.text}")
                return []
        
        except Exception as e:
            logger.error(f"Embedding generation error: {e}")
            return []
    
    def _process_book(self, pdf_path: Path) -> int:
        """Process a single book and return number of chunks indexed."""
        logger.info(f"Processing book: {pdf_path.name}")
        
        try:
            # Extract text from PDF
            text, is_image_based = self._extract_text_from_pdf(pdf_path)
            
            if not text or len(text.strip()) < 100:
                logger.warning(f"Skipping {pdf_path.name}: No meaningful text extracted")
                return 0
            
            # Extract base metadata
            base_metadata = {
                "book_name": pdf_path.stem,
                "file_name": pdf_path.name,
                "file_size": pdf_path.stat().st_size,
                "is_image_based": is_image_based,
                "processing_date": str(Path.cwd())  # Using current date as placeholder
            }
            
            # Chunk the text
            chunks = self._chunk_text(text, base_metadata)
            
            if not chunks:
                logger.warning(f"No chunks generated for {pdf_path.name}")
                return 0
            
            logger.info(f"Generated {len(chunks)} chunks from {pdf_path.name}")
            
            # Process each chunk
            indexed_count = 0
            for chunk in chunks:
                chunk_id = self._generate_chunk_id(
                    base_metadata["book_name"],
                    chunk["metadata"]["chunk_index"],
                    chunk["text"]
                )
                
                # Check if chunk already exists
                try:
                    existing = self.collection.get(
                        ids=[chunk_id],
                        include=["documents", "metadatas"]
                    )
                    
                    if existing["ids"]:
                        logger.debug(f"Chunk {chunk_id} already exists, skipping")
                        self.stats['skipped_chunks'] += 1
                        continue
                
                except Exception as e:
                    logger.debug(f"Error checking existing chunk: {e}")
                
                # Generate embedding
                embedding = self._generate_embedding(chunk["text"])
                
                if not embedding:
                    logger.warning(f"Failed to generate embedding for chunk {chunk_id}")
                    continue
                
                # Add to ChromaDB
                try:
                    self.collection.add(
                        ids=[chunk_id],
                        documents=[chunk["text"]],
                        embeddings=[embedding],
                        metadatas=[chunk["metadata"]]
                    )
                    indexed_count += 1
                    logger.debug(f"Indexed chunk {chunk_id}")
                
                except Exception as e:
                    logger.error(f"Failed to index chunk {chunk_id}: {e}")
            
            logger.info(f"Successfully indexed {indexed_count}/{len(chunks)} chunks from {pdf_path.name}")
            return indexed_count
        
        except Exception as e:
            logger.error(f"Failed to process {pdf_path.name}: {e}")
            return 0
    
    def process_all_books(self):
        """Process all PDF books in the specified folder."""
        if not self.books_folder.exists():
            logger.error(f"Books folder does not exist: {self.books_folder}")
            return
        
        pdf_files = list(self.books_folder.glob("*.pdf"))
        
        if not pdf_files:
            logger.warning(f"No PDF files found in {self.books_folder}")
            return
        
        self.stats['total_files'] = len(pdf_files)
        logger.info(f"Found {len(pdf_files)} PDF files to process")
        
        for pdf_path in pdf_files:
            try:
                chunks_indexed = self._process_book(pdf_path)
                self.stats['indexed_chunks'] += chunks_indexed
                self.stats['total_chunks'] += chunks_indexed  # This will be updated if we implement chunk counting
                self.stats['processed_files'] += 1
            
            except Exception as e:
                logger.error(f"Error processing {pdf_path.name}: {e}")
                self.stats['failed_files'] += 1
        
        self._print_summary()
    
    def _print_summary(self):
        """Print processing summary."""
        logger.info("\n" + "="*50)
        logger.info("PROCESSING SUMMARY")
        logger.info("="*50)
        logger.info(f"Total files found: {self.stats['total_files']}")
        logger.info(f"Successfully processed: {self.stats['processed_files']}")
        logger.info(f"Failed files: {self.stats['failed_files']}")
        logger.info(f"Total chunks indexed: {self.stats['indexed_chunks']}")
        logger.info(f"Skipped duplicate chunks: {self.stats['skipped_chunks']}")
        logger.info(f"Collection name: {self.collection_name}")
        logger.info("="*50)

def main():
    parser = argparse.ArgumentParser(
        description="Process Unani medicine books and index them to ChromaDB"
    )
    parser.add_argument(
        "--folder",
        type=str,
        default="./books",
        help="Path to folder containing PDF books (default: ./books)"
    )
    parser.add_argument(
        "--collection",
        type=str,
        default="unani_books",
        help="ChromaDB collection name (default: unani_books)"
    )
    
    args = parser.parse_args()
    
    logger.info("Starting Unani Books Processing...")
    logger.info(f"Books folder: {args.folder}")
    logger.info(f"Collection name: {args.collection}")
    
    try:
        processor = BookProcessor(args.folder, args.collection)
        processor.process_all_books()
        
        logger.info("Processing completed successfully!")
        return 0
    
    except Exception as e:
        logger.error(f"Processing failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())