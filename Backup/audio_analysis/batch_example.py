#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Example: Batch Processing Multiple Audio Files
==============================================
Demonstrates how to analyze multiple audio files (up to 100) in batch mode.
"""

from pathlib import Path
from batch_audio_analyzer import BatchAudioAnalyzer
import glob

def main():
    """Example batch processing."""
    
    # Example 1: Process all WAV files in a directory
    audio_directory = Path("path/to/your/audio/files")
    audio_files = list(audio_directory.glob("*.wav"))
    
    # Limit to 100 files
    if len(audio_files) > 100:
        print(f"Found {len(audio_files)} files. Limiting to first 100.")
        audio_files = audio_files[:100]
    
    # Create batch analyzer
    batch_analyzer = BatchAudioAnalyzer(
        audio_files=audio_files,
        output_dir=Path("batch_results"),
        max_workers=4,  # Use 4 parallel workers
        harmonic_tolerance=0.02,
        use_90_tier=True,
        auto_extract_weights=True
    )
    
    # Run batch analysis
    print(f"Starting batch analysis of {len(audio_files)} files...")
    results = batch_analyzer.run_batch_analysis()
    
    # Print summary
    print("\n" + "="*60)
    print("BATCH ANALYSIS SUMMARY")
    print("="*60)
    print(f"Total files: {results['summary']['total_files']}")
    print(f"Successful: {results['summary']['successful_count']}")
    print(f"Failed: {results['summary']['failed_count']}")
    
    if 'metrics' in results['summary']:
        print("\nAverage Metrics:")
        for metric_name, stats in results['summary']['metrics'].items():
            print(f"  {metric_name}:")
            print(f"    Mean: {stats['mean']:.4f}")
            print(f"    Std:  {stats['std']:.4f}")
            print(f"    Range: {stats['min']:.4f} - {stats['max']:.4f}")
    
    print(f"\nResults saved to: batch_results/")
    print("  - batch_results.json: Detailed results")
    print("  - batch_summary.xlsx: Summary table (Excel format)")
    print("  - batch_statistics.txt: Statistics report")


if __name__ == '__main__':
    main()

