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
    
    prompt = f"""You are an expert instructional designer and subject-matter tutor. Create EXACTLY 10 high-impact flashcards from the PDF content below.

OUTPUT FORMAT (STRICT):
- Output ONLY a valid JSON array (no markdown fences, no extra text, no preamble).
- The array must contain exactly 10 objects.
- Each object must have exactly two keys:
  - "question": string
  - "answer": string
- No additional keys. No nested objects. No trailing commentary.
- Your entire response begins with [ and ends with ].

CONTENT GROUNDING (NO INVENTION):
- Use ONLY information that is explicitly or implicitly supported by the provided PDF content.
- If a detail is not present or is uncertain, do NOT guess, invent, or extrapolate beyond the text. Reframe the question to match what is demonstrably supported.
- When PDF provides examples, use them; when it provides principles, generalize appropriately.
- Do not reference "the PDF says…" or "according to…" in the card text. Write as standalone, timeless learning cards.

CARD DESIGN PHILOSOPHY:
Your flashcards should serve as cognitive scaffolds—each card bridges from what the learner knows to deeper understanding. Prioritize cards that unlock insight, reveal dependencies between concepts, and expose common traps.

QUESTION DESIGN (HIGH PRIORITY):
Questions must:
- Test understanding over recall; strongly prefer one of these verb types:
  • "Why does X occur? What mechanism is at work?"
  • "How would you approach/design/troubleshoot X given constraint Y?"
  • "What would happen if X changed? Why?"
  • "Compare/contrast X and Y. When would you choose one over the other?"
  • "What is a common mistake when dealing with X? Why is it wrong?"
  • "Identify the assumption/limitation/risk in this scenario."
- Be concrete and specific (avoid vague prompts like "Explain X"; instead: "Why is X preferred in Y context?").
- Include a mini-scenario, constraint, or context clue when it grounds the question in real application.
- Avoid pure yes/no questions and single-word-answer questions; they test shallow recall.
- Use precise, domain-appropriate terminology consistent with the PDF.
- Frame questions so the answer is not obvious from the question wording alone.

ANSWER DESIGN (HIGH PRIORITY):
Answers must:
- Be concise: 1–3 sentences, strictly under 50 words (count them).
- Be directly responsive to the question (no tangents, no disclaimers).
- Include one supporting detail, rationale, or constraint that explains the "why" or "when" behind the answer when applicable.
- Use active, declarative language ("X occurs because…" not "One could argue that…").
- Avoid bullet lists entirely unless more than 2 items are essential; if used, limit to maximum 2 bullets with minimal text.
- If the answer requires an equation or notation, include it but immediately explain symbols in parentheses.

CARD COMPOSITION (MANDATORY DISTRIBUTION):
Ensure your 10 cards include:
- 2 foundational cards: Definition/core-concept cards (e.g., "What distinguishes X from Y?" or "What does X mean in the context of Y?").
- 4 application/analysis cards: Scenario-based or problem-solving cards (e.g., "You observe X in a system; what is the most likely cause and why?" or "How would you modify X to achieve Y?").
- 2 synthesis/evaluation cards: Cards addressing tradeoffs, design choices, system interactions, or failure modes (e.g., "Why is X chosen over Y despite Z limitation?" or "How does changing X impact Y and Z?").
- 2 misconception/error-prevention cards: Cards exposing common pitfalls, edge cases, or false assumptions (e.g., "Why does the intuitive approach to X fail?" or "What is the hidden cost or constraint in X?").

Validation Before Response:
- Verify exactly 10 flashcards are included
- Confirm each flashcard has both "question" and "answer" fields with string values
- Ensure the JSON is valid and properly formatted
- Test that your response can be parsed as JSON without errors

CONTENT SELECTION & COVERAGE:
- Identify the 10 most important, conceptually rich topics from the PDF—prioritize ideas that are foundational, frequently misunderstood, or critical to downstream application.
- Ensure diversity: no two cards should address the same narrow fact or restate the same concept.
- Include at least 2 cards that explicitly link concepts (e.g., cause-and-effect, design tradeoff, dependency, or interaction between ideas).
- Use consistent terminology throughout all 10 cards—do not rename the same concept or use synonyms interchangeably; build a coherent mental model.
- Exclude trivial, low-impact details; focus on knowledge that transfers across problems and contexts.
- Where relevant, include one question addressing common misconceptions or edge cases
NOTATION & TECHNICAL CONTENT:
- If the PDF includes equations, formulas, or technical notation, include only the minimum essential for the card and immediately explain any symbols in parentheses or as part of the answer.
- Prefer conceptual understanding over symbolic manipulation.

READABILITY & TONE:
- Use clear, direct, student-friendly language; assume an engaged learner, not a novice.
- Avoid jargon without context; if a term is essential, use it correctly and consistently.
- Write in active voice where possible ("X causes Y" vs. "Y is caused by X").

FINAL SELF-VALIDATION (MANDATORY—PERFORM BEFORE OUTPUT):
Before outputting your JSON, verify the following:
1. Count: exactly 10 cards—no more, no fewer.
2. Schema: each card has ONLY "question" and "answer" keys, both strings. No extra fields.
3. Grounding: every factual claim in every card is traceable to the PDF content; no invented or extrapolated details.
4. Distribution: the composition requirement is met (2 foundational, 4 application, 2 synthesis, 2 misconception).
5. Quality: at least 80% of questions are "why/how/compare/design/diagnose" style (not recall).
6. Diversity: no two cards overlap in topic; no redundant concepts.
7. Coherence: terminology is consistent across cards; concepts build on each other where appropriate.
8. Conciseness: every answer is under 50 words and directly answers the question.
9. JSON validity: your response is valid JSON that parses cleanly.
10. Format: your output begins with [ and ends with ]; no extra text before or after.

PDF CONTENT:
{text_content}

Return only the JSON array now:"""

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
