import os
from flask import Flask, request, jsonify, render_template
from langchain.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores import FAISS
from langchain.chains import RetrievalQA
from langchain.llms import GooglePalm
import google.generativeai as genai
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
import glob
from dotenv import load_dotenv
from prompt import prompt_template
from langchain_google_genai import GoogleGenerativeAIEmbeddings

app = Flask(__name__)

# Load environment variables from .env file
load_dotenv()

# Configure Google API
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)

# Define base directory for PDF files
BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "PDF")
print(f"Looking for PDFs in: {BASE_DIR}")

# Define the prompt template
PROMPT = PromptTemplate(
    template=prompt_template,  # This comes from your imported prompt.py
    input_variables=["context", "question"]
)

# Initialize empty dictionary for topic chains
topic_chains = {}

def setup_qa_chain(vectorstore, prompt):
    # Initialize the language model
    llm = ChatGoogleGenerativeAI(
        model="gemini-pro",
        google_api_key=GOOGLE_API_KEY,
        temperature=0.3
    )
    
    # Create the QA chain
    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=vectorstore.as_retriever(),
        return_source_documents=True,
        chain_type_kwargs={"prompt": prompt}
    )
    
    return qa_chain

def process_pdfs(pdf_directory):
    # Initialize empty list to store all documents
    all_documents = []
    
    # Get all PDF files in the directory
    pdf_files = glob.glob(os.path.join(pdf_directory, "*.pdf"))
    
    # Add debug logging
    print(f"Found {len(pdf_files)} PDF files in directory: {pdf_directory}")
    print("PDF files:", pdf_files)
    
    # Process each PDF file
    for pdf_path in pdf_files:
        loader = PyPDFLoader(pdf_path)
        documents = loader.load()
        all_documents.extend(documents)
    
    # Add debug logging
    print(f"Processed {len(all_documents)} documents total")
    
    # Split documents into chunks
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len
    )
    texts = text_splitter.split_documents(all_documents)
    
    # Add debug logging
    print(f"Created {len(texts)} text chunks")
    
    # Create embeddings and vector store using Google Palm embeddings
    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/embedding-001",
        google_api_key=GOOGLE_API_KEY
    )
    
    if not texts:
        raise ValueError("No texts to process. Please check if PDFs contain extractable text.")
        
    vectorstore = FAISS.from_documents(texts, embeddings)
    return vectorstore

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/get-topics', methods=['GET'])
def get_topics():
    # Get all subdirectories in the PDF directory
    topics = [d for d in os.listdir(BASE_DIR) if os.path.isdir(os.path.join(BASE_DIR, d))]
    return jsonify({"topics": topics})

@app.route('/initialize-topic', methods=['POST'])
def initialize_topic():
    try:
        data = request.get_json()
        topic = data.get('topic')
        
        if not topic:
            return jsonify({"success": False, "error": "No topic provided"}), 400
            
        # Check if topic directory exists
        topic_dir = os.path.join(BASE_DIR, topic)
        if not os.path.exists(topic_dir):
            return jsonify({"success": False, "error": "Topic directory not found"}), 404
            
        # Only process if not already initialized
        if topic not in topic_chains:
            print(f"Initializing embeddings for topic: {topic}")
            vectorstore = process_pdfs(topic_dir)
            qa_chain = setup_qa_chain(vectorstore, PROMPT)
            topic_chains[topic] = qa_chain
            print(f"Finished initializing {topic}")
            
        return jsonify({
            "success": True,
            "message": f"Topic {topic} initialized successfully"
        })
        
    except Exception as e:
        print(f"Error occurred: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/ask', methods=['POST'])
def ask_question():
    try:
        data = request.get_json()
        question = data.get('question')
        topic = data.get('topic')
        
        print(f"Received question: {question} for topic: {topic}")

        if not question:
            return jsonify({"error": "No question provided"}), 400
            
        if not topic:
            return jsonify({"error": "No topic selected"}), 400
            
        if topic not in topic_chains:
            return jsonify({"error": "Invalid topic"}), 400
        
        result = topic_chains[topic]({"query": question})
        
        word_count = len(result["result"].split())
        
        sources = []
        for doc in result.get("source_documents", []):
            sources.append({
                "page": doc.metadata.get("page", "Unknown"),
                "source": doc.metadata.get("source", "Unknown")
            })
        
        response = {
            "answer": result["result"],
            "word_count": word_count,
            "sources": sources,
            "topic": topic
        }

        print("Response is...", response)
        print(f"Response word count: {word_count}")

        return jsonify(response)
    
    
        
    except Exception as e:
        print(f"Error occurred: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
