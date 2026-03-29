import streamlit as st
import requests
import time

API_URL = "http://localhost:8000"

st.set_page_config(page_title="RAG College Project", page_icon="📚")
st.title("📚 Smart Document Assistant")

# --- 1. INITIALIZE MEMORY (SESSION STATE) ---
if "messages" not in st.session_state:
    st.session_state.messages = []  # Stores the chat history
if "current_doc" not in st.session_state:
    st.session_state.current_doc = None  # Stores the name of the uploaded PDF
if "suggestions" not in st.session_state:
    st.session_state.suggestions = [] # Stores AI-generated questions

# --- 2. SIDEBAR UI (DOCUMENT MANAGEMENT) ---
with st.sidebar:
    st.header("⚙️ Document Management")
    
    # Show active document and give the option to delete it
    if st.session_state.current_doc:
        st.success(f"**Currently Active:**\n{st.session_state.current_doc}")
        
        if st.button("🗑️ Delete Current Document"):
            requests.delete(f"{API_URL}/delete") # Tell backend to wipe DB
            st.session_state.current_doc = None  # Wipe frontend memory
            st.session_state.messages = []       # Wipe chat history
            st.session_state.suggestions = []    # Wipe suggestions
            st.rerun()                           # Refresh the page
    else:
        st.info("No document currently loaded.")

    st.divider()
    
    # Upload New Document Section
    st.subheader("📤 Upload New Document")
    st.warning("⚠️ **Note:** Uploading a new document will completely erase the past conversation and free up space from the previous document. You will need to re-upload old documents if you want to query them again.")
    
    uploaded_file = st.file_uploader("Choose a PDF", type="pdf")
    
    if st.button("Process PDF"):
        if uploaded_file is not None:
            with st.spinner("Wiping old data and processing new document..."):
                try:
                    files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")}
                    response = requests.post(f"{API_URL}/upload", files=files)
                    
                    if response.status_code == 200:
                        data = response.json()
                        st.success(data["message"])
                        
                        # Save new document name, wipe old chat, and save suggestions
                        st.session_state.current_doc = uploaded_file.name
                        st.session_state.messages = []
                        st.session_state.suggestions = data.get("suggestions", [])
                        st.rerun() # Refresh the page to update the UI
                    else:
                        st.error(f"Error: {response.text}")
                except Exception as e:
                    st.error(f"Failed to connect to backend: {e}")
        else:
            st.error("Please select a file first.")

# --- 3. MAIN CHAT INTERFACE ---

# The Typewriter Effect Function
def stream_data(text):
    for word in text.split(" "):
        yield word + " "
        time.sleep(0.04) # Speed of the typing

# Display all past conversation history on the screen
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        # If it's an AI message with sources, display them
        if "sources" in msg and msg["sources"]:
            st.caption(f"📚 **Sources:** {', '.join(msg['sources'])}")

# Show Suggestion Buttons (Only if a document is loaded and chat is empty)
if st.session_state.current_doc and len(st.session_state.messages) == 0:
    if st.session_state.suggestions:
        st.write("💡 **Suggested Questions:**")
        cols = st.columns(len(st.session_state.suggestions))
        for i, sug in enumerate(st.session_state.suggestions):
            if cols[i].button(sug):
                st.session_state.button_clicked = sug

# Determine the prompt: either typed by user OR clicked from a suggestion button
prompt = st.chat_input("Ask a question about your document...")
if "button_clicked" in st.session_state:
    prompt = st.session_state.button_clicked
    del st.session_state.button_clicked # Clear it so it doesn't loop forever

# Execute the question
if prompt:
    # Prevent asking questions if no document is uploaded
    if not st.session_state.current_doc:
        st.error("❌ Please upload a document in the sidebar first!")
    else:
        # 1. Show User's question on screen and save it to memory
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
            
        # 2. Ask the Backend
        with st.spinner("Thinking..."):
            try:
                response = requests.post(f"{API_URL}/ask", json={"question": prompt})
                if response.status_code == 200:
                    data = response.json()
                    answer = data.get("answer", "Error getting answer.")
                    sources = data.get("sources", [])
                    
                    # 3. Show AI's answer with Typewriter Effect and save to memory
                    with st.chat_message("assistant"):
                        st.write_stream(stream_data(answer))
                        if sources:
                            st.caption(f"📚 **Sources:** {', '.join(sources)}")
                            
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": answer,
                        "sources": sources
                    })
                else:
                    st.error("Error asking question.")
            except Exception as e:
                st.error(f"Backend connection error: {e}")