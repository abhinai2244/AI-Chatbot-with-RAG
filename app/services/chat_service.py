from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.models.db_models import Message, Session, DocumentChunk, Document
from app.services.vector_store import get_embeddings_service
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from app.core.config import settings
from fastapi import BackgroundTasks
import logging

# Configure Logger
logger = logging.getLogger(__name__)

async def get_llm():
    """
    Factory to get the configured LLM instance (OpenAI or Gemini).
    
    Why:
    ----
    - Allows seamless switching between providers via `LLM_PROVIDER` env var.
    - Centralizes model configuration (temperature, model name).
    """
    try:
        if settings.LLM_PROVIDER == "gemini":
            return ChatGoogleGenerativeAI(
                model=settings.GEMINI_MODEL,
                google_api_key=settings.GOOGLE_API_KEY,
                temperature=0.7,
                convert_system_message_to_human=True # Gemini sometimes prefers this
            )
        else:
            return ChatOpenAI(
                api_key=settings.OPENAI_API_KEY, 
                model=settings.OPENAI_MODEL,
                temperature=0.7
            )
    except Exception as e:
        logger.error(f"Error initializing LLM: {e}")
        raise e

async def update_summary(session_id: str):
    """
    Background task to update conversation summary.
    
    Why Background Task?
    --------------------
    - Summarization is a "slow" LLM operation.
    - We don't want to block the user's response while calculating the summary.
    - It can run asynchronously after the response is sent.
    
    Logic:
    ------
    1. Fetch recent messages (last 10).
    2. Fetch existing summary.
    3. Ask LLM to condense the new info into the existing summary.
    4. Update `valid_session.summary` in DB.
    """
    try:
        from app.core.database import SessionLocal
        async with SessionLocal() as session:
            # 1. Fetch last 10 messages (descending orders, then reversed)
            stmt = select(Message).where(Message.session_id == session_id).order_by(Message.created_at.desc()).limit(10)
            result = await session.execute(stmt)
            recent_messages = result.scalars().all()[::-1] 
            
            if not recent_messages:
                return

            # 2. Fetch current summary
            session_result = await session.execute(select(Session).where(Session.id == session_id))
            session_obj = session_result.scalar_one_or_none()
            current_summary = session_obj.summary if session_obj else "No summary yet."
            
            # 3. Generate new summary
            llm = await get_llm()
            
            # Lower temperature for summarization to be more factual
            llm.temperature = 0.3 
            
            prompt = f"""
            You are an expert summarizer. Update the conversation summary based on the new messages.
            
            Current Summary:
            {current_summary}
            
            Recent Messages:
            {chr(10).join([f"{msg.role}: {msg.content}" for msg in recent_messages])}
            
            Instruction:
            - Incorporate meaningful new information into the summary.
            - Keep the summary concise (under 200 words).
            - Maintain key details from the 'Current Summary' if they are still relevant.
            """
            
            response = await llm.ainvoke([HumanMessage(content=prompt)])
            new_summary = response.content
            
            # 4. Update DB
            await session.execute(
                update(Session).where(Session.id == session_id).values(summary=new_summary)
            )
            await session.commit()
            logger.info(f"Updated summary for session {session_id}")
            
    except Exception as e:
        logger.error(f"Failed to update summary for session {session_id}: {e}")
        # Build robustness: failure here shouldn't crash the app, just log it.

