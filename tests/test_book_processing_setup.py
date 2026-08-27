#!/usr/bin/env python3
"""
Test script to verify all dependencies for book processing are properly installed.
"""

import sys
import subprocess
from pathlib import Path

def test_python_packages():
    """Test if all required Python packages are installed."""
    print("Testing Python packages...")
    
    required_packages = [
        "PyPDF2",
        "pdf2image", 
        "PIL",  # Pillow
        "pytesseract",
        "tiktoken",
        "requests",
        "chromadb"
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✓ {package} is installed")
        except ImportError:
            print(f"✗ {package} is NOT installed")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\nMissing packages: {', '.join(missing_packages)}")
        print("Install with: pip install -r book_processing_requirements.txt")
        return False
    
    print("All Python packages are installed ✓")
    return True

def test_tesseract():
    """Test if Tesseract OCR is installed and accessible."""
    print("\nTesting Tesseract OCR...")
    
    try:
        result = subprocess.run(['tesseract', '--version'], 
                             capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            version = result.stdout.split('\n')[0]
            print(f"✓ Tesseract is installed: {version}")
            
            # Test Bengali language data
            result = subprocess.run(['tesseract', '--list-langs'], 
                                   capture_output=True, text=True, timeout=5)
            if 'ben' in result.stdout:
                print("✓ Bengali language data is available")
            else:
                print("✗ Bengali language data is NOT available")
                print("Install Bengali language pack for Tesseract")
                return False
            
            return True
        else:
            print("✗ Tesseract is NOT properly installed")
            return False
    except (subprocess.TimeoutExpired, FileNotFoundError):
        print("✗ Tesseract is NOT found in PATH")
        print("Install Tesseract OCR from: https://github.com/UB-Mannheim/tesseract/wiki")
        return False

def test_poppler():
    """Test if Poppler is installed (required for pdf2image)."""
    print("\nTesting Poppler...")
    
    try:
        # Test for pdftoppm (part of poppler)
        result = subprocess.run(['pdftoppm', '-h'], 
                             capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("✓ Poppler is installed")
            return True
        else:
            print("✗ Poppler is NOT properly installed")
            return False
    except (subprocess.TimeoutExpired, FileNotFoundError):
        print("✗ Poppler is NOT found in PATH")
        print("Install Poppler from: https://github.com/oschwartz10612/poppler-windows/releases/")
        return False

def test_ollama():
    """Test if Ollama is running and nomic-embed-text is available."""
    print("\nTesting Ollama...")
    
    try:
        import requests
        
        # Test Ollama connection
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            print("✓ Ollama is running")
            
            # Check for nomic-embed-text model
            models = response.json().get("models", [])
            model_names = [model.get("name", "") for model in models]
            
            if any("nomic-embed-text" in name for name in model_names):
                print("✓ nomic-embed-text model is available")
                return True
            else:
                print("✗ nomic-embed-text model is NOT available")
                print("Install with: ollama pull nomic-embed-text")
                return False
        else:
            print("✗ Ollama is NOT responding")
            print("Start Ollama with: ollama serve")
            return False
    except requests.exceptions.RequestException:
        print("✗ Cannot connect to Ollama")
        print("Start Ollama with: ollama serve")
        return False

def test_chromadb():
    """Test if ChromaDB is accessible."""
    print("\nTesting ChromaDB...")
    
    try:
        import chromadb
        
        # Test persistent client
        try:
            client = chromadb.PersistentClient(path="./test_chroma_db")
            print("✓ ChromaDB client can be created")
            
            # Test collection creation
            test_collection = client.create_collection(name="test_collection")
            print("✓ ChromaDB collection can be created")
            
            # Cleanup
            client.delete_collection("test_collection")
            import shutil
            shutil.rmtree("./test_chroma_db", ignore_errors=True)
            
            return True
        except Exception as e:
            print(f"✗ ChromaDB client error: {e}")
            return False
            
    except ImportError:
        print("✗ ChromaDB package is NOT installed")
        return False

def test_directory_structure():
    """Test if books directory exists and contains PDFs."""
    print("\nTesting directory structure...")
    
    books_folder = Path("./books")
    
    if not books_folder.exists():
        print(f"✗ Books folder does not exist: {books_folder}")
        print("Create books folder and add PDF files")
        return False
    
    pdf_files = list(books_folder.glob("*.pdf"))
    
    if not pdf_files:
        print(f"✗ No PDF files found in {books_folder}")
        print("Add PDF files to the books folder")
        return False
    
    print(f"✓ Books folder exists with {len(pdf_files)} PDF file(s)")
    return True

def main():
    print("="*50)
    print("BOOK PROCESSING SETUP TEST")
    print("="*50)
    
    tests = [
        ("Python Packages", test_python_packages),
        ("Tesseract OCR", test_tesseract),
        ("Poppler", test_poppler),
        ("Ollama", test_ollama),
        ("ChromaDB", test_chromadb),
        ("Directory Structure", test_directory_structure)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"✗ {test_name} test failed with error: {e}")
            results.append((test_name, False))
    
    print("\n" + "="*50)
    print("TEST SUMMARY")
    print("="*50)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{test_name}: {status}")
    
    all_passed = all(result for _, result in results)
    
    if all_passed:
        print("\n🎉 All tests passed! You can run the book processing script.")
        return 0
    else:
        print("\n❌ Some tests failed. Please fix the issues above before processing.")
        return 1

if __name__ == "__main__":
    sys.exit(main())