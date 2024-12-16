import os
from flask import Flask, request, jsonify, render_template
from langchain.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import FAISS
from langchain.chains import RetrievalQA
from langchain.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
import glob
from dotenv import load_dotenv
from prompt import prompt_template
app = Flask(__name__)

# Load environment variables from .env file
load_dotenv()

# Get API key from environment variables
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")

def process_pdfs(pdf_directory):
    # Initialize empty list to store all documents
    all_documents = []
    
    # Get all PDF files in the directory
    pdf_files = glob.glob(os.path.join(pdf_directory, "*.pdf"))
    
    # Process each PDF file
    for pdf_path in pdf_files:
        loader = PyPDFLoader(pdf_path)
        documents = loader.load()
        all_documents.extend(documents)
    
    # Split documents into chunks
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len
    )
    texts = text_splitter.split_documents(all_documents)
    
    # Create embeddings and vector store
    embeddings = OpenAIEmbeddings()
    vectorstore = FAISS.from_documents(texts, embeddings)
    
    return vectorstore

def setup_qa_chain(vectorstore, PROMPT):

    # Create a retrieval chain
    qa_chain = RetrievalQA.from_chain_type(
        llm=ChatOpenAI(
            model_name="gpt-4o-mini",
            temperature=0.1,
            max_tokens=1000
        ),
        chain_type="stuff",
        retriever=vectorstore.as_retriever(
            search_kwargs={"k": 6}
        ),
        return_source_documents=True,
        chain_type_kwargs={"prompt": PROMPT}
    )
    return qa_chain


PROMPT = PromptTemplate(
    template=prompt_template, 
    input_variables=["context", "question"]
)


# Initialize the vector store and QA chain
PDF_DIRECTORY = "/home/alignminds/Desktop/Alignminds/RAG_Chatbot/RDBMS"
vectorstore = process_pdfs(PDF_DIRECTORY)
qa_chain = setup_qa_chain(vectorstore, PROMPT)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/ask', methods=['POST'])
def ask_question():
    try:
        data = request.get_json()
        question = data.get('question')
        
        if not question:
            return jsonify({"error": "No question provided"}), 400
        
        # Add logging
        print(f"Processing question: {question}")
        
        # Get answer from the QA chain
        result = qa_chain({"query": question})
        
        # Count words in the response
        word_count = len(result["result"].split())
        
        # Extract source documents information
        sources = []
        for doc in result.get("source_documents", []):
            sources.append({
                "page": doc.metadata.get("page", "Unknown"),
                "source": doc.metadata.get("source", "Unknown")
            })
        
        response = {
            "answer": result["result"],
            "word_count": word_count,
            "sources": sources
        }
        print("Response is...", response)
        print(f"Response word count: {word_count}")
        return jsonify(response)
        
    except Exception as e:
        print(f"Error occurred: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
