import sys
print("---- DIAGNOSTIC INFO ----")
print("Python is running from:", sys.executable)
print("-------------------------")

import os
import shutil
from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_classic.chains import create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
import os
from dotenv import load_dotenv

# This automatically loads the GOOGLE_API_KEY from your .env file!
load_dotenv() 

app = FastAPI()

embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

# Windows-friendly path for the database
db_path = os.path.join(os.getcwd(), "chroma_db")
vector_store = Chroma(embedding_function=embeddings, persist_directory=db_path)

# Ensure this matches the correct Google model name
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")

class QuestionRequest(BaseModel):
    question: str

@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    global vector_store  # Tell Python we are modifying the main database
    
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    data_dir = os.path.join("..", "data")
    os.makedirs(data_dir, exist_ok=True)
    file_path = os.path.join(data_dir, file.filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    loader = PyPDFLoader(file_path)
    docs = loader.load()
    
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=300)
    splits = text_splitter.split_documents(docs)
    
    # --- WIPE THE OLD DATA BEFORE ADDING NEW DATA ---
    try:
        vector_store.delete_collection() # Destroys the old document data
    except:
        pass # Ignore if it's already empty
        
    # Re-initialize a completely fresh, empty database room
    vector_store = Chroma(embedding_function=embeddings, persist_directory=db_path)
    
    vector_store.add_documents(splits) # Add the new PDF data

    # --- GENERATE SUGGESTED QUESTIONS ---
    try:
        # Ask the AI to quickly read the first chunk and guess 3 questions
        suggestion_prompt = f"Based on this text, generate 3 short, specific questions a user could ask. Return ONLY the 3 questions separated by a pipe symbol (|). Text: {splits[0].page_content[:1000]}"
        suggestions_raw = llm.invoke(suggestion_prompt)
        suggestions_text = suggestions_raw.content if hasattr(suggestions_raw, 'content') else str(suggestions_raw)
        
        # Clean up the output into a Python list
        suggestions = [s.strip() for s in suggestions_text.split('|') if s.strip()][:3]
    except Exception:
        # Fallback if the AI is too slow or errors out
        suggestions = ["What is the main topic of this document?", "Can you summarize this?", "What are the key takeaways?"]

    return {
        "message": f"Successfully processed {len(splits)} chunks of text from {file.filename}!",
        "suggestions": suggestions # Send them to the frontend
    }

@app.delete("/delete")
async def delete_document():
    global vector_store
    try:
        vector_store.delete_collection()
        vector_store = Chroma(embedding_function=embeddings, persist_directory=db_path)
        return {"message": "Database wiped successfully."}
    except Exception as e:
        return {"message": f"Nothing to delete or error occurred: {str(e)}"}

@app.post("/ask")
async def ask_question(request: QuestionRequest):
    retriever = vector_store.as_retriever(
        search_type="mmr", 
        search_kwargs={"k": 5, "fetch_k": 20}
    )
    
    system_prompt = (
        "You are an expert document analyst. "
        "Carefully review the following pieces of retrieved context to answer the user's question. "
        "Synthesize the information if it is spread across multiple sections. "
        "If the answer is not contained within the context, you must explicitly say: "
        "'I am sorry, but I cannot find the answer to that in the uploaded document.' "
        "Do not invent or guess information. \n\n"
        "Context:\n{context}"
    )
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{input}"),
    ])
    
    question_answer_chain = create_stuff_documents_chain(llm, prompt)
    rag_chain = create_retrieval_chain(retriever, question_answer_chain)
    
    try:
        response = rag_chain.invoke({"input": request.question})
        
        # --- EXTRACT PAGE NUMBERS ---
        sources = []
        for doc in response.get("context", []):
            # PyPDFLoader saves the page number (0-indexed) in the metadata
            page = doc.metadata.get("page", 0)
            sources.append(f"Page {int(page) + 1}")
            
        unique_sources = list(set(sources)) # Remove duplicates
        
        return {
            "answer": response["answer"],
            "sources": unique_sources # Send sources to the frontend
        }
        
    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
            return {"answer": "⚠️ **API Rate Limit Reached.", "sources": []}
        else:
            return {"answer": f"⚠️ **An unexpected AI error occurred:** {error_msg}", "sources": []}

if __name__ == "__main__":
    import uvicorn
    # Running it this way bypasses the Windows multiprocessing bug
    uvicorn.run(app, host="localhost", port=8000)