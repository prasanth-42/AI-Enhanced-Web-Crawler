import os
import groq
from typing import ClassVar, List, Optional, Any, Dict, Type, Union
from dotenv import load_dotenv

from langchain_core.messages import AIMessage, HumanMessage, BaseMessage
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.outputs import ChatResult, ChatGeneration
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.chains import create_history_aware_retriever, create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from pydantic import BaseModel, Field

# Load environment variables
load_dotenv()

class GroqChatLLM(BaseChatModel):
    model_name: str = Field(default="llama3-8b-8192")
    temperature: float = 0.7
    api_key: Optional[str] = Field(default_factory=lambda: os.getenv("GROQ_API_KEY"))
    client: Any = None  # Add client field
    
    def __init__(self, **data):
        super().__init__(**data)
        if not self.api_key:
            raise ValueError("GROQ_API_KEY environment variable is not set")
        print(f"Using model: {self.model_name}")
        print(f"API key: {self.api_key[:5]}...{self.api_key[-5:] if self.api_key else ''}")
        self.client = groq.Client(api_key=self.api_key) if self.api_key else None

    @property
    def _llm_type(self) -> str:
        return "groq"

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        if not self.api_key:
            raise ValueError("GROQ_API_KEY is not set in environment variables")
        
        # Convert LangChain messages to Groq format
        formatted_messages = []
        for msg in messages:
            if isinstance(msg, AIMessage):
                role = "assistant"
            else:  # Default to user for HumanMessage and other types
                role = "user"
                
            formatted_messages.append({
                "role": role,
                "content": str(msg.content)
            })
        
        try:
            # Make the API call using Groq client
            chat_completion = self.client.chat.completions.create(
                messages=formatted_messages,
                model=self.model_name,
                temperature=self.temperature,
                max_tokens=1000,
                stop=stop
            )
            
            # Extract the response content
            if chat_completion.choices and chat_completion.choices[0].message:
                content = chat_completion.choices[0].message.content
                # Create a ChatGeneration object
                generation = ChatGeneration(
                    message=AIMessage(content=content),
                    text=content,
                )
                # Return a proper ChatResult object
                return ChatResult(generations=[generation])
            else:
                raise ValueError("No content in response")
                
        except Exception as e:
            error_msg = f"Error generating response: {str(e)}"
            print(f"Error details: {error_msg}")
            raise Exception(error_msg)

    def _call(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> str:
        return self._generate(messages, stop=stop, **kwargs)

def get_context_retriever_chain(vector_store):
    """Create a retriever chain that is aware of conversation history"""
    llm = GroqChatLLM()
    retriever = vector_store.as_retriever()

    prompt = ChatPromptTemplate.from_messages([
        MessagesPlaceholder(variable_name="chat_history"),
        ("user", "{input}"),
        ("user", "Given the above conversation, generate a search query to look up in order to get information relevant to the conversation")
    ])

    return create_history_aware_retriever(llm, retriever, prompt)

def get_conversational_rag_chain(retriever_chain):
    """Create a conversational RAG chain using the retriever chain"""
    llm = GroqChatLLM()

    prompt = ChatPromptTemplate.from_messages([
        ("system", "Answer the user's questions based on the below context:\n\n{context}"),
        MessagesPlaceholder(variable_name="chat_history"),
        ("user", "{input}"),
    ])

    stuff_documents_chain = create_stuff_documents_chain(llm, prompt)
    return create_retrieval_chain(retriever_chain, stuff_documents_chain)

def get_response(user_input, vector_store, chat_history):
    """
    Get a response from the LLM based on user input, vector store, and chat history
    
    Args:
        user_input (str): The user's query
        vector_store: The vector store containing embedded website content
        chat_history (list): List of previous chat messages
        
    Returns:
        str: The LLM's response
    """
    retriever_chain = get_context_retriever_chain(vector_store)
    rag_chain = get_conversational_rag_chain(retriever_chain)

    response = rag_chain.invoke({
        "chat_history": chat_history,
        "input": user_input
    })

    return response["answer"]

def update_chat_history(chat_history, user_query, response):
    """
    Update the chat history with a new user query and response
    
    Args:
        chat_history (list): The current chat history
        user_query (str): The user's query
        response (str): The LLM's response
        
    Returns:
        list: The updated chat history
    """
    updated_history = chat_history.copy()
    updated_history.append(HumanMessage(content=user_query))
    updated_history.append(AIMessage(content=response))
    return updated_history
