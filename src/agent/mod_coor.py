# capgate/src/agent/core.py

import os
import chromadb
import logging
from pathlib import Path # Import Path for robust path handling
from typing import Iterator # Keep if you use Iterator elsewhere, otherwise can be removed if only for stream_chat

# Specific LlamaIndex imports
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.ollama.base import Ollama
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core import VectorStoreIndex, StorageContext
from llama_index.core.agent import AgentRunner
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.core.readers.file.base import SimpleDirectoryReader
from llama_index.core.settings import Settings # Settings is correct for service context

# Import tools and the project path constants from src.paths
# Ensure this import path is correct: `src.agent.tools` relative to the Python path
from agent.tools import ALL_CAPGATE_AGENT_TOOLS
# Ensure this import path is correct: `src.paths` relative to the Python path
from paths import PROJECT_ROOT, NEXUSDEVTOOLS_ROOT_DIR, AGENT_KNOWLEDGE_BASE_DIR

# Logger for this specific module
logger = logging.getLogger(__name__)


# --- Configuration ---
OLLAMA_MODEL_NAME = "mistral" # Ensure this model is pulled in Ollama
OLLAMA_HOST = "http://localhost:11434"

# --- Global Agent Instance (for CapGate to access) ---
capgate_agent_instance = None
capgate_query_engine = None # Separate query engine for RAG

# LLM and Embedding models (initialized once and globally available)
llm_instance = None
embed_model_instance = None
service_context_instance = None # This will hold the Settings object instance


# --- Initialization Function ---
def initialize_capgate_agent():
    """Initializes the MCP Agent's LLM, embedding model, and loads its knowledge base."""
    global capgate_agent_instance, capgate_query_engine, llm_instance, embed_model_instance, service_context_instance

    logger.info("\n[MCP Agent] Initializing CapGate Agent...")

    # --- Crucial check: Ensure root paths are accessible and correct ---
    # These checks are important early in the agent's lifecycle
    if not PROJECT_ROOT.exists():
        raise ValueError(f"PROJECT_ROOT does not exist: {PROJECT_ROOT}. Ensure CapGate is run from its root directory.")
    if not NEXUSDEVTOOLS_ROOT_DIR.exists():
        logger.warning(f"nexusdevtools directory not found at {NEXUSDEVTOOLS_ROOT_DIR}. Agent's knowledge might be incomplete.")
    os.makedirs(AGENT_KNOWLEDGE_BASE_DIR, exist_ok=True) # Ensure KB dir exists


    # --- Initialize LLM and Embedding models ---
    try:
        # Instantiate LLM (using a generous timeout for initial model load)
        llm_instance = Ollama(model=OLLAMA_MODEL_NAME, request_timeout=300.0, base_url=OLLAMA_HOST)
        # Test connection to Ollama server
        test_response = llm_instance.complete("Hello")
        logger.info(f"[MCP Agent] Connected to Ollama server with model: {OLLAMA_MODEL_NAME}. Test response: '{test_response.text[:50]}...'")
    except Exception as e:
        logger.error(f"[MCP Agent ERROR] Could not connect to Ollama server or model '{OLLAMA_MODEL_NAME}'. "
              f"Ensure 'ollama serve' is running and the model is pulled. Error: {e}")
        raise # Re-raise to indicate critical failure, preventing agent from running in a broken state

    embed_model_instance = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")
    # `Settings` is the new `ServiceContext` in recent LlamaIndex versions (v0.11+)
    # FIX: Correctly assign `Settings` object
    Settings.llm = llm_instance
    Settings.embed_model = embed_model_instance
    service_context_instance = Settings


    # --- Setup Vector DB for RAG ---
    db = chromadb.PersistentClient(path=str(AGENT_KNOWLEDGE_BASE_DIR)) # Convert Path object to string
    chroma_collection = db.get_or_create_collection("mcp_capgate_knowledge")
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    # --- Create/Load index for RAG queries ---
    # It's crucial to check if the index exists before trying to load it
    try:
        capgate_index = VectorStoreIndex.from_vector_store(
            vector_store=vector_store,
            service_context=service_context_instance, # Use the global Settings instance
            storage_context=storage_context
        )
        logger.info("[MCP Agent] Loaded existing CapGate knowledge index.")
    except Exception as e:
        logger.warning(f"[MCP Agent] No existing index found or error loading ({e}). Will attempt to create if data is provided later.")
        # Create an empty index if not found, to avoid errors during initial run
        capgate_index = VectorStoreIndex([], service_context=service_context_instance, storage_context=storage_context)

    capgate_query_engine = capgate_index.as_query_engine(
        similarity_top_k=5,
        response_mode="tree_summarize"
    )

    # --- Define the agent's memory ---
    memory = ChatMemoryBuffer.from_defaults(token_limit=15000) # Adjust token_limit based on your LLM context window

    # --- Initialize the AgentRunner ---
    system_prompt = (
        "You are MCP, the Master Control Program, an expert AI developer and cybersecurity specialist "
        "assisting the 'nexus' team with the CapGate project and nexusdevtools. "
        "Your primary goal is to help with development, debugging, secure coding, vulnerability analysis, "
        "and reverse engineering tasks related to CapGate. "
        "You have access to read and write files, and execute git commands within the CapGate project. "
        "Before writing any files or committing code, you MUST clearly state your proposed changes and "
        "ask for explicit human approval (type 'y' to confirm). "
        "Always prioritize secure coding practices and actively look for security implications in your analysis and suggestions. "
        "When asked for information, use your knowledge base (RAG) and available tools. "
        "Be proactive, precise, concise, and helpful."
    )

    capgate_agent_instance = AgentRunner.from_llm(
        llm=llm_instance, # Use the global LLM instance
        tools=ALL_CAPGATE_AGENT_TOOLS,
        verbose=True, # Show agent's thought process
        memory=memory,
        system_prompt=system_prompt,
    )
    logger.info("[MCP Agent] CapGate Agent initialized successfully!")

