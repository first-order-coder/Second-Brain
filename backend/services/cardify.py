"""
Cardify service for processing transcript segments into semantic windows
and selecting key points for flashcard generation.
"""
import re
import json
from typing import List, Dict, Tuple
from collections import defaultdict

def merge_small_segments(segments: List[Dict], max_gap: float = 1.2) -> List[Dict]:
    """
    Merge segments that are close together in time.
    Returns coalesced segments with merged text.
    """
    if not segments:
        return []
    
    merged = []
    # Convert transcript objects to dicts if needed
    current_segment = dict(segments[0]) if not hasattr(segments[0], 'copy') else segments[0].copy()
    
    for segment in segments[1:]:
        # Convert to dict if needed
        segment_dict = dict(segment) if not hasattr(segment, 'copy') else segment.copy()
        
        gap = segment_dict['start'] - current_segment['end']
        
        if gap <= max_gap:
            # Merge segments
            current_segment['text'] += ' ' + segment_dict['text']
            current_segment['end'] = segment_dict['end']
        else:
            # Start new segment
            merged.append(current_segment)
            current_segment = segment_dict.copy()
    
    merged.append(current_segment)
    return merged

def semantic_windows(segments: List[Dict], target_window_chars: int = 800) -> List[Dict]:
    """
    Build windows that end on sentence boundaries and respect character limits.
    Returns list of windows with start/end times and text.
    """
    if not segments:
        return []
    
    windows = []
    current_window = {
        'text': '',
        'start': segments[0]['start'],
        'end': segments[0]['end'],
        'segments': []
    }
    
    for segment in segments:
        segment_text = segment['text'].strip()
        if not segment_text:
            continue
        
        # Check if adding this segment would exceed target length
        potential_text = current_window['text'] + ' ' + segment_text if current_window['text'] else segment_text
        
        if len(potential_text) > target_window_chars and current_window['text']:
            # Try to end at sentence boundary
            sentences = re.split(r'[.!?]+\s+', current_window['text'])
            if len(sentences) > 1:
                # Keep all but last sentence
                current_window['text'] = '. '.join(sentences[:-1]) + '.'
            
            # Finalize current window
            windows.append(current_window)
            
            # Start new window
            current_window = {
                'text': segment_text,
                'start': segment['start'],
                'end': segment['end'],
                'segments': [segment]
            }
        else:
            # Add to current window
            current_window['text'] = potential_text
            current_window['end'] = segment['end']
            current_window['segments'].append(segment)
    
    # Add final window if it has content
    if current_window['text']:
        windows.append(current_window)
    
    return windows

def select_key_points(windows: List[Dict], k: int) -> List[Dict]:
    """
    Select top k*2 windows using rudimentary scoring.
    Prioritizes definitions, questions, and content with educational value.
    """
    if not windows:
        return []
    
    scored_windows = []
    
    for window in windows:
        score = 0
        text = window['text'].lower()
        
        # Score based on content indicators
        definition_patterns = [
            r'\b(?:is|are|was|were|means?|refers to|defined as)\b',
            r'\b(?:definition|define|meaning)\b',
            r'\b(?:example|for instance|such as)\b',
            r'\b(?:because|since|due to|therefore)\b',
            r'\b(?:however|but|although|despite)\b',
            r'\b(?:first|second|third|initially|then|finally)\b',
            r'\b(?:important|key|crucial|essential)\b',
            r'\b(?:difference|compare|contrast|versus|vs)\b',
            r'\b(?:how|why|what|when|where)\b'
        ]
        
        for pattern in definition_patterns:
            matches = len(re.findall(pattern, text))
            score += matches * 2
        
        # Bonus for question patterns
        question_patterns = [
            r'\?',
            r'\b(?:what|how|why|when|where|which|who)\b.*\?',
            r'\b(?:can you|could you|would you)\b'
        ]
        
        for pattern in question_patterns:
            matches = len(re.findall(pattern, text))
            score += matches * 3
        
        # Penalty for very short or very long content
        word_count = len(text.split())
        if word_count < 10:
            score -= 2
        elif word_count > 200:
            score -= 1
        
        # Bonus for content with numbers (often indicates facts)
        if re.search(r'\d+', text):
            score += 1
        
        # Bonus for content with proper nouns (often indicates important entities)
        if re.search(r'\b[A-Z][a-z]+ [A-Z][a-z]+\b', window['text']):
            score += 1
        
        scored_windows.append((score, window))
    
    # Sort by score (descending) and take top k*2
    scored_windows.sort(key=lambda x: x[0], reverse=True)
    selected_windows = [window for score, window in scored_windows[:int(k)*2]]
    
    # Ensure we have some diversity - don't take all from the beginning
    if len(selected_windows) > int(k):
        # Take some from different parts of the video
        step = max(1, len(selected_windows) // int(k))
        selected_windows = selected_windows[::step][:int(k)]
    
    return selected_windows

def prepare_excerpts_for_llm(windows: List[Dict]) -> str:
    """
    Format windows as JSON for LLM processing.
    Returns JSON string with excerpt data.
    """
    excerpts = []
    
    for i, window in enumerate(windows):
        excerpt = {
            "excerpt_id": i + 1,
            "start_s": window['start'],
            "end_s": window['end'],
            "text": window['text'].strip()
        }
        excerpts.append(excerpt)
    
    return json.dumps(excerpts, indent=2)

def deduplicate_cards(cards: List[Dict]) -> List[Dict]:
    """
    Remove duplicate or very similar cards based on Jaccard similarity of answers.
    """
    if len(cards) <= 1:
        return cards
    
    def jaccard_similarity(text1: str, text2: str) -> float:
        """Calculate Jaccard similarity between two texts."""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 and not words2:
            return 1.0
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0
    
    deduplicated = []
    used_indices = set()
    
    for i, card in enumerate(cards):
        if i in used_indices:
            continue
        
        # Check similarity with remaining cards
        is_duplicate = False
        for j, other_card in enumerate(cards[i+1:], i+1):
            if j in used_indices:
                continue
            
            similarity = jaccard_similarity(card.get('back', ''), other_card.get('back', ''))
            if similarity > 0.7:  # 70% similarity threshold
                is_duplicate = True
                used_indices.add(j)
                break
        
        if not is_duplicate:
            deduplicated.append(card)
            used_indices.add(i)
    
    return deduplicated

def truncate_answer(answer: str, max_words: int = 45) -> str:
    """Truncate answer to maximum word count."""
    words = answer.split()
    if len(words) <= max_words:
        return answer
    
    return ' '.join(words[:max_words]) + '...'
