"""
Explore downloaded nflfastR data to understand structure and contents.

Run this after extract_nflfastr.py to validate the data and understand
what columns are available for the pipeline.
"""

import pandas as pd
from pathlib import Path
import sys

def explore_play_by_play(year: int = 2024):
    """Explore play-by-play data structure."""
    file_path = Path(f"data/raw/play_by_play_{year}.parquet")
    
    if not file_path.exists():
        print(f"❌ File not found: {file_path}")
        print("Run extract_nflfastr.py first to download the data.")
        return
    
    print(f"\n{'='*60}")
    print(f"PLAY-BY-PLAY DATA ({year})")
    print(f"{'='*60}\n")
    
    df = pd.read_parquet(file_path)
    
    print(f"Shape: {df.shape[0]:,} plays × {df.shape[1]} columns\n")
    
    print("First few rows:")
    print(df.head(3))
    
    print("\n" + "-"*60)
    print("Key columns for our project:")
    print("-"*60)
    
    key_columns = [
        'game_id', 'play_id', 'posteam', 'defteam',
        'passer_player_name', 'passer_id', 'qb_epa',
        'epa', 'success', 'play_type', 'down', 'ydstogo',
        'season', 'week', 'season_type'
    ]
    
    available_cols = [col for col in key_columns if col in df.columns]
    print(df[available_cols].head())
    
    print("\n" + "-"*60)
    print("Data types:")
    print("-"*60)
    print(df[available_cols].dtypes)
    
    print("\n" + "-"*60)
    print("Missing data:")
    print("-"*60)
    print(df[available_cols].isnull().sum())
    
    print("\n" + "-"*60)
    print("Sample EPA statistics:")
    print("-"*60)
    print(df['epa'].describe())
    
    return df


def explore_participation(year: int = 2024):
    """Explore participation data structure."""
    file_path = Path(f"data/raw/participation_{year}.parquet")
    
    if not file_path.exists():
        print(f"❌ File not found: {file_path}")
        print("Run extract_nflfastr.py first to download the data.")
        return
    
    print(f"\n{'='*60}")
    print(f"PARTICIPATION DATA ({year})")
    print(f"{'='*60}\n")
    
    df = pd.read_parquet(file_path)
    
    print(f"Shape: {df.shape[0]:,} plays × {df.shape[1]} columns\n")
    
    print("All columns:")
    print(df.columns.tolist())
    print("\nFirst few rows:")
    print(df.head(3))
    
    print("\n" + "-"*60)
    print("Personnel groupings sample:")
    print("-"*60)
    
    if 'offense_personnel' in df.columns:
        print("\nOffensive personnel distribution:")
        print(df['offense_personnel'].value_counts().head(10))
    
    if 'defense_personnel' in df.columns:
        print("\nDefensive personnel distribution:")
        print(df['defense_personnel'].value_counts().head(10))
    
    print("\n" + "-"*60)
    print("Sample player data (semicolon-delimited):")
    print("-"*60)
    
    if 'offense_players' in df.columns:
        sample_players = df['offense_players'].iloc[0]
        print(f"Raw: {sample_players}")
        print(f"Split: {sample_players.split(';')[:5]}...")  # Show first 5
    
    return df


def explore_rosters(year: int = 2024):
    """Explore roster data structure."""
    file_path = Path(f"data/raw/roster_{year}.parquet")
    
    if not file_path.exists():
        print(f"❌ File not found: {file_path}")
        print("Run extract_nflfastr.py first to download the data.")
        return
    
    print(f"\n{'='*60}")
    print(f"ROSTER DATA ({year})")
    print(f"{'='*60}\n")
    
    df = pd.read_parquet(file_path)
    
    print(f"Shape: {df.shape[0]:,} players × {df.shape[1]} columns\n")
    
    print("Sample QBs:")
    if 'position' in df.columns:
        qbs = df[df['position'] == 'QB'][['full_name', 'team', 'position']].head(10)
        print(qbs)
    
    return df


def join_example(year: int = 2024):
    """Show how play-by-play and participation data join together."""
    pbp_path = Path(f"data/raw/play_by_play_{year}.parquet")
    part_path = Path(f"data/raw/participation_{year}.parquet")
    
    if not pbp_path.exists() or not part_path.exists():
        print("\n❌ Missing data files. Run extract_nflfastr.py first.")
        return
    
    print(f"\n{'='*60}")
    print(f"JOIN EXAMPLE (Play-by-Play + Participation)")
    print(f"{'='*60}\n")
    
    pbp = pd.read_parquet(pbp_path)
    part = pd.read_parquet(part_path)
    
    print(f"Play-by-play columns: {pbp.columns.tolist()[:10]}...")
    print(f"Participation columns: {part.columns.tolist()}\n")
    
    # Find common columns for joining
    common_cols = list(set(pbp.columns) & set(part.columns))
    print(f"Common columns for joining: {common_cols}\n")
    
    # Typical join keys for nflfastR data
    join_keys = [col for col in ['game_id', 'play_id', 'old_game_id', 'nflverse_game_id'] 
                 if col in common_cols]
    
    if not join_keys:
        print("❌ No common join keys found!")
        print("\nPlay-by-play sample:")
        print(pbp.head(2))
        print("\nParticipation sample:")
        print(part.head(2))
        return
    
    print(f"Using join keys: {join_keys}\n")
    
    # Join on available keys
    joined = pbp.merge(
        part,
        on=join_keys,
        how='inner'
    )
    
    print(f"Play-by-play rows: {len(pbp):,}")
    print(f"Participation rows: {len(part):,}")
    print(f"Joined rows: {len(joined):,}")
    print(f"Join rate: {len(joined)/len(pbp)*100:.1f}%\n")
    
    print("Sample joined data with personnel info:")
    cols_to_show = [
        'game_id', 'play_id', 'passer_player_name', 'epa',
        'offense_personnel', 'defense_personnel', 'nflverse_game_id', 'old_game_id'
    ]
    available = [col for col in cols_to_show if col in joined.columns]
    print(joined[available].head(10))
    
    return joined


def main():
    """Run all exploration functions."""
    print("\n" + "🏈"*30)
    print("NFL DATA EXPLORATION")
    print("🏈"*30)
    
    # Explore each data type
    explore_play_by_play(2024)
    explore_participation(2024)
    explore_rosters(2024)
    
    # Show join example
    join_example(2024)
    
    print("\n" + "="*60)
    print("✅ Exploration complete!")
    print("="*60)


if __name__ == "__main__":
    main()