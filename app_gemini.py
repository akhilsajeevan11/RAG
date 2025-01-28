import os
from flask import Flask, request, jsonify, render_template, session
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
from prompt import prompt_template, follow_up_prompt, relevancy_prompt
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from typing import Dict, List
from collections import defaultdict
from threading import Lock
import uuid

import traceback
from flask_cors import CORS



app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Add a secret key for session management
app.secret_key = os.urandom(24)

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

# Create separate dictionaries for each user session
user_topic_chains = defaultdict(dict)
user_chat_histories = defaultdict(lambda: defaultdict(list))
topic_locks = defaultdict(Lock)

@app.before_request
def before_request():
    # Create a unique session ID for each user if they don't have one
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())

def setup_qa_chain(vectorstore, PROMPT):
    # Initialize the language model
    llm = ChatGoogleGenerativeAI(
        model="gemini-pro",
        google_api_key=GOOGLE_API_KEY,
        temperature=0.1,
        max_tokens=4096
    )
    
    # Create the QA chain
    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=vectorstore.as_retriever(
            search_type="mmr",
            search_kwargs={
                "k": 6,
                "fetch_k": 8,
                "lambda_mult": 0.7
            }
        ),
        return_source_documents=True,
        chain_type_kwargs={"prompt": PROMPT, "verbose": True}
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

# @app.route('/get-topics', methods=['GET'])
# def get_topics():
#     # Get all subdirectories in the PDF directory
#     topics = [d for d in os.listdir(BASE_DIR) if os.path.isdir(os.path.join(BASE_DIR, d))]
#     return jsonify({"topics": topics})


@app.route('/get-topics', methods=['GET'])
def get_topics():
    try:
        print(f"Checking PDF directory: {BASE_DIR}")
        if not os.path.exists(BASE_DIR):
            print(f"❌ PDF directory missing at: {BASE_DIR}")
            return jsonify({"topics": []})

        print(f"Listing directories in {BASE_DIR}...")
        dir_list = os.listdir(BASE_DIR)
        print(f"Found entries: {dir_list}")
        
        topics = []
        for entry in dir_list:
            dir_path = os.path.join(BASE_DIR, entry)
            print(f"Checking {dir_path}...")
            if os.path.isdir(dir_path) and not entry.startswith('.'):
                print(f"✅ Valid topic found: {entry}")
                topics.append(entry)

        print(f"Returning topics: {topics}")
        return jsonify({"topics": sorted(topics)})

    except Exception as e:
        print(f"🔥 Critical error in get-topics: {traceback.format_exc()}")
        return jsonify({"topics": []}), 500


