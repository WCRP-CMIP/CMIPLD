#!/usr/bin/env python3
"""
Command-Line Interface for JSON-LD Validation

This module provides the command-line interface for the JSON-LD validation tool,
including argument parsing, configuration, and main execution logic.
"""

import argparse
import os
import sys
import time
from pathlib import Path
from typing import Optional

# from ..logging.unique import UniqueLogger, logging
from .validator import JSONValidator
from .context_manager import ContextManager
from .git_integration import GitCoauthorManager
from .reporting import ValidationReporter

log = UniqueLogger()
# need to fix 

def create_argument_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser."""
    parser = argparse.ArgumentParser(
        description="Validate and fix JSON-LD files for CMIP-LD compliance",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic validation
  python -m cmipld.utils.validate_json .
  
  # Dry run to see what would change
  python -m cmipld.utils.validate_json /path/to/files --dry-run
  
  # Context-aware validation
  python -m cmipld.utils.validate_json . --context context.json
  
  # Validation with more workers
  python -m cmipld.utils.validate_json /path/to/files --workers 8
  
  # Validate and add co-authors to modified files
  python -m cmipld.utils.validate_json . --add-coauthors
  
  # Validate, fix, and auto-commit with co-authors
  python -m cmipld.utils.validate_json . --add-coauthors --auto-commit
  
  # Use the last commit author instead of current user
  python -m cmipld.utils.validate_json . --use-last-author
  
  # Generate JSON report
  python -m cmipld.utils.validate_json . --report output.json
        """
    )

    # Required arguments
    parser.add_argument(
        'directory', 
        help='Directory containing JSON files to validate'
    )

    # Core options
    parser.add_argument(
        '--dry-run', '-n', 
        action='store_true', 
        help='Show changes without modifying files'
    )
    
    parser.add_argument(
        '--context', '-c',
        type=str,
        help='Path to JSON-LD context file for context-aware validation'
    )
    
    parser.add_argument(
        '--workers', '-w', 
        type=int, 
        default=4, 
        help='Number of parallel workers (default: 4)'
    )

    # Logging options
    parser.add_argument(
        '--verbose', '-v', 
        action='store_true', 
        help='Enable verbose logging'
    )
    
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Suppress non-essential output'
    )

    # Git integration options
    parser.add_argument(
        '--add-coauthors', '-a', 
        action='store_true', 
        help='Add historic file authors as co-authors when modifying files'
    )
    
    parser.add_argument(
        '--use-last-author', '-l',
        action='store_true',
        help='Use the author of the last commit instead of current user'
    )
    
    parser.add_argument(
        '--auto-commit', '-m',
        action='store_true',
        help='Automatically create a commit with co-authors after modifications'
    )

    # Reporting options
    parser.add_argument(
        '--report', '-r',
        type=str,
        help='Generate JSON report and save to specified file'
    )

    # Advanced options
    parser.add_argument(
        '--required-keys',
        type=str,
        nargs='+',
        help='Custom list of required keys (overrides defaults)'
    )
    
    parser.add_argument(
        '--config',
        type=str,
        help='Path to configuration file (JSON format)'
    )

    return parser


def load_configuration(config_file: str) -> dict:
    """
    Load configuration from JSON file.
    
    Args:
        config_file: Path to configuration file
        
    Returns:
        Configuration dictionary
    """
    import json
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        log.info(f"Loaded configuration from: {config_file}")
        return config
    except Exception as e:
        log.error(f"Failed to load configuration from {config_file}: {e}")
        return {}


def validate_arguments(args) -> bool:
    """
    Validate command-line arguments for consistency and requirements.
    
    Args:
        args: Parsed arguments namespace
        
    Returns:
        True if valid, False otherwise
    """
    # Check directory exists
    if not os.path.exists(args.directory):
        print(f"❌ Error: Directory '{args.directory}' does not exist")
        return False

    if not os.path.isdir(args.directory):
        print(f"❌ Error: '{args.directory}' is not a directory")
        return False

    # Check context file if specified
    if args.context and not os.path.exists(args.context):
        print(f"❌ Error: Context file '{args.context}' does not exist")
        return False

    # Validate argument combinations
    if args.auto_commit and args.dry_run:
        print("❌ Error: Cannot use --auto-commit with --dry-run")
        return False

    if args.verbose and args.quiet:
        print("❌ Error: Cannot use --verbose and --quiet together")
        return False

    if args.workers < 1 or args.workers > 32:
        print("❌ Error: Number of workers must be between 1 and 32")
        return False

    return True