async def process_chat(session_id: str, user_query: str, db: AsyncSession, background_tasks: BackgroundTasks) -> str:
    """
    Core Chat Logic with RAG and Memory.
    
    Steps:
    1. Manage Session: Ensure session exists.
    2. Save User Message: Persist input immediately.
    3. RAG Retrieval: Search pgvector for relevant document chunks.
    4. History Retrieval: Get recent messages + session summary.
    5. Prompt Construction: Combine System Instruction + Context + Summary + History.
    6. LLM Generation: Get response.
    7. Save AI Message: Persist output.
    8. Background Task: Trigger summary update.
    """
    try:
        # ------------------------------------------------------------------
        # 1. Ensure Session Exists
        # ------------------------------------------------------------------
        result = await db.execute(select(Session).where(Session.id == session_id))
        session_obj = result.scalar_one_or_none()
        if not session_obj:
            logger.info(f"Creating new session: {session_id}")
            session_obj = Session(id=session_id)
            db.add(session_obj)
            await db.commit()
            session_summary = ""
        else:
            session_summary = session_obj.summary or ""

        # ------------------------------------------------------------------
        # 2. Save User Message to DB
        # ------------------------------------------------------------------
        # We save BEFORE processing to ensure we capture the intent even if processing fails later.
        user_msg = Message(session_id=session_id, role="user", content=user_query)
        db.add(user_msg)
        await db.commit()
        
        # ------------------------------------------------------------------
        # 3. Retrieve Context (RAG) - Manual PGVector Search
        # ------------------------------------------------------------------
        # Why <-> operator? It calculates Euclidean distance (L2). 
        # Lower distance = Higher similarity.
        context_text = ""
        try:
            embeddings_service = get_embeddings_service()
            query_vector = await embeddings_service.aembed_query(user_query)
            
            # Query: Join DocumentChunk -> Document to filter by session_id
            stmt = (
                select(DocumentChunk)
                .join(Document, DocumentChunk.document_id == Document.id)
                .where(Document.session_id == session_id)
                .order_by(DocumentChunk.embedding.l2_distance(query_vector))
                .limit(3) # Top 3 chunks
            )
            
            result = await db.execute(stmt)
            relevant_chunks = result.scalars().all()
            
            if relevant_chunks:
                context_text = "\n\n".join([f"[Chunk]: {chunk.content}" for chunk in relevant_chunks])
            else:
                context_text = "No relevant documents found."
                
        except Exception as e:
            logger.error(f"RAG Retrieval failed: {e}")
            context_text = "Error retrieving context."

        # ------------------------------------------------------------------
        # 4. Retrieve History - Smart Retrieval
        # ------------------------------------------------------------------
        # Fetching only last 6 messages to save context window.
        # The 'session_summary' covers older context.
        stmt = select(Message).where(Message.session_id == session_id).order_by(Message.created_at.desc()).limit(6)
        history_result = await db.execute(stmt)
        history_records = history_result.scalars().all()[::-1] # Reverse to chronological
        
        # ------------------------------------------------------------------
        # 5. Build System Prompt & Messages
        # ------------------------------------------------------------------
        messages = []
        
        system_prompt = f"""You are an intelligent AI Assistant for the 'Atlantis' system.

        Instructions:
        1. Answer the user's question accurately.
        2. Use the provided 'Context from Documents' if relevant.
        3. Use the 'Conversation Summary' and 'Conversation History' to maintain continuity.
        4. If the answer is not in the context, use your general knowledge but mention that it's outside the provided documents.

        Context from Documents (RAG):
        {context_text}

        Conversation Summary (Long-term Memory):
        {session_summary}
        """
        
        # Add System Message
        messages.append(SystemMessage(content=system_prompt))
        
        # Add History (Short-term Memory)
        for msg in history_records:
            if msg.role == "user":
                messages.append(HumanMessage(content=msg.content))
            elif msg.role == "assistant":
                messages.append(AIMessage(content=msg.content))
                
        # ------------------------------------------------------------------
        # 6. LLM Generation with Retry Logic (for Gemini 429 Errors)
        # ------------------------------------------------------------------
        # The user's free tier quota is very low (limit: 20 requests/day or minute).
        # We implementation a simple exponential backoff retry.
        import time
        import asyncio
        
        max_retries = 3
        retry_delay = 5 # seconds
        
        ai_response_text = "I apologize, but I am currently overloaded. Please try again later."
        
        for attempt in range(max_retries):
            try:
                llm = await get_llm()
                response = await llm.ainvoke(messages)
                ai_response_text = response.content
                break # Success, exit loop
                
            except Exception as e:
                error_str = str(e)
                if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str: 
                    if attempt < max_retries - 1:
                        logger.warning(f"Quota exceeded (Attempt {attempt+1}/{max_retries}). Retrying in {retry_delay}s...")
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2 # Exponential backoff: 5, 10, 20
                        continue
                
                # If not quota error or max retries reached, raise it
                logger.error(f"LLM Error (Attempt {attempt+1}): {e}")
                raise e
        
        # ------------------------------------------------------------------
        # 7. Save AI Response to DB
        # ------------------------------------------------------------------
        ai_msg = Message(session_id=session_id, role="assistant", content=ai_response_text)
        db.add(ai_msg)
        await db.commit()
        
        # ------------------------------------------------------------------
        # 8. Schedule Summary Update
        # ------------------------------------------------------------------
        # Trigger background summarization to keep 'session_summary' up to date.
        background_tasks.add_task(update_summary, session_id)
        
        return ai_response_text

    except Exception as e:
        logger.error(f"Error in process_chat: {e}")
        # In a real app, we might retry or return a graceful error message.
        return "I apologize, but I encountered an internal error while processing your request."
