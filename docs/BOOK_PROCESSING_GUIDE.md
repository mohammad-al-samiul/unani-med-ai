# Unani Books Processing Guide

## Overview
এই স্ক্রিপ্টটি ইউনানী চিকিৎসা বইয়ের PDF প্রসেস করে ChromaDB-তে ইনডেক্স করে, যা RAG (Retrieval-Augmented Generation) system-এর জন্য ব্যবহার করা যাবে।

## স্ক্রিপ্ট ফিচার:

### ১. PDF Text Extraction
- **Direct Text Extraction:** প্রথমে সরাসরি text extraction চেষ্টা করে
- **OCR Fallback:** Direct extraction ব্যর্থ হলে Tesseract OCR ব্যবহার করে
- **Multilingual OCR:** Bengali (ben) + English (eng) language support

### ২. Intelligent Chunking
- **Token-based Chunking:** 300-500 tokens per chunk (400 default)
- **Overlap:** 50 tokens overlap between chunks for context continuity
- **Metadata Enrichment:** Book name, chapter, page info included

### ৩. Embedding Generation
- **Ollama Integration:** nomic-embed-text model for embeddings
- **Local Processing:** কোনো cloud API প্রয়োজন নেই
- **Error Handling:** Failed embeddings gracefully handled

### ৪. ChromaDB Integration
- **Duplicate Prevention:** Same chunk দ্বিতীয়বার index হবে না
- **Persistent Storage:** Local ChromaDB instance
- **Rich Metadata:** Comprehensive metadata stored with each chunk

## Prerequisites Installation:

### ১. Python Dependencies:
```powershell
cd C:\Users\Admin\Documents\dev\office-dev\unani-med-ai
.\venv\Scripts\activate
pip install -r book_processing_requirements.txt
```

### ২. System Dependencies:

#### Tesseract OCR:
```powershell
# Windows installer download করুন:
# https://github.com/UB-Mannheim/tesseract/wiki

# অথবা chocolatey দিয়ে:
choco install tesseract
```

#### Poppler (pdf2image এর জন্য):
```powershell
# Windows এর জন্য:
# https://github.com/oschwartz10612/poppler-windows/releases/

# Download করে PATH এ যোগ করুন
```

### ৩. Ollama Setup:
```powershell
# Ollama running আছে কিনা চেক করুন
curl http://localhost:11434/api/tags

# nomic-embed-text model available কিনা চেক করুন
ollama list

# যদি না থাকে:
ollama pull nomic-embed-text
```

### ৪. ChromaDB Setup:
```powershell
# ChromaDB Docker container running আছে কিনা চেক করুন
docker ps | findstr chromadb

# যদি না থাকে:
docker run -d -p 8000:8000 --name chromadb chromadb/chroma:latest
```

## Directory Structure:

```
unani-med-ai/
├── books/                    # PDF books এখানে রাখুন
│   ├── book1.pdf
│   ├── book2.pdf
│   └── ...
├── process_unani_books.py    # Main processing script
├── book_processing_requirements.txt
├── chroma_db/               # ChromaDB data (auto-created)
└── book_processing.log      # Processing log
```

## Usage:

### বেসিক Usage:
```powershell
# Default settings (./books folder, unani_books collection)
python process_unani_books.py

# Custom folder and collection
python process_unani_books.py --folder "C:\MyBooks\Unani" --collection "hakim_texts"
```

### CLI Arguments:
- `--folder`: PDF books যেখানে আছে (default: `./books`)
- `--collection`: ChromaDB collection name (default: `unani_books`)

## Processing Workflow:

### ১. PDF Discovery:
```
Script scans specified folder → Finds all .pdf files → Logs total count
```

### ২. Text Extraction:
```
For each PDF:
├─ Try direct text extraction
├─ If failed/poor quality → Use OCR
├─ Tesseract with ben+eng languages
└─ Extract text with page numbers
```

### ৩. Text Chunking:
```
Extracted text → Tokenize → Split into 400-token chunks
├─ Add 50-token overlap between chunks
├─ Generate metadata for each chunk
└─ Filter out very small chunks (<20 chars)
```

### ৪. Embedding Generation:
```
For each chunk:
├─ Send to Ollama nomic-embed-text
├─ Get 768-dimensional embedding vector
└─ Handle failures gracefully
```

### ৫. ChromaDB Indexing:
```
For each chunk:
├─ Generate unique ID (book_name + chunk_index + content_hash)
├─ Check if already exists (duplicate prevention)
├─ If new → Add to collection
└─ If exists → Skip and log
```

## Output and Logging:

