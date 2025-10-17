"""
LLM integration for generating flashcards from transcript excerpts.
"""
import json
import logging
import os
from typing import Dict, List, Any
import openai
from openai import OpenAI

logger = logging.getLogger(__name__)

def call_llm_json(system_prompt: str, user_prompt: str) -> Dict[str, Any]:
    """
    Call OpenAI API and return STRICT JSON response.
    """
    try:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=2000,
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content
        return json.loads(content)
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM JSON response: {e}")
        raise Exception("LLM returned invalid JSON")
    except Exception as e:
        logger.error(f"LLM API call failed: {e}")
        raise Exception(f"LLM API call failed: {str(e)}")

def generate_flashcards_from_excerpts(excerpts_json: str, n_cards: int = 10, target_count: int = None) -> List[Dict[str, Any]]:
    """
    Generate flashcards from transcript excerpts using LLM.
    
    Args:
        excerpts_json: JSON string containing transcript excerpts
        n_cards: Legacy parameter for backward compatibility
        target_count: Target number of cards to generate (overrides n_cards if provided)
    """
    # Use target_count if provided, otherwise fall back to n_cards
    actual_target = target_count if target_count is not None else n_cards
    
    system_prompt = """You write concise, atomic study flashcards. Each card tests one fact, definition, relation, or small procedure. Answers are short, factual, and testable. Use simple language. Avoid fluff and opinions."""

    user_prompt = f"""Create exactly {actual_target} high-quality flashcards from the transcript excerpts below.

Rules:
- You MUST produce at most {actual_target} flashcards.
- Prefer quality and coverage. If content is insufficient, produce fewer.
- Prefer "why/how" and "compare/contrast" when justified by the text.
- Keep each answer ≤ 45 words.
- Include a short evidence quote ≤ 18 words copied from the excerpt.
- If a cloze fits naturally, include it; otherwise set cloze to null.
- Return timestamps from the provided start_s/end_s.
- Output STRICT JSON:
  {{"cards":[{{"front": "...", "back":"...", "cloze": null|"...", "start_s": number, "end_s": number, "evidence":"...", "difficulty":"easy"|"medium"|"hard"|null, "tags":["youtube"]}}]}}

Transcript excerpts (JSON):
<<<
{excerpts_json}
>>>"""

    try:
        result = call_llm_json(system_prompt, user_prompt)
        cards = result.get('cards', [])
        
        # Validate and clean cards
        cleaned_cards = []
        for card in cards:
            cleaned_card = {
                'front': card.get('front', '').strip(),
                'back': card.get('back', '').strip(),
                'cloze': card.get('cloze'),
                'start_s': card.get('start_s'),
                'end_s': card.get('end_s'),
                'evidence': card.get('evidence', '').strip(),
                'difficulty': card.get('difficulty'),
                'tags': card.get('tags', ['youtube'])
            }
            
            # Ensure required fields
            if not cleaned_card['front'] or not cleaned_card['back']:
                continue
            
            # Truncate long answers
            if len(cleaned_card['back'].split()) > 45:
                cleaned_card['back'] = ' '.join(cleaned_card['back'].split()[:45]) + '...'
            
            # Ensure timestamps are numbers
            try:
                cleaned_card['start_s'] = float(cleaned_card['start_s']) if cleaned_card['start_s'] is not None else None
                cleaned_card['end_s'] = float(cleaned_card['end_s']) if cleaned_card['end_s'] is not None else None
            except (ValueError, TypeError):
                cleaned_card['start_s'] = None
                cleaned_card['end_s'] = None
            
            cleaned_cards.append(cleaned_card)
        
        # Enforce exact count: truncate if more than target, return whatever we have if fewer
        if len(cleaned_cards) > actual_target:
            cleaned_cards = cleaned_cards[:int(actual_target)]
        
        return cleaned_cards
        
    except Exception as e:
        logger.error(f"Failed to generate flashcards: {e}")
        raise Exception(f"Flashcard generation failed: {str(e)}")
