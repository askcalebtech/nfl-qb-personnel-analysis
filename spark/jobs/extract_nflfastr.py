"""
Extract NFL play-by-play and participation data from nflfastR repository.

This script downloads parquet files directly from the nflfastR GitHub releases,
avoiding dependency conflicts with the nfl-data-py wrapper library.

Data sources:
- Play-by-play: https://github.com/nflverse/nflverse-data/releases/download/pbp/
- Rosters: https://github.com/nflverse/nflverse-data/releases/download/rosters/
- Participation: https://github.com/nflverse/nflverse-data/releases/download/pbp_participation/
"""

import os
import sys
import pandas as pd
import requests
from pathlib import Path
from typing import List, Optional
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class NFLDataExtractor:
    """Extracts NFL data from nflfastR GitHub repository."""
    
    BASE_URL = "https://github.com/nflverse/nflverse-data/releases/download"
    
    def __init__(self, output_dir: str = "data/raw"):
        """
        Initialize the data extractor.
        
        Args:
            output_dir: Directory to save downloaded parquet files
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def download_file(self, url: str, output_path: Path) -> bool:
        """
        Download a file from URL to local path.
        
        Args:
            url: URL to download from
            output_path: Local path to save file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Downloading from {url}")
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    
            logger.info(f"Successfully saved to {output_path}")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to download {url}: {e}")
            return False
    
    def extract_play_by_play(self, years: List[int]) -> List[Path]:
        """
        Extract play-by-play data for specified years.
        
        Args:
            years: List of seasons to download (e.g., [2022, 2023, 2024])
            
        Returns:
            List of paths to downloaded files
        """
        downloaded_files = []
        
        for year in years:
            url = f"{self.BASE_URL}/pbp/play_by_play_{year}.parquet"
            output_path = self.output_dir / f"play_by_play_{year}.parquet"
            
            # Skip if already exists
            if output_path.exists():
                logger.info(f"File already exists: {output_path}")
                downloaded_files.append(output_path)
                continue
            
            if self.download_file(url, output_path):
                downloaded_files.append(output_path)
                
                # Log some basic stats about the data
                try:
                    df = pd.read_parquet(output_path)
                    logger.info(f"  → {year}: {len(df):,} plays, {len(df.columns)} columns")
                except Exception as e:
                    logger.warning(f"Could not read parquet file: {e}")
        
        return downloaded_files
    
    def extract_participation(self, years: List[int]) -> List[Path]:
        """
        Extract participation data for specified years.
        
        Args:
            years: List of seasons to download (e.g., [2022, 2023, 2024])
            
        Returns:
            List of paths to downloaded files
        """
        downloaded_files = []
        
        for year in years:
            url = f"{self.BASE_URL}/pbp_participation/pbp_participation_{year}.parquet"
            output_path = self.output_dir / f"participation_{year}.parquet"
            
            # Skip if already exists
            if output_path.exists():
                logger.info(f"File already exists: {output_path}")
                downloaded_files.append(output_path)
                continue
            
            if self.download_file(url, output_path):
                downloaded_files.append(output_path)
                
                # Log some basic stats
                try:
                    df = pd.read_parquet(output_path)
                    logger.info(f"  → {year}: {len(df):,} plays with participation data")
                except Exception as e:
                    logger.warning(f"Could not read parquet file: {e}")
        
        return downloaded_files
    
    def extract_rosters(self, years: List[int]) -> List[Path]:
        """
        Extract roster data for specified years.
        
        Args:
            years: List of seasons to download
            
        Returns:
            List of paths to downloaded files
        """
        downloaded_files = []
        
        for year in years:
            url = f"{self.BASE_URL}/rosters/roster_{year}.parquet"
            output_path = self.output_dir / f"roster_{year}.parquet"
            
            # Skip if already exists
            if output_path.exists():
                logger.info(f"File already exists: {output_path}")
                downloaded_files.append(output_path)
                continue
            
            if self.download_file(url, output_path):
                downloaded_files.append(output_path)
                
                # Log some basic stats
                try:
                    df = pd.read_parquet(output_path)
                    logger.info(f"  → {year}: {len(df):,} players")
                except Exception as e:
                    logger.warning(f"Could not read parquet file: {e}")
        
        return downloaded_files
    
    def extract_all(self, years: List[int]) -> dict:
        """
        Extract all data types for specified years.
        
        Args:
            years: List of seasons to download
            
        Returns:
            Dictionary with lists of downloaded file paths by type
        """
        logger.info(f"Starting data extraction for years: {years}")
        
        results = {
            'play_by_play': self.extract_play_by_play(years),
            'participation': self.extract_participation(years),
            'rosters': self.extract_rosters(years)
        }
        
        logger.info("Data extraction complete!")
        return results


def main():
    """Main execution function."""
    # Configuration
    YEARS = [2022, 2023, 2024, 2025]  # Seasons to download (2025 = current season)
    OUTPUT_DIR = "data/raw"
    
    # Initialize extractor
    extractor = NFLDataExtractor(output_dir=OUTPUT_DIR)
    
    # Extract all data
    print(f"\nAttempting to download data for years: {YEARS}")
    print("Note: 2025 participation data may be incomplete (season in progress)\n")
    
    results = extractor.extract_all(years=YEARS)
    
    # Summary
    print("\n" + "="*60)
    print("EXTRACTION SUMMARY")
    print("="*60)
    for data_type, files in results.items():
        print(f"{data_type}: {len(files)} files downloaded")
        if not files:
            print(f"  ⚠️  No files downloaded for {data_type}")
    print("="*60)
    
    # Specific check for 2025 participation
    participation_2025 = Path(OUTPUT_DIR) / "participation_2025.parquet"
    if participation_2025.exists():
        print(f"\n✅ 2025 participation data found!")
    else:
        print(f"\n⚠️  2025 participation data not available yet")
        print("   This is normal - participation data lags behind play-by-play data")
        print("   You can still process 2022-2024 data for now")


if __name__ == "__main__":
    main()