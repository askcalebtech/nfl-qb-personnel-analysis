"""
Personnel Parser Utility

Converts detailed personnel strings from nflfastR into standardized notation:
- Offensive: "1 RB, 1 TE, 3 WR" format → "11" notation
- Defensive: Count DBs → "Base", "Nickel", "Dime", "Quarter"

Pure Python functions (no Spark dependency) for easy unit testing.
"""

import re
from typing import Optional, Dict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Position groupings for parsing
OFFENSIVE_SKILL_POSITIONS = {'RB', 'FB', 'TE', 'WR'}
DEFENSIVE_BACK_POSITIONS = {'CB', 'FS', 'SS', 'S', 'DB'}


def parse_position_counts(personnel_string: str) -> Dict[str, int]:
    """
    Parse a personnel string into position counts.
    
    Args:
        personnel_string: e.g., "1 C, 2 G, 1 QB, 1 RB, 2 T, 1 TE, 3 WR"
        
    Returns:
        Dict of position -> count, e.g., {"RB": 1, "TE": 1, "WR": 3}
        
    Example:
        >>> parse_position_counts("1 C, 2 G, 1 QB, 1 RB, 2 T, 1 TE, 3 WR")
        {'C': 1, 'G': 2, 'QB': 1, 'RB': 1, 'T': 2, 'TE': 1, 'WR': 3}
    """
    if not personnel_string or pd.isna(personnel_string):
        return {}
    
    position_counts = {}
    
    # Pattern: "2 G" or "1 RB" (number followed by position abbreviation)
    pattern = r'(\d+)\s+([A-Z]+)'
    matches = re.findall(pattern, str(personnel_string))
    
    for count, position in matches:
        position_counts[position] = int(count)
    
    return position_counts


def standardize_offensive_personnel(personnel_string: str) -> Optional[str]:
    """
    Convert offensive personnel string to standard notation (RB-TE-WR format).
    
    Standard notation format: "{RBs}{TEs}" 
    - "11" = 1 RB, 1 TE, 3 WR (most common, 11 personnel)
    - "12" = 1 RB, 2 TE, 2 WR (12 personnel)
    - "21" = 2 RB, 1 TE, 2 WR (21 personnel)
    - "10" = 1 RB, 0 TE, 4 WR (10 personnel, empty)
    
    Args:
        personnel_string: Raw nflfastR personnel, e.g., "1 C, 2 G, 1 QB, 1 RB, 2 T, 1 TE, 3 WR"
        
    Returns:
        Standardized notation string (e.g., "11", "12", "21") or None if invalid
        
    Example:
        >>> standardize_offensive_personnel("1 C, 2 G, 1 QB, 1 RB, 2 T, 1 TE, 3 WR")
        "11"
    """
    if not personnel_string or pd.isna(personnel_string):
        return None
    
    counts = parse_position_counts(personnel_string)
    
    # Extract skill position counts (RB + FB counted together)
    rb_count = counts.get('RB', 0) + counts.get('FB', 0)  # FB counts as RB
    te_count = counts.get('TE', 0)
    wr_count = counts.get('WR', 0)
    
    # Validate: should have 5 total skill positions (standard 11-man offense)
    total_skill = rb_count + te_count + wr_count
    
    if total_skill != 5:
        # Edge case: some formations have non-standard counts
        logger.debug(f"Non-standard skill position count ({total_skill}): {personnel_string}")
        # Still try to categorize by RB-TE pattern
    
    # Create standard notation: "{RBs}{TEs}"
    return f"{rb_count}{te_count}"


