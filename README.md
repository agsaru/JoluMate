# JoluMate

JoluMate is an AI chatbot application designed for interactive   
conversations, secure user authentication, and intelligent       
responses powered by Retrieval Augmented Generation (RAG). Users 
can manage their chat history, engage with the AI assistant, and 
upload PDF documents to provide custom knowledge for
context-aware interactions.

## Table of Contents
*   ✨ [Key Features](#key-features)
*   🛠️ [Tech Stack](#tech-stack)
*   📂 [Folder Structure](#folder-structure)
*   ⚙️ [Installation](#installation)
*   🚀 [Usage](#usage)
*   🌐 [Configuration / Environment
Variables](#configuration--environment-variables)
*   🧠 [How the Code Works](#how-the-code-works)
*   📞 [API Endpoints](#api-endpoints)
*   ⚖️ [License](#license)

## Key Features

*   **User Authentication**: Robust signup, login, logout, and   
token refresh mechanisms using JWT for secure access.
*   **Chatbot Interaction**: Engage in natural language
conversations with an AI assistant powered by a Groq LLM.        
*   **Conversation Management**: View, load, and delete
individual chat conversations, maintaining chat history.
*   **Document Upload**: Upload PDF files which are processed,   
chunked, embedded, and stored to augment the AI's knowledge base.
*   **Retrieval Augmented Generation (RAG)**: The AI agent       
leverages uploaded documents to provide contextually relevant and
informed responses.
*   **LangGraph Workflow**: An asynchronous LangGraph
orchestrates the AI agent's decision-making, tool usage (like    
knowledge base search), and state management.
*   **Persistent Data Storage**: User credentials, refresh       
tokens, conversation history, and document embeddings are        
securely stored in a PostgreSQL database.
*   **Web Interface**: A Streamlit-based client provides an      
intuitive and interactive user interface for accessing chatbot   
functionalities.
*   **Request Logging**: Server-side middleware logs incoming    
HTTP requests for monitoring and debugging.

## Tech Stack

*   **Backend Framework**: FastAPI
*   **Client Framework**: Streamlit
*   **Database**: PostgreSQL
*   **Asynchronous Database Driver**: `psycopg_pool`, `psycopg`  
*   **AI Frameworks**: LangChain, LangGraph
*   **LLM Provider**: Groq
*   **LLM Model**: `llama-3.3-70b-versatile`
*   **Embedding Model**: Google Generative AI
(`models/text-embedding-004`)
*   **Authentication**: JWT (JSON Web Tokens), `passlib` (bcrypt)
*   **HTTP Client**: `requests`
*   **PDF Processing**: `pypdf`
*   **Environment Variables**: `python-dotenv`
*   **Data Validation**: Pydantic
*   **Web Server**: Uvicorn (implied with FastAPI)
*   **Concurrency**: `asyncio`

## Folder Structure

```
JoluMate/
    ├── LICENSE
    └── README.md
    ├── client/
        ├── api.py
        ├── app.py
    ├── db/
        └── formatting.sql
    ├── server/
        ├── main.py
        ├── agent/
            └── graph.py
        ├── auth/
            ├── auth.py
            ├── hash.py
            └── router.py
        ├── chat/
            └── router.py
        ├── configs/
            └── db.py
        ├── conversation/
            └── router.py
        ├── middlewares/
            └── log_requests.py
        ├── rag/
            ├── tools.py
            └── utils.py
```

## Installation

To set up and run JoluMate locally, follow these steps:

### Prerequisites

*   Python 3.9+
*   PostgreSQL database
*   `git`

### 1. Clone the Repository

```bash
git clone <repository_url>
cd JoluMate
```

### 2. Set Up Environment Variables

Create a `.env` file in the root `JoluMate/` directory and       
populate it with the necessary environment variables.

```env
# Client-side
BACKEND_URL="http://localhost:8000" # Or your deployed backend   
URL

# Server-side
GROQ_API_KEY="your_groq_api_key_here"
JWT_SECRET="super_secret_jwt_key" # Change this to a strong,     
random key
DATABASE_URL="postgresql://user:password@host:port/database_name"
GOOGLE_API_KEY="your_google_api_key_here"
```

### 3. Install Dependencies

It is recommended to use a virtual environment.

```bash
python -m venv venv
source venv/bin/activate # On Windows use `venv\Scripts\activate`

pip install -r requirements.txt
```

**`requirements.txt` content (based on file summaries):**        

```
fastapi
streamlit
requests
python-dotenv
uvicorn
psycopg-pool
psycopg # Or psycopg if you prefer source build
langchain-groq
langchain-core
langgraph
python-jose
passlib
pydantic
pypdf
langchain-text-splitters
langchain-google-genai
```

### 4. Database Setup

Ensure you have a PostgreSQL database running. Then, apply the   
schema using the provided SQL script:

```bash
psql -U your_username -d your_database_name -f db/formatting.sql 
```
Replace `your_username` and `your_database_name` with your       
PostgreSQL credentials.

### 5. Run the Backend Server

Navigate to the `server/` directory and start the FastAPI        
application:

```bash
cd server
uvicorn main:app --reload
```
The server will typically run on `http://localhost:8000`.        

### 6. Run the Client Application

Open a new terminal, activate your virtual environment, navigate 
to the `client/` directory, and start the Streamlit application: 

```bash
cd client
streamlit run app.py
```
The Streamlit app will open in your web browser, usually at      
`http://localhost:8501`.

## Usage

Once both the backend and client applications are running:       

1.  **Access the Streamlit UI**: Open your web browser to        
`http://localhost:8501`.
2.  **Sign Up / Log In**: Use the Login or Signup tabs to create 
a new account or log in with existing credentials.
3.  **Chat with JoluMate**: After logging in, you can start new  
conversations, send messages, and view chat history in the main  
panel.
4.  **Upload Documents**: Use the "Upload PDF" feature in the    
sidebar to add PDF documents. The AI agent will then be able to  
retrieve information from these documents to answer your
questions.
5.  **Manage Conversations**: In the sidebar, you can select     
existing conversations to continue them or delete them as needed.

## Configuration / Environment Variables

The application's behavior is influenced by several environment  
variables and constants:

### Environment Variables

Loaded from `.env` files:

*   `BACKEND_URL`: (Client-side) The base URL for the backend    
API.
*   `GROQ_API_KEY`: (Server-side) API key required for accessing 
the Groq LLM.
*   `JWT_SECRET`: (Server-side) Secret key used for signing and  
verifying JSON Web Tokens.
*   `DATABASE_URL`: (Server-side) Connection string for the      
PostgreSQL database.
*   `GOOGLE_API_KEY`: (Server-side) API key for accessing Google 
Generative AI embedding models.

### Server-side Constants

Configured within the server code:

*   `ACCESS_TOKEN_MINUTES`: Lifetime duration for JWT access     
tokens (in minutes). Defined in `server/auth/auth.py`.
*   `REFRESH_TOKEN_DAYS`: Lifetime duration for refresh tokens   
(in days). Defined in `server/auth/auth.py`.
*   `EMBEDDINGS_MODEL`: Specifies `models/text-embedding-004` as 
the embedding model for Google Generative AI. Defined in
`server/rag/utils.py`.
*   `CHUNK_SIZE`: The maximum character size for text chunks     
during document processing (default: 1000 characters). Defined in
`server/rag/utils.py`.
*   `CHUNK_OVERLAP`: The character overlap between consecutive   
text chunks during document processing (default: 200 characters).
Defined in `server/rag/utils.py`.
*   `DEFAULT_SEARCH_LIMIT`: The default limit for the number of  
document search results to retrieve (default: 5 documents).      
Defined in `server/rag/utils.py`.
*   `DATABASE_POOL_SETTINGS`: Configured in
`server/configs/db.py` for `psycopg_pool`, including
`min_size=1`, `max_size=10`, `row_factory=dict_row`,
`autocommit=True`, and `prepare_threshold=None`.

## How the Code Works

JoluMate is structured as a client-server application, with a    
Streamlit frontend interacting with a FastAPI backend.

1.  **Client Application (`client/app.py` & `client/api.py`)**:  
    *   The `client/app.py` file powers the Streamlit web        
interface, providing the UI for user authentication, conversation
display, PDF uploads, and chat input. It manages the
application's session state, including user information, active  
conversation IDs, and chat messages.
    *   `client/api.py` acts as a thin client-side wrapper,      
encapsulating HTTP requests to the backend API. It defines helper
functions for signup, login, logout, fetching user info, getting 
answers, retrieving chat history, listing conversations, deleting
conversations, and uploading documents. It loads `BACKEND_URL`   
from the `.env` file.

2.  **Backend Application (`server/main.py`)**:
    *   `server/main.py` is the entry point for the FastAPI      
server. It configures the FastAPI application, sets up an        
asynchronous PostgreSQL connection pool (`configs.db.pool`), and 
initializes the LangGraph checkpointer
(`agent.graph.checkpointer`) during its lifespan for persistent  
state management.
    *   It registers a custom `log_requests` middleware
(`middlewares/log_requests.py`) to log all incoming HTTP
requests.
    *   It includes routers for authentication
(`auth/router.py`), chat interactions (`chat/router.py`), and    
conversation management (`conversation/router.py`).

3.  **Database Management (`db/formatting.sql` &
`server/configs/db.py`)**:
    *   `db/formatting.sql` defines the PostgreSQL database      
schema. It creates tables for `users` (credentials),
`refresh_tokens` (JWT refresh tokens), `conversations` (chat     
metadata), `chats` (individual messages), and `documents`        
(uploaded PDF text chunks with vector embeddings). It also sets  
up `vector` and `pgcrypto` extensions.
    *   `server/configs/db.py` establishes an asynchronous       
PostgreSQL connection pool using `psycopg_pool`, configured to   
handle database connections efficiently and provide them via the 
`get_conn` async generator. It loads the `DATABASE_URL` from the 
environment.

4.  **Authentication (`server/auth/`)**:
    *   `server/auth/hash.py` provides utilities for securely    
hashing user passwords using `bcrypt` (via `passlib`) and        
verifying them against stored hashes.
    *   `server/auth/auth.py` handles the core JWT logic. It     
creates access tokens (containing `user_id`) and random refresh  
tokens, manages their expiry, and stores refresh tokens in the   
database. It also defines `get_user` as a FastAPI dependency to  
authenticate requests by validating access tokens from cookies   
and retrieving user details.
    *   `server/auth/router.py` defines API endpoints for user   
authentication. This includes `/auth/signup` (creates new users),
`/auth/login` (verifies credentials, issues JWTs, sets HttpOnly  
cookies), `/auth/refresh` (rotates refresh tokens),
`/auth/logout` (clears tokens and cookies), and `/auth/me`       
(retrieves current user profile).

5.  **Chat and Conversation Management (`server/chat/router.py` &
`server/conversation/router.py`)**:
    *   `server/chat/router.py` manages all chat-related API     
interactions under the `/chat` prefix. It handles `POST
/chat/ask` requests by saving user messages, invoking the AI     
agent (`agent.graph.workflow`) to generate responses, and storing
assistant replies. It dynamically creates new conversations if no
`conversation_id` is provided. It also provides `GET
/chat/{conversation_id}` for retrieving chat history.
    *   `server/conversation/router.py` provides API endpoints   
for managing conversations under the `/conversations` prefix. It 
offers `GET /conversations` to list all conversations for an     
authenticated user and `POST /conversations/delete` to remove a  
specific conversation and all its associated chat messages from  
the database.

6.  **AI Agent (`server/agent/graph.py`)**:
    *   `server/agent/graph.py` defines the core AI agent using  
LangGraph. It establishes an asynchronous workflow named
"JoluMate" using a `ChatGroq` LLM (specifically
`llama-3.3-70b-versatile`).
    *   The agent uses a `search_knowledge_base` tool
(`rag.tools.search_knowledge_base`) to query uploaded documents. 
    *   The LangGraph workflow is built with an `agent_node` (for
LLM invocation with a system prompt) and a `ToolNode` (for       
executing tools). Conditional routing ensures the graph
transitions to the `tools` node when the LLM decides to use a    
tool, otherwise, it proceeds with direct LLM responses.
    *   The agent's state is persistently stored using an        
`AsyncPostgresSaver` checkpoint, allowing conversations to resume
seamlessly.

7.  **Retrieval Augmented Generation (RAG) (`server/rag/`)**:    
    *   `server/rag/utils.py` contains the core logic for PDF    
processing and vector search. It extracts text from PDF files    
using `pypdf`, splits the text into overlapping chunks using     
`RecursiveCharacterTextSplitter`, generates vector embeddings for
each chunk using `GoogleGenerativeAIEmbeddings` (with
`models/text-embedding-004`), and stores these in the `documents`
table. It also provides the `search_documents` function, which   
performs a cosine similarity search on stored embeddings in      
PostgreSQL to retrieve relevant document content for a given     
query and user.
    *   `server/rag/tools.py` defines the `search_knowledge_base`
asynchronous LangChain tool. This tool acts as the interface for 
the AI agent to interact with the RAG system. It receives a user 
query, extracts the `user_id` from the LangGraph
`RunnableConfig`, and then calls `rag.utils.search_documents` to 
fetch relevant information from the user's uploaded documents,   
returning the results to the AI agent.

## API Endpoints

The JoluMate backend provides the following REST API endpoints:  

### Authentication Endpoints (`/auth`)

*   **`POST /auth/signup`**
    *   **Description**: Registers a new user.
    *   **Request Body**: `{"name": "...", "email": "...",       
"password": "..."}`
    *   **Success Response**: `{"message": "User created
successfully"}` (Status: 201)
*   **`POST /auth/login`**
    *   **Description**: Authenticates a user, issues access and 
refresh tokens, and sets them as HttpOnly cookies.
    *   **Request Body**: `{"email": "...", "password": "..."}`  
    *   **Success Response**: `{"access_token": "..."}` (Status: 
200)
*   **`POST /auth/refresh`**
    *   **Description**: Validates the refresh token (from       
cookie), issues new access and refresh tokens, and updates       
HttpOnly cookies.
    *   **Success Response**: `{"access_token": "..."}` (Status: 
200)
*   **`POST /auth/logout`**
    *   **Description**: Deletes the refresh token from the      
database and clears authentication cookies.
    *   **Success Response**: `{"message": "Logged out
successfully"}` (Status: 200)
*   **`GET /auth/me`**
    *   **Description**: Retrieves the details of the currently  
authenticated user.
    *   **Success Response**: `{"id": "...", "name": "...",      
"email": "..."}` (Status: 200)

### Chat Endpoints (`/chat`)

*   **`POST /chat/ask`**
    *   **Description**: Submits a user message to the AI agent  
and retrieves an AI-generated response. Creates a new
conversation if `conversation_id` is not provided.
    *   **Request Body**: `{"message": "user's question",        
"conversation_id": "optional_conversation_id"}`
    *   **Success Response**: `{"conversation_id": "...",        
"answer": "AI's response"}` (Status: 200)
*   **`GET /chat/{conversation_id}`**
    *   **Description**: Fetches all chat messages for a specific
conversation, ordered by creation time.
    *   **Path Parameter**: `conversation_id` (UUID string)      
    *   **Success Response**: `[{"role": "user", "content":      
"..."}, {"role": "assistant", "content": "..."}, ...]` (Status:  
200)
*   **`POST /chat/upload`**
    *   **Description**: Uploads a PDF file for processing and   
integration into the RAG knowledge base.
    *   **Request Body**: Form data with `file` field containing 
the PDF file.
    *   **Success Response**: `{"message": "File uploaded and    
processed successfully"}` (Status: 200)

### Conversation Endpoints (`/conversations`)

*   **`GET /conversations`**
    *   **Description**: Lists all conversations belonging to the
authenticated user, ordered by creation date (descending).       
    *   **Success Response**: `[{"id": "...", "title": "...",    
"created_at": "..."}, ...]` (Status: 200)
*   **`POST /conversations/delete`**
    *   **Description**: Deletes a specific conversation and all 
its associated chat messages if it belongs to the authenticated  
user.
    *   **Query Parameter**: `conversation_id` (UUID string)     
    *   **Success Response**: `{"message": "Conversation deleted 
successfully"}` (Status: 200)

### Root Endpoint

*   **`GET /`**
    *   **Description**: A simple health check endpoint.
    *   **Success Response**: `{"message": "Hello JoluMate!"}`   
(Status: 200)

## License

This project is licensed under the MIT License.

Copyright (c) 2025 Sarowar Jahan Biswas

Permission is hereby granted, free of charge, to any person      
obtaining a copy of this software and associated documentation   
files (the "Software"), to deal in the Software without
restriction, including without limitation the rights to use,     
copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the        
Software is furnished to do so, subject to the following
conditions:

The above copyright notice and this permission notice shall be   
included in all copies or substantial portions of the Software.  

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,  
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES  
OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT      
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,     
WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING     
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR    
OTHER DEALINGS IN THE SOFTWARE.