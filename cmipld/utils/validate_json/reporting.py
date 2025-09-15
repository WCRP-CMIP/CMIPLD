#!/usr/bin/env python3
"""
Validation Reporting Module

This module handles all reporting functionality for the JSON-LD validation process,
including console output, statistics, and detailed error reporting.
"""

from typing import Dict, Any, List
from pathlib import Path

from ..logging.unique import UniqueLogger, logging

log = UniqueLogger()


class ValidationReporter:
    """
    Handles reporting and output formatting for validation results.
    
    Provides comprehensive reporting including statistics, error details,
    and formatted output for different audiences.
    """
    
    def __init__(self):
        """Initialize the validation reporter."""
        self.console_width = 60

    def report_results(self, results: List[Dict[str, Any]], stats: Dict[str, int],
                      dry_run: bool = False, context_info: Dict[str, Any] = None,
                      git_info: Dict[str, Any] = None) -> None:
        """
        Generate comprehensive validation report.
        
        Args:
            results: List of validation results for files that were modified or had errors
            stats: Statistics dictionary with counts
            dry_run: Whether this was a dry run
            context_info: Optional context manager information
            git_info: Optional git integration information
        """
        self._print_header("PROCESSING SUMMARY")
        self._print_basic_stats(stats, dry_run)
        
        if context_info:
            self._print_context_info(context_info)
        
        if git_info:
            self._print_git_info(git_info)
        
        # Report errors
        errors = [r for r in results if not r['success']]
        if errors:
            self._print_errors(errors)
        
        # Report modifications
        modifications = [r for r in results if r['modified']]
        if modifications:
            self._print_modifications(modifications, dry_run)
        
        # Summary messages
        self._print_summary_messages(stats, dry_run, len(modifications), git_info)
        
        self._print_footer()

    def _print_header(self, title: str) -> None:
        """Print a formatted section header."""
        print("\n" + "=" * self.console_width)
        print(f"📊 {title}")
        print("=" * self.console_width)

    def _print_footer(self) -> None:
        """Print the report footer."""
        print("=" * self.console_width)

    def _print_basic_stats(self, stats: Dict[str, int], dry_run: bool) -> None:
        """Print basic processing statistics."""
        print(f"Total files processed: {stats['processed']}")
        print(f"Files modified: {stats['modified']}")
        print(f"Files already valid: {stats['processed'] - stats['modified'] - stats['errors']}")
        print(f"Errors encountered: {stats['errors']}")
        
        if dry_run and stats['modified'] > 0:
            print(f"\n💡 DRY RUN: {stats['modified']} files would be modified in actual run")

    def _print_context_info(self, context_info: Dict[str, Any]) -> None:
        """Print context manager information."""
        if context_info.get("status") == "Context loaded":
            print(f"\n📋 CONTEXT INFORMATION:")
            print(f"   Context file: {context_info.get('context_file', 'Unknown')}")
            print(f"   Total terms: {context_info.get('total_terms', 0)}")
            print(f"   Required terms: {context_info.get('required_terms', 0)}")
            print(f"   Priority terms: {context_info.get('priority_terms', 0)}")
            print(f"   Linked fields: {context_info.get('linked_fields_count', 0)}")
            
            type_dist = context_info.get('type_distribution', {})
            if type_dist:
                print(f"   Type distribution: {dict(sorted(type_dist.items()))}")
                
            # Show linked fields if any
            linked_fields = context_info.get('linked_fields', [])
            if linked_fields:
                print(f"   🔗 Link normalization for: {', '.join(linked_fields[:5])}")
                if len(linked_fields) > 5:
                    print(f"       ... and {len(linked_fields) - 5} more")

    def _print_git_info(self, git_info: Dict[str, Any]) -> None:
        """Print git integration information."""
        if git_info.get("status") == "Git repository":
            print(f"\n🔧 GIT INFORMATION:")
            print(f"   Current branch: {git_info.get('current_branch', 'Unknown')}")
            print(f"   Has uncommitted changes: {git_info.get('has_uncommitted_changes', False)}")
            
            if git_info.get('coauthors_enabled'):
                print(f"   Co-authors enabled: ✅")
            if git_info.get('auto_commit_enabled'):
                print(f"   Auto-commit enabled: ✅")
            if git_info.get('use_last_author'):
                print(f"   Using last author: ✅")
            
            # Show commit summary if available
            commits_info = git_info.get('commits')
            if commits_info and not commits_info.get('skipped'):
                print(f"\n   📦 COMMIT SUMMARY:")
                print(f"   Successful commits: {commits_info.get('commits_created', 0)}")
                if commits_info.get('commits_failed', 0) > 0:
                    print(f"   Failed commits: {commits_info.get('commits_failed', 0)}")

    def _print_errors(self, errors: List[Dict[str, Any]]) -> None:
        """Print error information."""
        print(f"\n❌ ERRORS ({len(errors)} files):")
        
        # Show up to 10 errors
        for error in errors[:10]:
            print(f"   {error['file']}: {error['message']}")
        
        if len(errors) > 10:
            print(f"   ... and {len(errors) - 10} more errors")
        
        # Error type summary
        error_types = {}
        for error in errors:
            error_type = self._categorize_error(error['message'])
            error_types[error_type] = error_types.get(error_type, 0) + 1
        
        if len(error_types) > 1:
            print(f"\n   Error breakdown:")
            for error_type, count in sorted(error_types.items()):
                print(f"     {error_type}: {count} files")

    def _print_modifications(self, modifications: List[Dict[str, Any]], dry_run: bool) -> None:
        """Print modification information."""
        if len(modifications) <= 20:
            action = "WOULD BE MODIFIED" if dry_run else "MODIFIED FILES"
            print(f"\n✅ {action} ({len(modifications)}):")
            for mod in modifications:
                print(f"   {mod['file']}")
        else:
            action = "would be modified" if dry_run else "modified"
            print(f"\n✅ MODIFICATIONS: {len(modifications)} files {action} (too many to list)")

    def _print_summary_messages(self, stats: Dict[str, int], dry_run: bool,
                               modifications_count: int, git_info: Dict[str, Any] = None) -> None:
        """Print final summary messages."""
        # Co-author information
        if git_info and git_info.get('coauthors_enabled') and modifications_count > 0 and not dry_run:
            print(f"\n👥 CO-AUTHORS: Created individual commits for {modifications_count} files")
            print("   Each file was committed with its own historic authors")
        elif git_info and git_info.get('coauthors_enabled') and modifications_count > 0 and dry_run:
            print(f"\n👥 CO-AUTHORS: Would create individual commits for {modifications_count} files")
            print("   (Use --auto-commit to create commits with co-authors)")
        
        # Success/failure summary
        if stats['errors'] == 0:
            if modifications_count > 0:
                if dry_run:
                    print(f"\n🔍 Dry run completed successfully. {modifications_count} files need updates.")
                else:
                    print(f"\n✅ Validation completed successfully. {modifications_count} files were updated.")
            else:
                print(f"\n✅ All files are valid. No changes needed.")
        else:
            print(f"\n⚠️ Validation completed with {stats['errors']} errors. Please review and fix manually.")

    def _categorize_error(self, error_message: str) -> str:
        """Categorize error messages for summary reporting."""
        error_msg_lower = error_message.lower()
        
        if "invalid json" in error_msg_lower:
            return "JSON Syntax"
        elif "empty file" in error_msg_lower:
            return "Empty Files"
        elif "not an object" in error_msg_lower:
            return "Structure"
        elif "file already exists" in error_msg_lower:
            return "File Conflicts"
        elif "permission" in error_msg_lower or "access" in error_msg_lower:
            return "Permissions"
        elif "context" in error_msg_lower:
            return "Context Issues"
        else:
            return "Other"

    def generate_json_report(self, results: List[Dict[str, Any]], stats: Dict[str, int],
                           context_info: Dict[str, Any] = None,
                           git_info: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Generate a structured JSON report.
        
        Args:
            results: Validation results
            stats: Processing statistics
            context_info: Context manager information
            git_info: Git integration information
            
        Returns:
            Dictionary suitable for JSON serialization
        """
        import datetime
        
        errors = [r for r in results if not r['success']]
        modifications = [r for r in results if r['modified']]
        
        report = {
            "timestamp": datetime.datetime.now().isoformat(),
            "summary": {
                "total_files": stats['processed'],
                "modified_files": stats['modified'],
                "valid_files": stats['processed'] - stats['modified'] - stats['errors'],
                "error_files": stats['errors'],
                "success_rate": (stats['processed'] - stats['errors']) / stats['processed'] if stats['processed'] > 0 else 1.0
            },
            "errors": [
                {
                    "file": error['file'],
                    "message": error['message'],
                    "category": self._categorize_error(error['message'])
                }
                for error in errors
            ],
            "modifications": [mod['file'] for mod in modifications],
            "error_categories": self._get_error_category_counts(errors)
        }
        
        if context_info:
            report["context"] = context_info
        
        if git_info:
            report["git"] = git_info
        
        return report

    def _get_error_category_counts(self, errors: List[Dict[str, Any]]) -> Dict[str, int]:
        """Get counts of errors by category."""
        category_counts = {}
        for error in errors:
            category = self._categorize_error(error['message'])
            category_counts[category] = category_counts.get(category, 0) + 1
        return category_counts

    def print_verbose_stats(self, stats: Dict[str, int], processing_time: float = None) -> None:
        """Print detailed statistics for verbose mode."""
        print(f"\n📈 DETAILED STATISTICS:")
        print(f"   Files processed: {stats['processed']}")
        print(f"   Files modified: {stats['modified']}")
        print(f"   Files with errors: {stats['errors']}")
        print(f"   Files skipped: {stats.get('skipped', 0)}")
        
        if processing_time:
            print(f"   Processing time: {processing_time:.2f} seconds")
            if stats['processed'] > 0:
                avg_time = processing_time / stats['processed']
                print(f"   Average time per file: {avg_time:.3f} seconds")
        
        if stats['processed'] > 0:
            success_rate = (stats['processed'] - stats['errors']) / stats['processed'] * 100
            print(f"   Success rate: {success_rate:.1f}%")

    def save_report_to_file(self, report: Dict[str, Any], output_file: Path) -> bool:
        """
        Save a JSON report to file.
        
        Args:
            report: Report dictionary
            output_file: Path to output file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            import json
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            log.info(f"Report saved to: {output_file}")
            return True
        except Exception as e:
            log.error(f"Failed to save report to {output_file}: {e}")
            return False
