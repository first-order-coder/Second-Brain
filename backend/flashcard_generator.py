import os
import json
import re
from typing import List, Dict
import httpx
from openai import OpenAI
from openai import RateLimitError, OpenAIError, APIError, APITimeoutError, AuthenticationError
from fastapi import HTTPException
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# SECURITY: OpenAI timeout configuration
OPENAI_TIMEOUT_SECONDS = int(os.getenv("OPENAI_TIMEOUT_SECONDS", "60"))
MAX_INPUT_CHARS = int(os.getenv("MAX_INPUT_CHARS", "8000"))

def clean_json_response(response_text: str) -> str:
    """
    Clean OpenAI response text to extract pure JSON.
    
    Handles:
    - Markdown code fences (```json ... ``` or ``` ... ```)
    - Leading/trailing whitespace
    - Explanatory text before/after JSON
    
    Args:
        response_text: Raw response from OpenAI
        
    Returns:
        Cleaned JSON string ready for parsing
    """
    if not response_text:
        raise ValueError("Empty response text")
    
    # Strip leading/trailing whitespace
    text = response_text.strip()
    
    # Remove markdown code fences
    # Pattern: ```json ... ``` or ``` ... ```
    json_fence_pattern = r'^```(?:json)?\s*\n?(.*?)\n?```\s*$'
    match = re.search(json_fence_pattern, text, re.DOTALL)
    if match:
        text = match.group(1).strip()
    
    # If still wrapped in fences (multiline case), try again
    if text.startswith('```'):
        # Find first ``` and last ```
        start_idx = text.find('```')
        if start_idx != -1:
            # Skip the opening fence
            text = text[start_idx + 3:]
            # Remove 'json' label if present
            if text.startswith('json'):
                text = text[4:].lstrip()
            # Find closing fence
            end_idx = text.rfind('```')
            if end_idx != -1:
                text = text[:end_idx].strip()
    
    # Try to find JSON array start
    json_start = text.find('[')
    json_end = text.rfind(']')
    
    if json_start != -1 and json_end != -1 and json_end > json_start:
        text = text[json_start:json_end + 1]
    
    # Final strip
    return text.strip()

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
        # SECURITY: Add timeout to prevent hanging requests
        http_client = httpx.Client(timeout=OPENAI_TIMEOUT_SECONDS)
        
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
    
    # SECURITY: Truncate text if too long (OpenAI has token limits, prevents cost attacks)
    if len(text_content) > MAX_INPUT_CHARS:
        logger.warning(f"Truncating input from {len(text_content)} to {MAX_INPUT_CHARS} chars")
        text_content = text_content[:MAX_INPUT_CHARS] + "..."
    
    prompt = f"""You are an expert educational content designer specializing in creating high-impact flashcards for deep learning and long-term retention. Your task is to extract and synthesize the most valuable knowledge from the provided PDF content into exactly 10 strategic flashcards.

RESPONSE FORMAT REQUIREMENT - CRITICAL:
You MUST respond with ONLY a valid JSON array. Do NOT include any markdown code fences.

JSON Structure:
Return a JSON array containing exactly 10 objects. Each object MUST have precisely two fields:
- "question": (string) The question posed to the learner
- "answer": (string) The corresponding answer

FLASHCARD DESIGN PRINCIPLES:

Question Quality Standards:
- Design questions to test comprehension, application, and synthesis—not mere factual recall
- Ask "why," "how," and "what if" questions that promote deeper understanding
- Include context-specific scenarios where applicable
- Avoid yes/no or single-word answer questions
- Frame questions to reveal misconceptions and test nuanced understanding
- Prioritize questions that bridge theory and practical application

Answer Quality Standards:
- Keep answers concise and precise (1-2 sentences maximum, ideally under 50 words)
- Ensure answers directly and completely address the question asked
- Include only essential information; omit redundancy
- Use clear, accessible language appropriate to the content domain
- Where applicable, include brief supporting evidence or reasoning within the answer

Content Selection Strategy:
- Identify and prioritize the 10 most foundational, high-impact concepts from the PDF
- Balance coverage across different topic areas and complexity levels
- Ensure questions build on each other, forming a coherent knowledge structure
- Include at least 2-3 questions that address critical relationships between concepts
- Exclude trivial details; focus on knowledge that has broad applicability
- Where relevant, include one question addressing common misconceptions or edge cases

Cognitive Difficulty Distribution:
- Include 2-3 foundational definition/concept questions (basic understanding)
- Include 3-4 application/analysis questions (intermediate difficulty)
- Include 2-3 synthesis/evaluation questions (higher-order thinking)

Validation Before Response:
- Verify exactly 10 flashcards are included
- Confirm each flashcard has both "question" and "answer" fields with string values
- Ensure the JSON is valid and properly formatted
- Test that your response can be parsed as JSON without errors

CRITICAL RESTRICTIONS (NON-NEGOTIABLE):
- Return ONLY valid JSON array format: starts with [ and ends with ]
- NO markdown code fences
- NO explanatory text, preamble, or closing remarks
- NO deviation from the exact 10-flashcard requirement
- NO nested structures other than the required "question" and "answer" fields

PDF Content:
{text_content}

Your response must be valid, parseable JSON with exactly 10 flashcard objects, starting with [ and ending with ]:"""

    try:
        logger.info("Making OpenAI API call...")
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system", 
                    "content": "You are a helpful assistant that creates educational flashcards from text content. You MUST respond with ONLY a valid JSON array. Do NOT use markdown code fences (```), do NOT add explanations, do NOT add any text before or after the JSON. Your response must start with [ and end with ]."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000,
            timeout=OPENAI_TIMEOUT_SECONDS,  # SECURITY: Prevent hanging requests
        )
        logger.info("✅ OpenAI API call successful")
        
        response_text = response.choices[0].message.content.strip()
        logger.info(f"Raw response length: {len(response_text)} characters")
        logger.debug(f"Raw response preview: {response_text[:500]}...")
        
        # Clean and parse JSON response
        try:
            # First, try direct parsing
            flashcards = json.loads(response_text)
            logger.info(f"✅ JSON parsed directly, got {len(flashcards)} flashcards")
        except json.JSONDecodeError as e:
            logger.warning(f"Direct JSON parse failed: {str(e)}, attempting to clean response...")
            logger.debug(f"Full response text: {response_text}")
            
            try:
                # Clean the response (remove markdown fences, etc.)
                cleaned_text = clean_json_response(response_text)
                flashcards = json.loads(cleaned_text)
                logger.info(f"✅ JSON parsed after cleaning, got {len(flashcards)} flashcards")
            except (json.JSONDecodeError, ValueError) as clean_error:
                # Log the full response for debugging
                logger.error(f"❌ JSON decode error after cleaning: {str(clean_error)}")
                logger.error(f"Original response (first 1000 chars): {response_text[:1000]}")
                logger.error(f"Cleaned response (first 1000 chars): {cleaned_text[:1000] if 'cleaned_text' in locals() else 'N/A'}")
                
                # Raise a clear error with the problematic text
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to parse flashcard response from AI. The AI returned invalid JSON. Please try again."
                )
        
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
