import os
import json
from typing import List, Dict
from openai import OpenAI
from openai import RateLimitError, OpenAIError, APIError, APITimeoutError, AuthenticationError
from fastapi import HTTPException
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_flashcards(text_content: str) -> List[Dict[str, str]]:
    """
    Generate flashcards from PDF text content using OpenAI API
    
    Args:
        text_content: Extracted text from PDF
        
    Returns:
        List of flashcards with question and answer fields
        
    Raises:
        Exception: If OpenAI API call fails or invalid response
    """
    
    # Check API key first
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.error("OpenAI API key not found in environment variables")
        raise HTTPException(
            status_code=500, 
            detail="AI service configuration error, please contact support"
        )
    
    logger.info(f"Initializing OpenAI client with API key length: {len(api_key)}")
    
    try:
        # Initialize OpenAI client with custom HTTP client to avoid proxies issue
        import httpx
        
        # Create a custom HTTP client without proxies
        http_client = httpx.Client()
        
        client = OpenAI(api_key=api_key, http_client=http_client)
        logger.info("✅ OpenAI client initialized successfully")
    except Exception as e:
        logger.error(f"❌ OpenAI client initialization failed: {str(e)}")
        logger.error(f"Exception type: {type(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500, 
            detail="Failed to initialize AI service, please try again later"
        )
    
    # Truncate text if too long (OpenAI has token limits)
    max_chars = 8000  # Conservative limit to stay within token bounds
    if len(text_content) > max_chars:
        text_content = text_content[:max_chars] + "..."
    
    prompt = f"""From this PDF content, create exactly 10 high-quality flashcards.
Format as JSON array with 'question' and 'answer' fields.
Make questions test understanding, not just memorization.
Keep answers concise (1-2 sentences max).
Ensure the questions cover the most important concepts from the content.

PDF Content: {text_content}

Return ONLY the JSON array, no additional text."""

    try:
        logger.info("Making OpenAI API call...")
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that creates educational flashcards from text content. Always respond with valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )
        logger.info("✅ OpenAI API call successful")
        
        response_text = response.choices[0].message.content.strip()
        logger.info(f"Raw response length: {len(response_text)} characters")
        
        # Parse JSON response
        try:
            flashcards = json.loads(response_text)
            logger.info(f"✅ JSON parsed successfully, got {len(flashcards)} flashcards")
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON decode error: {str(e)}")
            logger.error(f"Response text preview: {response_text[:200]}...")
            # Try to extract JSON from response if it's wrapped in markdown
            if "```json" in response_text:
                start = response_text.find("```json") + 7
                end = response_text.find("```", start)
                if end != -1:
                    json_text = response_text[start:end].strip()
                    flashcards = json.loads(json_text)
                else:
                    raise Exception("Invalid JSON format in OpenAI response")
            else:
                raise Exception("Invalid JSON format in OpenAI response")
        
        # Validate response format
        if not isinstance(flashcards, list):
            raise Exception("OpenAI response is not a list")
        
        if len(flashcards) != 10:
            logger.warning(f"Expected 10 flashcards, got {len(flashcards)}")
        
        # Validate each flashcard
        validated_flashcards = []
        for i, card in enumerate(flashcards):
            if not isinstance(card, dict):
                raise Exception(f"Flashcard {i+1} is not a dictionary")
            
            if "question" not in card or "answer" not in card:
                raise Exception(f"Flashcard {i+1} missing question or answer field")
            
            validated_flashcards.append({
                "question": str(card["question"]).strip(),
                "answer": str(card["answer"]).strip()
            })
        
        return validated_flashcards
        
    except RateLimitError as e:
        logger.error(f"OpenAI rate limit exceeded: {str(e)}")
        raise HTTPException(
            status_code=429, 
            detail="AI quota exceeded, please try again later"
        )
    except AuthenticationError as e:
        logger.error(f"OpenAI authentication failed: {str(e)}")
        raise HTTPException(
            status_code=401, 
            detail="AI service authentication failed. Please check API key configuration."
        )
    except APITimeoutError as e:
        logger.error(f"OpenAI API timeout: {str(e)}")
        raise HTTPException(
            status_code=504, 
            detail="AI service timeout, please try again later"
        )
    except APIError as e:
        logger.error(f"OpenAI API error: {str(e)}")
        # Check if it's a quota/billing error
        if "quota" in str(e).lower() or "billing" in str(e).lower():
            raise HTTPException(
                status_code=429, 
                detail="AI quota exceeded, please try again later"
            )
        else:
            raise HTTPException(
                status_code=502, 
                detail="AI service error, please try again later"
            )
    except OpenAIError as e:
        logger.error(f"OpenAI service error: {str(e)}")
        raise HTTPException(
            status_code=502, 
            detail="AI service temporarily unavailable, please try again later"
        )
    except Exception as e:
        logger.error(f"Unexpected error during flashcard generation: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail="Failed to generate flashcards, please try again later"
        )

def test_flashcard_generation():
    """Test function to verify flashcard generation works"""
    test_text = """
    Machine Learning is a subset of artificial intelligence that focuses on algorithms 
    that can learn from data. Supervised learning uses labeled training data to make 
    predictions, while unsupervised learning finds patterns in unlabeled data. 
    Common algorithms include linear regression, decision trees, and neural networks.
    """
    
    try:
        flashcards = generate_flashcards(test_text)
        print(f"Generated {len(flashcards)} flashcards successfully")
        for i, card in enumerate(flashcards):
            print(f"{i+1}. Q: {card['question']}")
            print(f"   A: {card['answer']}\n")
    except Exception as e:
        print(f"Test failed: {str(e)}")

if __name__ == "__main__":
    test_flashcard_generation()