def configure_logging(args) -> None:
    """Configure logging based on command-line arguments."""
    if args.verbose:
        log.logger.setLevel(logging.DEBUG)
        log.debug("Verbose logging enabled")
    elif args.quiet:
        log.logger.setLevel(logging.ERROR)
    else:
        log.logger.setLevel(logging.WARNING)


def merge_config_with_args(args, config: dict):
    """Merge configuration file settings with command-line arguments."""
    # Command-line arguments take precedence over config file
    for key, value in config.items():
        if hasattr(args, key) and getattr(args, key) is None:
            setattr(args, key, value)
        elif hasattr(args, key.replace('-', '_')) and getattr(args, key.replace('-', '_')) is None:
            setattr(args, key.replace('-', '_'), value)


def print_startup_info(args) -> None:
    """Print startup information and configuration."""
    if not args.quiet:
        print("🔧 CMIP-LD JSON Validation Tool v2.0")
        print(f"📁 Target directory: {args.directory}")
        
        if args.context:
            print(f"📋 Context file: {args.context}")
        
        if args.dry_run:
            print("🔍 Mode: DRY RUN (no files will be modified)")
        
        if args.add_coauthors:
            print("👥 Co-authors: Enabled")
        
        if args.auto_commit:
            print("📦 Auto-commit: Enabled")
        
        if args.workers != 4:
            print(f"⚡ Workers: {args.workers}")
        
        print()


def run_validation(args) -> bool:
    """
    Run the validation process with the given arguments.
    
    Args:
        args: Parsed command-line arguments
        
    Returns:
        True if validation succeeded, False otherwise
    """
    start_time = time.time()
    
    try:
        # Create validator with all options
        validator = JSONValidator(
            directory=args.directory,
            context_file=args.context,
            max_workers=args.workers,
            dry_run=args.dry_run,
            add_coauthors=args.add_coauthors,
            use_last_author=args.use_last_author,
            auto_commit=args.auto_commit,
            custom_required_keys=args.required_keys
        )
        
        # Run validation
        success = validator.run()
        
        # Calculate processing time
        processing_time = time.time() - start_time
        
        # Generate additional reporting if requested
        if args.report:
            generate_report(validator, args, processing_time)
        
        # Print verbose stats if requested
        if args.verbose and not args.quiet:
            validator.reporter.print_verbose_stats(validator.stats, processing_time)
        
        return success
        
    except KeyboardInterrupt:
        print("\n⚠️ Operation cancelled by user")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return False


def generate_report(validator: JSONValidator, args, processing_time: float) -> None:
    """
    Generate and save a detailed JSON report.
    
    Args:
        validator: The JSONValidator instance
        args: Command-line arguments
        processing_time: Total processing time
    """
    try:
        # Collect additional information
        context_info = None
        if validator.context_manager:
            context_info = validator.context_manager.get_context_info()
        
        git_info = None
        if validator.git_manager:
            git_info = validator.git_manager.get_repository_info()
            if hasattr(validator.git_manager, '_last_commit_results'):
                git_info['commits'] = validator.git_manager._last_commit_results
        
        # Generate report
        report = validator.reporter.generate_json_report(
            results=[],  # We don't store all results, just summary
            stats=validator.stats,
            context_info=context_info,
            git_info=git_info
        )
        
        # Add processing metadata
        report['processing'] = {
            'processing_time_seconds': processing_time,
            'workers_used': args.workers,
            'dry_run': args.dry_run,
            'context_aware': bool(args.context)
        }
        
        # Save report
        report_path = Path(args.report)
        if validator.reporter.save_report_to_file(report, report_path):
            if not args.quiet:
                print(f"\n📄 Report saved to: {report_path}")
        
    except Exception as e:
        log.error(f"Failed to generate report: {e}")


def main() -> int:
    """
    Main entry point for the CLI application.
    
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    parser = create_argument_parser()
    args = parser.parse_args()
    
    # Load configuration if specified
    config = {}
    if args.config:
        config = load_configuration(args.config)
        merge_config_with_args(args, config)
    
    # Validate arguments
    if not validate_arguments(args):
        return 1
    
    # Configure logging
    configure_logging(args)
    
    # Print startup information
    print_startup_info(args)
    
    # Implicit co-author enabling
    if args.auto_commit and not args.add_coauthors:
        if not args.quiet:
            print("ℹ️  Note: --auto-commit implies --add-coauthors")
        args.add_coauthors = True
    
    # Run validation
    success = run_validation(args)
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
