# RAG Integration Guide for n8n Workflow

## Overview
এই গাইডে n8n workflow-এ Retrieval-Augmented Generation (RAG) integration ব্যাখ্যা করা হয়েছে, যা ইউনানী বইয়ের processed data থেকে relevant context retrieve করে LLM response কে ground করে।

## RAG Pipeline Architecture

### Complete Text Branch with RAG:
```
User Text → Set Text Input → Embed Question → Query ChromaDB → Format Augmented Prompt → Ollama with RAG → Text Response
```

### Complete Voice Branch with RAG:
```
User Voice → Set Voice Data → STT Service → Set Voice Input → Embed Question → Query ChromaDB → Format Augmented Prompt → Ollama with RAG → TTS Service → Audio Response
```

## New Nodes Configuration

### ১. Embed Question (Text/Voice) - HTTP Request Node

**Purpose:** User question কে vector embedding-এ রূপান্তর করা

**Configuration:**
- Method: POST
- URL: `http://localhost:11434/api/embed`
- Send Body: True
- Specify Body: JSON

**JSON Body:**
```json
{
  "model": "nomic-embed-text",
  "prompt": "={{ $json.user_input }}"
}
```

**Response:** `{ "embedding": [0.1, 0.2, 0.3, ...] }`

### ২. Query ChromaDB (Text/Voice) - HTTP Request Node

**Purpose:** Embedding দিয়ে ChromaDB থেকে top-4 relevant chunks retrieve করা

**Configuration:**
- Method: POST
- URL: `http://localhost:8000/api/v1/collections/unani_books/query`
- Send Body: True
- Specify Body: JSON

**JSON Body:**
```json
{
  "query_embeddings": [={{ $json.embedding }}],
  "n_results": 4,
  "include": ["documents", "metadatas", "distances"]
}
```

**Response Format:**
```json
{
  "ids": [["id1", "id2", "id3", "id4"]],
  "documents": [["chunk1 text", "chunk2 text", "chunk3 text", "chunk4 text"]],
  "metadatas": [[
    {"book_name": "book1", "page": 1},
    {"book_name": "book2", "page": 5},
    {"book_name": "book1", "page": 10},
    {"book_name": "book3", "page": 2}
  ]],
  "distances": [[0.1, 0.2, 0.3, 0.4]]
}
```

### ৩. Format Augmented Prompt (Text/Voice) - Code Node

**Purpose:** Retrieved chunks কে structured format-এ augmented prompt-এ বসানো

**JavaScript Code:**
```javascript
// Format retrieved chunks into augmented prompt
const chunks = $input.all();
const user_input = $('Set Text Input').item.json.user_input; // or 'Set Voice Input' for voice branch

let referenceText = "";

if (chunks && chunks.length > 0) {
  const firstChunk = chunks[0].json;
  
  if (firstChunk.documents && firstChunk.documents[0]) {
    const documents = firstChunk.documents[0];
    const metadatas = firstChunk.metadatas ? firstChunk.metadatas[0] : [];
    
    for (let i = 0; i < documents.length; i++) {
      const doc = documents[i];
      const meta = metadatas[i] || {};
      const bookName = meta.book_name || 'Unknown Book';
      const pageNum = meta.estimated_page || 'Unknown Page';
      
      referenceText += `[${bookName} - Page ${pageNum}]:\n${doc}\n\n`;
    }
  }
}

if (!referenceText) {
  referenceText = "কোনো প্রাসঙ্গিক তথ্য পাওয়া যায়নি।";
}

const augmentedPrompt = `নিচের রেফারেন্স অংশগুলো ব্যবহার করে প্রশ্নের উত্তর দাও। রেফারেন্সে না থাকলে অনুমান করে বানিয়ে বোলো না, বরং জানাও যে এই বিষয়ে নির্দিষ্ট তথ্য নেই:\n\n${referenceText}\n\nপ্রশ্ন: ${user_input}`;

return {
  json: {
    augmented_prompt: augmentedPrompt,
    user_input: user_input,
    reference_count: referenceText ? (chunks[0].json.documents[0]?.length || 0) : 0
  }
};
```

**Output:** `{ "augmented_prompt": "...", "user_input": "...", "reference_count": 4 }`

### ৪. Call Ollama with RAG (Text/Voice) - HTTP Request Node

**Purpose:** Augmented prompt দিয়ে grounded response generate করা