### Console Output:
```
2024-08-26 10:00:00 - INFO - Starting Unani Books Processing...
2024-08-26 10:00:00 - INFO - Books folder: ./books
2024-08-26 10:00:00 - INFO - Collection name: unani_books
2024-08-26 10:00:01 - INFO - Found 5 PDF files to process
2024-08-26 10:00:02 - INFO - Processing book: book1.pdf
2024-08-26 10:00:10 - INFO - Generated 45 chunks from book1.pdf
2024-08-26 10:00:45 - INFO - Successfully indexed 42/45 chunks from book1.pdf
...
==================================================
PROCESSING SUMMARY
==================================================
Total files found: 5
Successfully processed: 4
Failed files: 1
Total chunks indexed: 187
Skipped duplicate chunks: 12
Collection name: unani_books
==================================================
```

### Log File:
- `book_processing.log` - Detailed processing log
- Contains warnings, errors, and debug information

### ChromaDB Storage:
- `./chroma_db/` - Persistent ChromaDB storage
- Can be backed up and restored

## Metadata Structure:

Each chunk in ChromaDB contains:

```python
{
    "book_name": "book1",                    # Book identifier
    "file_name": "book1.pdf",               # Original filename
    "file_size": 1048576,                   # File size in bytes
    "is_image_based": true,                 # Whether OCR was used
    "processing_date": "2024-08-26",        # Processing timestamp
    "chunk_start": 0,                       # Start position in text
    "chunk_end": 1200,                      # End position in text
    "chunk_index": 0,                       # Chunk sequence number
    "token_count": 395,                     # Number of tokens in chunk
    "total_chunks_in_book": 45,             # Total chunks in this book
    "estimated_page": 1                      # Estimated page number
}
```

## Troubleshooting:

### Tesseract Not Found:
```powershell
# Check Tesseract installation
tesseract --version

# Add to PATH if needed
# Environment Variables → System → PATH → Add Tesseract path
```

### Poppler Not Found:
```powershell
# Download and extract Poppler
# Add bin folder to PATH
# Test: pdftoppm -h
```

### Ollama Connection Failed:
```powershell
# Check Ollama is running
ollama serve

# Test connection
curl http://localhost:11434/api/tags
```

### Memory Issues:
```powershell
# Reduce chunk size in script
self.chunk_size = 300  # Instead of 400

# Process books one at a time
# Move processed books to different folder
```

### OCR Quality Issues:
```powershell
# Improve OCR quality
# 1. Use higher DPI: dpi=400 instead of 300
# 2. Pre-process images (deskew, denoise)
# 3. Try different OCR configurations
```

### ChromaDB Connection Issues:
```powershell
# Check ChromaDB container
docker ps | findstr chromadb

# Restart if needed
docker restart chromadb

# Check connection
curl http://localhost:8000/api/v1/heartbeat
```

## Advanced Usage:

### Custom Chunking Parameters:
```python
# In process_unani_books.py, modify:
self.chunk_size = 500      # Larger chunks
self.chunk_overlap = 100   # More overlap
```

### Custom Metadata:
```python
# Add custom metadata extraction
def _extract_metadata(self, pdf_path, chunk_start, chunk_end):
    # Add your custom metadata logic
    metadata["custom_field"] = "custom_value"
    return metadata
```

### Batch Processing:
```powershell
# Process multiple collections
python process_unani_books.py --folder "./books/ayurveda" --collection "ayurveda_books"
python process_unani_books.py --folder "./books/homeopathy" --collection "homeopathy_books"
```

## Performance Tips:

### ১. Parallel Processing:
```python
# For faster processing, consider multiprocessing
# (Requires modification of the script)
```

### ২. Caching:
```python
# Cache embeddings to avoid recomputation
# Store processed file hashes
```

### ৩. Resource Management:
```powershell
# Monitor system resources during processing
# Adjust chunk sizes based on available memory
```

## Integration with n8n:

এই processed data n8n workflow-এ RAG হিসেবে ব্যবহার করা যাবে:

### ১. Query Endpoint তৈরি করুন:
```python
# Add query function to retrieve relevant chunks
def query_collection(query_text, n_results=5):
    embedding = self._generate_embedding(query_text)
    results = self.collection.query(
        query_embeddings=[embedding],
        n_results=n_results,
        include=["documents", "metadatas"]
    )
    return results
```

### ২. n8n HTTP Request Node:
```json
{
  "method": "POST",
  "url": "http://localhost:8003/query",
  "body": {
    "query": "user question",
    "collection": "unani_books",
    "n_results": 3
  }
}
```

## Next Steps:

### ১. Query Interface:
- FastAPI endpoint তৈরি করুন ChromaDB query এর জন্য
- n8n থেকে query করার সুবিধা

### ২. RAG Integration:
- Ollama LLM-এ retrieved context pass করুন
- System prompt-এ relevant books info যোগ করুন

### ৩. Quality Improvement:
- Better OCR preprocessing
- Advanced chunking strategies
- Metadata enrichment

### ৪. Maintenance:
- Regular re-indexing for new books
- Quality monitoring and metrics
- Backup and recovery procedures