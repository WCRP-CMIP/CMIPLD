"""
ID generation utilities for creating @id from issue metadata.

Provides functions for generating unique identifiers from GitHub issue
submitter and creation timestamp, useful for creating entities without
explicit identifiers provided by the user.
"""

from datetime import datetime
import hashlib


def timestamp_to_epoch(timestamp_str):
    """
    Convert ISO 8601 timestamp to seconds since epoch (Unix time).
    
    Args:
        timestamp_str: ISO 8601 format string (e.g., '2025-02-26T15:30:45Z')
    
    Returns:
        int: Seconds since epoch, or None if parsing fails
        
    Examples:
        >>> timestamp_to_epoch('2025-02-26T15:30:45Z')
        1740511845
        >>> timestamp_to_epoch('2025-02-26T15:30:45+00:00')
        1740511845
    """
    if not timestamp_str:
        return None
    
    try:
        # Parse ISO 8601 format (handle both Z and +00:00 timezone formats)
        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        return int(dt.timestamp())
    except (ValueError, AttributeError):
        return None


def generate_id_from_issue(author, created_at):
    """
    Generate a unique @id from issue submitter and creation timestamp.
    
    Creates IDs in format: {author}-{epoch_seconds}
    
    Useful when issues don't provide explicit validation_key/label/acronym.
    The combination of author + timestamp guarantees uniqueness.
    
    Args:
        author (str): GitHub username of issue submitter
        created_at (str): ISO 8601 timestamp of issue creation (e.g., '2025-02-26T15:30:45Z')
    
    Returns:
        dict: Contains:
            - 'author' (str): The submitter username
            - 'epoch' (int): Seconds since epoch, or None if timestamp unparseable
            - 'id' (str): Generated ID (author-epoch or author-hash fallback)
            
    Examples:
        >>> result = generate_id_from_issue('daniel-ellis', '2025-02-26T15:30:45Z')
        >>> result['id']
        'daniel-ellis-1740511845'
        >>> result['epoch']
        1740511845
        
        >>> result = generate_id_from_issue('alice', '2025-02-26T15:30:45Z')
        >>> result['id']
        'alice-1740511845'
    """
    
    if not author:
        author = 'unknown'
    
    epoch = timestamp_to_epoch(created_at)
    
    if epoch:
        return {
            'author': author,
            'epoch': epoch,
            'id': f'{author}-{epoch}'
        }
    else:
        # Fallback to hash if timestamp can't be parsed
        # Use first 8 chars of MD5 hash of author+timestamp
        hash_input = f"{author}{created_at}".encode()
        hash_str = hashlib.md5(hash_input).hexdigest()[:8]
        return {
            'author': author,
            'epoch': None,
            'id': f'{author}-{hash_str}'
        }


def clean_id(id_str):
    """
    Clean an ID string to be URL-safe and filesystem-safe.
    
    Converts to lowercase and replaces spaces/underscores with hyphens.
    
    Args:
        id_str (str): ID to clean
    
    Returns:
        str: Cleaned ID
        
    Examples:
        >>> clean_id('My ID')
        'my-id'
        >>> clean_id('test_value')
        'test-value'
    """
    if not id_str:
        return ''
    return id_str.lower().strip().replace(' ', '-').replace('_', '-')


def parse_commiters(author, additional_commiters_str):
    """
    Parse GitHub usernames from author and additional_commiters string.
    
    Returns list of all commiters: [author, ...additional_commiters]
    
    Handles comma-separated lists and filters empty/whitespace entries.
    
    Args:
        author (str): Primary GitHub username (issue author)
        additional_commiters_str (str): Comma-separated GitHub usernames, or empty string
    
    Returns:
        list: [author, committer1, committer2, ...] or [author] if no additional
        
    Examples:
        >>> parse_commiters('alice', 'bob, charlie')
        ['alice', 'bob', 'charlie']
        
        >>> parse_commiters('alice', '')
        ['alice']
        
        >>> parse_commiters('alice', '  bob  ,  charlie  ')
        ['alice', 'bob', 'charlie']
    """
    commiters = [author] if author else []
    
    if additional_commiters_str:
        # Parse comma-separated list, strip whitespace
        additional = [c.strip() for c in additional_commiters_str.split(',')]
        # Filter out empty strings
        additional = [c for c in additional if c]
        commiters.extend(additional)
    
    return commiters