def classify_defensive_personnel(personnel_string: str) -> Optional[str]:
    """
    Classify defensive personnel into standard categories based on DB count.
    
    Categories:
    - "Base": 4 DBs (traditional defense)
    - "Nickel": 5 DBs (most common, 60%+ of plays)
    - "Dime": 6 DBs (passing situations)
    - "Quarter": 7+ DBs (prevent defense)
    
    Args:
        personnel_string: Raw nflfastR personnel, e.g., "3 CB, 2 DE, 2 DT, 1 FS, 2 ILB, 1 SS"
        
    Returns:
        Category string ("Base", "Nickel", "Dime", "Quarter") or None if invalid
        
    Example:
        >>> classify_defensive_personnel("3 CB, 2 DE, 2 DT, 1 FS, 2 ILB, 1 SS")
        "Nickel"
    """
    if not personnel_string or pd.isna(personnel_string):
        return None
    
    counts = parse_position_counts(personnel_string)
    
    # Count total defensive backs (CB + FS + SS + S + DB)
    db_count = sum(counts.get(pos, 0) for pos in DEFENSIVE_BACK_POSITIONS)
    
    # Classify based on DB count
    if db_count <= 4:
        return "Base"
    elif db_count == 5:
        return "Nickel"
    elif db_count == 6:
        return "Dime"
    elif db_count >= 7:
        return "Quarter"
    else:
        logger.warning(f"Unexpected DB count ({db_count}): {personnel_string}")
        return None


def standardize_personnel_batch(
    offense_personnel_list: list,
    defense_personnel_list: list
) -> tuple:
    """
    Batch process personnel strings (useful for Pandas/Spark operations).
    
    Args:
        offense_personnel_list: List of offensive personnel strings
        defense_personnel_list: List of defensive personnel strings
        
    Returns:
        Tuple of (standardized_offense_list, classified_defense_list)
    """
    standardized_offense = [
        standardize_offensive_personnel(p) for p in offense_personnel_list
    ]
    classified_defense = [
        classify_defensive_personnel(p) for p in defense_personnel_list
    ]
    
    return standardized_offense, classified_defense


# Import pandas for isna checks
try:
    import pandas as pd
except ImportError:
    # Fallback if pandas not available
    class pd:
        @staticmethod
        def isna(x):
            return x is None or (isinstance(x, float) and x != x)


if __name__ == "__main__":
    # Test the personnel parsing functions
    print("Testing Personnel Parser\n")
    print("="*60)
    
    # Test offensive personnel standardization
    test_offense = [
        "1 C, 2 G, 1 QB, 1 RB, 2 T, 1 TE, 3 WR",  # Should be "11"
        "1 C, 2 G, 1 QB, 1 RB, 2 T, 2 TE, 2 WR",  # Should be "12"
        "1 C, 2 G, 1 QB, 2 RB, 2 T, 1 TE, 2 WR",  # Should be "21"
        "1 C, 1 FB, 2 G, 1 QB, 1 RB, 2 T, 1 TE, 2 WR",  # Should be "21" (FB=RB)
        "1 C, 2 G, 1 QB, 1 RB, 2 T, 0 TE, 4 WR",  # Should be "10"
    ]
    
    print("OFFENSIVE PERSONNEL STANDARDIZATION:")
    print("-"*60)
    for personnel in test_offense:
        result = standardize_offensive_personnel(personnel)
        print(f"{personnel}")
        print(f"  → {result}\n")
    
    # Test defensive personnel classification
    test_defense = [
        "3 CB, 2 DE, 2 DT, 1 FS, 2 ILB, 1 SS",  # 5 DBs = Nickel
        "2 CB, 2 DE, 2 DT, 1 FS, 3 ILB, 1 SS",  # 4 DBs = Base
        "4 CB, 2 DE, 2 DT, 2 FS",                # 6 DBs = Dime
        "4 CB, 2 DE, 1 DT, 1 FS, 1 ILB, 2 SS",  # 7 DBs = Quarter
    ]
    
    print("\nDEFENSIVE PERSONNEL CLASSIFICATION:")
    print("-"*60)
    for personnel in test_defense:
        result = classify_defensive_personnel(personnel)
        counts = parse_position_counts(personnel)
        db_count = sum(counts.get(pos, 0) for pos in DEFENSIVE_BACK_POSITIONS)
        print(f"{personnel}")
        print(f"  → {db_count} DBs = {result}\n")
    
    print("="*60)
    print("✅ Testing complete!")