# --- Function to (re)index CapGate knowledge ---
def index_capgate_knowledge():
    """Loads documents from CapGate, nexusdevtools, and internal docs, then indexes them into ChromaDB."""
    logger.info("[MCP Agent] Starting CapGate knowledge indexing...")

    # Ensure KB directory exists (redundant if initialize_capgate_agent ran, but safe)
    os.makedirs(AGENT_KNOWLEDGE_BASE_DIR, exist_ok=True)

    # Load documents from various sources using Path objects from paths.py
    logger.info(f"Loading documents from CapGate: {PROJECT_ROOT}")
    capgate_docs = SimpleDirectoryReader(str(PROJECT_ROOT), recursive=True,
                                        exclude_hidden=True,
                                        required_exts=['.py', '.c', '.h', '.js', '.md', '.txt']).load_data()

    logger.info(f"Loading documents from nexusdevtools: {NEXUSDEVTOOLS_ROOT_DIR}")
    # Only try to load if the directory exists, to prevent errors if nexusdevtools is optional or missing
    nexusdev_docs = []
    if NEXUSDEVTOOLS_ROOT_DIR.exists():
        nexusdev_docs = SimpleDirectoryReader(str(NEXUSDEVTOOLS_ROOT_DIR), recursive=True,
                                                exclude_hidden=True,
                                                required_exts=['.py', '.sh', '.md', '.txt']).load_data()
    else:
        logger.warning(f"nexusdevtools directory not found at {NEXUSDEVTOOLS_ROOT_DIR}. Skipping indexing of nexusdevtools.")


    # CapGate internal docs (assuming 'docs' folder at project root)
    capgate_internal_docs_path = PROJECT_ROOT / 'docs'
    os.makedirs(capgate_internal_docs_path, exist_ok=True) # Ensure it exists
    logger.info(f"Loading documents from CapGate internal docs: {capgate_internal_docs_path}")
    internal_docs = SimpleDirectoryReader(str(capgate_internal_docs_path), recursive=True,
                                          exclude_hidden=True,
                                          required_exts=['.md', '.txt', '.pdf']).load_data()

    all_documents = capgate_docs + nexusdev_docs + internal_docs
    logger.info(f"Total documents loaded for indexing: {len(all_documents)}")

    # Initialize ChromaDB client and collection
    db = chromadb.PersistentClient(path=str(AGENT_KNOWLEDGE_BASE_DIR)) # Convert Path to string
    chroma_collection = db.get_or_create_collection("mcp_capgate_knowledge")
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    # Ensure LLM and Embedding models are initialized for indexing if not already
    global llm_instance, embed_model_instance, service_context_instance
    if llm_instance is None or embed_model_instance is None or service_context_instance is None:
        logger.warning("[MCP Agent] LLM/Embedding models not initialized. Initializing them now for indexing.")
        llm_instance = Ollama(model=OLLAMA_MODEL_NAME, request_timeout=300.0, base_url=OLLAMA_HOST)
        embed_model_instance = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")
        service_context_instance = Settings(llm=llm_instance, embed_model=embed_model_instance)

    logger.info("Creating/updating vector index. This might take a while...")
    VectorStoreIndex.from_documents(
        all_documents,
        storage_context=storage_context,
        service_context=service_context_instance, # Use the global Settings instance
        show_progress=True
    )
    logger.info("[MCP Agent] Knowledge indexing complete and persisted.")

