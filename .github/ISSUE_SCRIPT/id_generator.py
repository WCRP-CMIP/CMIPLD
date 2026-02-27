"""
Generate @id from issue submitter and creation timestamp
"""

from datetime import datetime
import hashlib


def timestamp_to_epoch(timestamp_str):
    """
    Convert ISO 8601 timestamp to seconds since epoch.
    
    Args:
        timestamp_str: ISO 8601 format string (e.g., '2025-02-26T15:30:45Z')
    
    Returns:
        Integer seconds since epoch or None
    """
    if not timestamp_str:
        return None
    
    try:
        # Parse ISO 8601 format
        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        return int(dt.timestamp())
    except (ValueError, AttributeError):
        return None


def generate_id_from_issue(author, created_at):
    """
    Generate a unique @id from issue submitter and timestamp.
    
    Args:
        author: GitHub username (string)
        created_at: ISO 8601 timestamp string (e.g., '2025-02-26T15:30:45Z')
    
    Returns:
        Dictionary with:
        - 'author': the submitter username
        - 'epoch': seconds since epoch
        - 'id': generated ID (author-epoch)
    """
    
    if not author:
        author = 'unknown'
    
    epoch = timestamp_to_epoch(created_at)
    
    return {
        'author': author,
        'epoch': epoch,
        'id': f'{author}-{epoch}' if epoch else author
    }
