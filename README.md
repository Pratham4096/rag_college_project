# 📚 Smart Document Assistant (RAG Pipeline)

An enterprise-grade Retrieval-Augmented Generation (RAG) application built to chat with multiple PDF documents. This project utilizes a decoupled architecture with a FastAPI backend and a Streamlit frontend, ensuring high performance, scalability, and an excellent user experience.

## ✨ Key Features
* **Multi-Document Management:** Upload PDFs dynamically with automatic state tracking.
* **Smart Context Retrieval:** Implements Maximal Marginal Relevance (MMR) search to prevent "tunnel vision" and ensure diverse context gathering.
* **Auto-Suggested Queries:** AI-generated suggested questions appear instantly upon document upload.
* **Source Citations:** Mathematically proves AI accuracy by returning the exact page numbers used to generate the answer.
* **Streaming Responses:** Real-time typewriter effect for a seamless, ChatGPT-like user experience.
* **Memory Management:** Full CRUD capabilities for the vector database, allowing users to wipe old documents and free up system memory.

## 🛠️ Technology Stack
* **Frontend:** Streamlit
* **Backend:** FastAPI, Uvicorn
* **AI & Orchestration:** LangChain, Google Gemini 2.5 Flash
* **Embeddings:** HuggingFace (`all-MiniLM-L6-v2`)
* **Vector Database:** ChromaDB

## 🚀 How to Run Locally

### 1. Clone the Repository
```bash
git clone [https://github.com/Pratham4096/rag_college_project.git](https://github.com/Pratham4096/rag_college_project.git)
cd rag_college_project
```

### 2. Set Up the Environment
Create a virtual environment and install the required dependencies:

```Bash
python -m venv venv
venv\Scripts\activate
pip install fastapi uvicorn streamlit pydantic langchain langchain-google-genai langchain-community langchain-huggingface chromadb pypdf python-dotenv
```

### 3. Add Your API Key
Create a .env file in the root directory and add your Google Gemini API key:

```Plaintext
GOOGLE_API_KEY="your_api_key_here"
```

### 4. Start the Backend Server
Open a terminal and run the FastAPI server:

```Bash
python backend/main.py
The API will be available at http://localhost:8000
```

### 5. Start the Frontend Application
Open a second terminal, ensure the virtual environment is activated, and run:

```Bash
streamlit run frontend/app.py
The UI will be available at http://localhost:8501
```

🧠 System Architecture
Ingestion: PDFs are parsed using PyPDFLoader and split into chunks (1500 chars, 300 overlap) using RecursiveCharacterTextSplitter.

Embedding: Text chunks are converted into dense vectors using HuggingFace's open-source MiniLM model running locally.

Storage: Vectors are persisted locally in a ChromaDB database.

Retrieval: User queries are vectorized and matched against the database using MMR (k=5, fetch_k=20).

Generation: Context and queries are passed to Gemini via LangChain prompt templates to synthesize a final, cited response.