@app.route('/initialize-topic', methods=['POST'])
def initialize_topic():
    try:
        user_id = session['user_id']
        data = request.get_json()
        topic = data.get('topic')
        
        if not topic:
            return jsonify({"success": False, "error": "No topic provided"}), 400
            
        topic_dir = os.path.join(BASE_DIR, topic)
        if not os.path.exists(topic_dir):
            return jsonify({"success": False, "error": "Topic directory not found"}), 404
            
        # Initialize topic for specific user if not already done
        if topic not in user_topic_chains[user_id]:
            print(f"Initializing embeddings for topic: {topic} for user: {user_id}")
            with topic_locks[topic]:  # Thread-safe operation
                vectorstore = process_pdfs(topic_dir)
                qa_chain = setup_qa_chain(vectorstore, PROMPT)
                user_topic_chains[user_id][topic] = qa_chain
            print(f"Finished initializing {topic} for user: {user_id}")
            
        return jsonify({
            "success": True,
            "message": f"Topic {topic} initialized successfully"
        })
        
    except Exception as e:
        print(f"Error occurred for user {session.get('user_id')}: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# @app.route('/ask', methods=['POST'])
# def ask_question():
#     try:
#         user_id = session['user_id']
#         data = request.get_json()
#         question = data.get('question')
#         topic = data.get('topic')
        
#         print(f"Received question from user {user_id}: {question} for topic: {topic}")

#         if not question or not topic:
#             return jsonify({"error": "Missing question or topic"}), 400

#         # Use user-specific topic chains
#         if topic not in user_topic_chains[user_id]:
#             return jsonify({"error": "Topic not initialized"}), 400

#         # Get user-specific chat history
#         if topic not in user_chat_histories[user_id]:
#             user_chat_histories[user_id][topic] = []

#         with topic_locks[topic]:  # Thread-safe operation
#             llm = ChatGoogleGenerativeAI(
#                 model="gemini-pro",
#                 google_api_key=GOOGLE_API_KEY,
#                 temperature=0
#             )

#             # Check for follow-up using user-specific history
#             is_follow_up = llm.predict(follow_up_prompt.format(
#                 question=question
#             )).strip().lower() == 'yes'

#             if is_follow_up and user_chat_histories[user_id][topic]:
#                 last_question = user_chat_histories[user_id][topic][-1]["question"]
#                 enhanced_question = f"{last_question} {question}"
#                 result = user_topic_chains[user_id][topic]({"query": enhanced_question})
#             else:
#                 relevancy_check = llm.predict(relevancy_prompt.format(
#                     topic=topic,
#                     question=question
#                 )).strip().lower()
                
#                 if relevancy_check != 'yes':
#                     return jsonify({
#                         "answer": f"I apologize, but this question doesn't seem to be related to {topic}.",
#                         "word_count": 0,
#                         "sources": []
#                     })
                
#                 result = user_topic_chains[user_id][topic]({"query": question})

#             # Store in user-specific chat history
#             if not is_follow_up:
#                 user_chat_histories[user_id][topic].append({
#                     "question": question,
#                     "answer": result["result"]
#                 })

#             word_count = len(result["result"].split())
            
#             sources = []
#             for doc in result.get("source_documents", []):
#                 sources.append({
#                     "page": doc.metadata.get("page", "Unknown"),
#                     "source": doc.metadata.get("source", "Unknown")
#                 })
            
#             response = {
#                 "answer": result["result"],
#                 "word_count": word_count,
#                 "sources": sources,
#                 "topic": topic
#             }
#             print("Response is...", response)
#             print("Chat history is...", user_chat_histories)
#             print("Word count is...", word_count)
#             return jsonify(response)

#     except Exception as e:
#         print(f"Error occurred for user {session.get('user_id')}: {str(e)}")
#         return jsonify({"error": str(e)}), 500



@app.route('/ask', methods=['POST'])
def ask_question():
    try:
        user_id = session['user_id']
        data = request.get_json()
        question = data.get('question')
        topic = data.get('topic')

        print(f"Received question from user {user_id}: {question} for topic: {topic}")

        if not question or not topic:
            return jsonify({"error": "Missing question or topic"}), 400

        if topic not in user_topic_chains[user_id]:
            return jsonify({"error": "Topic not initialized"}), 400

        # Get chat history for this user and topic
        chat_history = user_chat_histories[user_id][topic]

        with topic_locks[topic]:  # Thread-safe operation
            llm = ChatGoogleGenerativeAI(
                model="gemini-pro",
                google_api_key=GOOGLE_API_KEY,
                temperature=0
            )

            # Determine follow-up
            is_follow_up = llm.predict(follow_up_prompt.format(
                question=question
            )).strip().lower() == 'yes'

            if is_follow_up and chat_history:
                last_question = chat_history[-1]["question"]
                enhanced_question = f"{last_question} {question}"
                result = user_topic_chains[user_id][topic]({"query": enhanced_question})
            else:
                relevancy_check = llm.predict(relevancy_prompt.format(
                    topic=topic,
                    question=question
                )).strip().lower()

                if relevancy_check != 'yes':
                    return jsonify({
                        "answer": f"I apologize, but this question doesn't seem to be related to {topic}.",
                        "word_count": 0,
                        "sources": []
                    })

                result = user_topic_chains[user_id][topic]({"query": question})

            # Store the question-answer pair in chat history
            chat_history.append({
                "question": question,
                "answer": result["result"]
            })

            # Extract word count and sources
            word_count = len(result["result"].split())
            sources = [
                {
                    "page": doc.metadata.get("page", "Unknown"),
                    "source": doc.metadata.get("source", "Unknown")
                }
                for doc in result.get("source_documents", [])
            ]

            response = {
                "answer": result["result"],
                "word_count": word_count,
                "sources": sources,
                "topic": topic
            }
            print("Response:", response)
            print("Updated Chat History:", user_chat_histories)
            return jsonify(response)

    except Exception as e:
        print(f"Error occurred for user {session.get('user_id')}: {str(e)}")
        return jsonify({"error": str(e)}), 500






# Add cleanup function to remove old sessions periodically
def cleanup_old_sessions():
    # Implement session cleanup logic here
    pass

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', threaded=True, port=5000)
