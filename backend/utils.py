"""
Utility functions for the Second Brain application.
"""
from typing import Union

def clamp(value: Union[int, float, None], default: Union[int, float], min_val: Union[int, float], max_val: Union[int, float]) -> Union[int, float]:
    """
    Clamp a value to a specified range with a fallback default.
    
    Args:
        value: The value to clamp (can be None)
        default: Default value if input is None or invalid
        min_val: Minimum allowed value
        max_val: Maximum allowed value
    
    Returns:
        Clamped value within the specified range
    """
    if value is None:
        return default
    
    try:
        # Convert to float first to handle both int and float inputs
        num_value = float(value)
        if num_value < min_val:
            return min_val
        elif num_value > max_val:
            return max_val
        else:
            return num_value
    except (ValueError, TypeError):
        return default