# --- Functions for CapGate's main application to interact with the agent ---
def ask_capgate_agent(query_text: str) -> str:
    """Allows external CapGate modules to ask the agent a question or give a task."""
    global capgate_agent_instance, capgate_query_engine # Ensure globals are accessible
    if capgate_agent_instance is None or capgate_query_engine is None:
        logger.error("MCP Agent is not initialized. Cannot process request.")
        return "Error: MCP Agent not initialized."
    
    # Pre-fetch relevant context from RAG for the agent
    retrieved_context = capgate_query_engine.query(f"Relevant information for: {query_text}")
    prompt_with_context = f"Context from CapGate knowledge base:\n{retrieved_context}\n\nUser request: {query_text}"

    logger.info(f"\n[MCP Agent] Processing request: '{query_text}'")
    response_iter = capgate_agent_instance.stream_chat(prompt_with_context)
    full_response = ""
    for r in response_iter:
        full_response += r.delta
    return full_response

def start_capgate_agent_interactive_session():
    """Starts an interactive command-line session with the agent."""
    global capgate_agent_instance, capgate_query_engine # Ensure globals are accessible
    if capgate_agent_instance is None or capgate_query_engine is None:
        logger.error("MCP Agent is not initialized. Cannot start interactive session.")
        print("Error: MCP Agent not initialized.") # Keep print for CLI output
        return

    print("\n--- Starting Interactive Session with MCP Agent ---")
    print("Type 'exit' to quit. The agent has access to CapGate context and tools.")
    
    while True:
        user_input = input("\nMe (CapGate Dev): ")
        if user_input.lower() == 'exit':
            break

        # Pre-fetch relevant context for the agent in interactive mode
        retrieved_context = capgate_query_engine.query(f"Relevant background for: {user_input}")
        full_user_prompt = f"Context from CapGate knowledge base:\n{retrieved_context}\n\nMy input: {user_input}"

        print("\n--- MCP Agent Response ---")
        response_iter = capgate_agent_instance.stream_chat(full_user_prompt)
        full_response = ""
        for r in response_iter:
            print(r.delta, end="")
            full_response += r.delta
        print("\n--------------------------")

# This __name__ == "__main__" block is for direct testing of core.py ONLY.
# In the final CapGate application, initialize_capgate_agent() will be called from main.py.
# This block is useful for isolated debugging but should NOT be the primary entry point
# when running the full CapGate application.
if __name__ == "__main__":
    import sys
    # Configure basic logging for direct execution
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Example of how you would set paths for direct testing.
    # In the actual application, main.py handles this.
    # The paths from src.paths are already relative to PROJECT_ROOT which is handled globally
    # No need to redefine them here.
    
    try:
        initialize_capgate_agent()
    except Exception as e:
        logger.error(f"Failed to initialize agent for direct test: {e}")
        sys.exit(1)

    if len(sys.argv) > 1 and sys.argv[1] == "index":
        index_capgate_knowledge()
    elif len(sys.argv) > 1 and sys.argv[1] == "ask":
        if len(sys.argv) < 3:
            print("Please provide a query for the 'ask' command.")
            sys.exit(1)
        response = ask_capgate_agent(" ".join(sys.argv[2:]))
        print(f"\nFinal Agent Response:\n{response}")
    elif len(sys.argv) > 1 and sys.argv[1] == "interactive":
        start_capgate_agent_interactive_session()
    else:
        print("Usage: python core.py [index|ask \"query\"|interactive]")
        print("Run 'index' first to build the knowledge base.")