**Configuration:**
- Method: POST
- URL: `http://localhost:11434/api/chat`
- Send Body: True
- Specify Body: JSON

**JSON Body:**
```json
{
  "model": "llama3.1:8b",
  "messages": [
    {
      "role": "system",
      "content": "তুমি একজন সহায়ক ইউনানী স্বাস্থ্য-তথ্য সহকারী। তুমি প্রকৃত হাকিম/ডাক্তারের বিকল্প নও, শুধু সাধারণ তথ্য দাও এবং জটিল/গুরুতর ক্ষেত্রে সবসময় একজন প্রকৃত হাকিম দেখানোর পরামর্শ দাও। তুমি শুধুমাত্র প্রদত্ত রেফারেন্স বইয়ের অংশ থেকে তথ্য ব্যবহার করবে। রেফারেন্সে না থাকলে অনুমান করে উত্তর দেবে না।"
    },
    {
      "role": "user",
      "content": "={{ $json.augmented_prompt }}"
    }
  ],
  "stream": false,
  "options": {
    "temperature": 0.7,
    "max_tokens": 500
  }
}
```

## Grounding Improvements

### Enhanced System Prompt:
```
"তুমি একজন সহায়ক ইউনানী স্বাস্থ্য-তথ্য সহকারী। তুমি প্রকৃত হাকিম/ডাক্তারের বিকল্প নও, শুধু সাধারণ তথ্য দাও এবং জটিল/গুরুতর ক্ষেত্রে সবসময় একজন প্রকৃত হাকিম দেখানোর পরামর্শ দাও। তুমি শুধুমাত্র প্রদত্ত রেফারেন্স বইয়ের অংশ থেকে তথ্য ব্যবহার করবে। রেফারেন্সে না থাকলে অনুমান করে উত্তর দেবে না।"
```

**Key Grounding Instructions:**
- **Context Restriction:** শুধুমাত্র প্রদত্ত reference ব্যবহার করতে হবে
- **No Hallucination:** রেফারেন্সে না থাকলে অনুমান করা যাবে না
- **Source Attribution:** উত্তরে book এবং page reference থাকতে পারে
- **Medical Disclaimer:** জটিল cases-এ real doctor দেখানোর পরামর্শ

## Augmented Prompt Template

### Structure:
```
নিচের রেফারেন্স অংশগুলো ব্যবহার করে প্রশ্নের উত্তর দাও। রেফারেন্সে না থাকলে অনুমান করে বানিয়ে বোলো না, বরং জানাও যে এই বিষয়ে নির্দিষ্ট তথ্য নেই:

[Book Name - Page X]:
chunk content 1

[Book Name - Page Y]:
chunk content 2

[Book Name - Page Z]:
chunk content 3

[Book Name - Page W]:
chunk content 4

প্রশ্ন: user_question
```

### Example:
```
নিচের রেফারেন্স অংশগুলো ব্যবহার করে প্রশ্নের উত্তর দাও। রেফারেন্সে না থাকলে অনুমান করে বানিয়ে বোলো না, বরং জানাও যে এই বিষয়ে নির্দিষ্ট তথ্য নেই:

[canonical_medicine_guide - Page 45]:
মাথা ব্যথার জন্য হাকিমরা সাধারণত গোলমরিচের ফোঁটা এবং আদা দিয়ে তৈরি মালিশ প্রয়োগ করেন। এটি রক্ত সঞ্চালন বৃদ্ধি করে এবং ব্যথা উপশম দেয়।

[herbal_remedies_bangla - Page 12]:
মাথা ব্যথার জন্য পুদিনা পাতার রস এবং মধুর মিশ্রণ খুব উপকারী। এটি প্রাকৃতিক ব্যথানাশক হিসেবে কাজ করে।

[unani_treatment_guide - Page 78]:
দীর্ঘস্থায়ী মাথা ব্যথার জন্য হাকিমরা নিয়মিত ঘুমানোর পরামর্শ দেন এবং কফি কমানোর পরামর্শ দেন।

প্রশ্ন: মাথা ব্যথার জন্য কি করব?
```

## Prerequisites Check

### ১. ChromaDB with Indexed Data:
```powershell
# ChromaDB running আছে কিনা চেক করুন
docker ps | findstr chromadb

# Collection exists কিনা চেক করুন
curl http://localhost:8000/api/v1/collections

# Books processed হয়েছে কিনা চেক করুন
# আগের book processing script run করেছেন তো?
```

### ২. Ollama with Embedding Model:
```powershell
# Ollama running আছে কিনা চেক করুন
curl http://localhost:11434/api/tags

# nomic-embed-text model available কিনা চেক করুন
ollama list

# যদি না থাকে:
ollama pull nomic-embed-text
```

### ৩. n8n Workflow Import:
```powershell
# n8n ড্যাশবোর্ডে যান
# facebook-messenger-webhook-workflow-with-rag.json import করুন
# Configuration আপডেট করুন (verify token, credentials, URLs)
```

## Testing the RAG Pipeline

### ১. Text Message Test:
```
User: "মাথা ব্যথার জন্য কি করব?"

Expected Flow:
1. Embed question → vector
2. Query ChromaDB → top-4 relevant chunks
3. Format augmented prompt with references
4. Ollama processes with grounding
5. Response based on book references
```

### ২. Voice Message Test:
```
User: [Voice message "পেটের সমস্যার জন্য কি করব?"]

Expected Flow:
1. STT transcribes voice to text
2. Embed question → vector
3. Query ChromaDB → top-4 relevant chunks
4. Format augmented prompt with references
5. Ollama processes with grounding
6. TTS generates voice response
```

### ৩. No Match Test:
```
User: "মঙ্গল গ্রহের অবস্থান কি?"

Expected Response:
"আপনার প্রশ্নের বিষয়ে ইউনানী বইয়ে নির্দিষ্ট তথ্য পাওয়া যায়নি। এই বিষয়ে তথ্যের জন্য অন্য উৎস সন্ধান করুন।"
```

## Workflow Configuration Details

### ChromaDB Collection Name:
- Default: `unani_books`
- Update if you used different collection name in book processing
- Node URL: `http://localhost:8000/api/v1/collections/YOUR_COLLECTION_NAME/query`

### Number of Retrieved Chunks:
- Default: 4 chunks
- Adjust in Query ChromaDB node: `"n_results": 4`
- More chunks = more context but slower processing

### Embedding Model:
- Default: `nomic-embed-text`
- Ensure same model used for book processing and querying
- Different models = incompatible embeddings

## Troubleshooting

### ChromaDB Connection Failed:
```powershell
# Check ChromaDB container
docker ps | findstr chromadb

# Restart if needed
docker restart chromadb

# Check connection
curl http://localhost:8000/api/v1/heartbeat
```

### No Results from ChromaDB:
```powershell
# Check collection has data
curl http://localhost:8000/api/v1/collections/unani_books/count

# Re-run book processing if needed
python process_unani_books.py --folder "./books" --collection "unani_books"
```

### Embedding Generation Failed:
```powershell
# Check Ollama embedding model
ollama list

# Test embedding
curl -X POST http://localhost:11434/api/embed \
  -H "Content-Type: application/json" \
  -d '{"model": "nomic-embed-text", "prompt": "test"}'
```

### Code Node Errors:
- JavaScript syntax চেক করুন
- Variable references validate করুন
- n8n expressions সঠিক কিনা দেখুন

### Grounding Not Working:
- System prompt চেক করুন
- Augmented prompt format verify করুন
- LLM response analyze করুন

## Performance Optimization

### ১. Reduce Retrieved Chunks:
```json
// Query ChromaDB node
"n_results": 2  // Instead of 4
```

### ২. Caching:
- Frequently asked questions cache করুন
- Embedding results cache করুন

### ৩. Async Processing:
- Voice branch-এ async processing consider করুন
- Background processing for large contexts

## Monitoring and Quality

### Response Quality Monitoring:
- Grounding accuracy track করুন
- Source attribution verify করুন
- Hallucination detection implement করুন

### Metrics to Track:
- Average response time
- Chunk retrieval accuracy
- User satisfaction scores
- Ground adherence percentage

## Next Steps

### ১. Advanced RAG:
- Hybrid search (semantic + keyword)
- Re-ranking of retrieved chunks
- Context window optimization

### ২. Quality Improvement:
- Better chunking strategies
- Multi-hop reasoning
- Source verification

### ৩. User Experience:
- Reference citations in responses
- Confidence scoring
- Alternative suggestions

This RAG integration ensures your AI assistant provides accurate, grounded responses based on the indexed Unani medicine books while maintaining proper medical disclaimers and avoiding hallucinations.