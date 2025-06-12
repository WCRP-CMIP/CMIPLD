# CMIP-LD SSL/TLS Patch Summary

## Overview
This patch adds support for working with HTTPS without requiring OpenSSL to be installed, with automatic detection and fallback capabilities.

## Changes Made

### 1. **server.py** - Enhanced SSL Support

#### New Functions Added:
- `check_openssl_available()`: Checks if OpenSSL is available in system PATH
- `create_self_signed_cert_python()`: Creates SSL certificates using Python's cryptography library as fallback

#### LocalServer Class Changes:
- **New constructor parameter**: `use_ssl=None` 
  - `None`: Auto-detect SSL capability (default)
  - `True`: Force SSL (will fail if not possible)
  - `False`: Disable SSL completely
- **New methods**:
  - `_auto_detect_ssl()`: Automatically detects SSL availability
  - `_setup_ssl_certificates()`: Sets up SSL certificates using available methods
  - `_create_ssl_certificates_openssl()`: Creates certificates with OpenSSL (with error handling)
- **Modified `start_server()`**: 
  - Now supports both HTTP and HTTPS modes
  - Graceful fallback from HTTPS to HTTP if SSL setup fails
  - Different log colors for HTTP (cyan) vs HTTPS (magenta)

#### SSL Auto-Detection Logic:
1. Check if OpenSSL is available in PATH
2. If not, check if Python `cryptography` library is available
3. If neither available, disable SSL and use HTTP only
4. If SSL setup fails at runtime, fallback to HTTP

### 2. **offline.py** - Updated LD_server Class

#### Constructor Changes:
- **New parameter**: `use_ssl=None` - passed through to LocalServer
- Updated docstring to explain SSL options

#### Method Updates:
- `from_zip()`: Added missing `override` parameter for consistency
- `start_server()`: Now passes `use_ssl` parameter to LocalServer

### 3. **New Files Created**

#### offline_patched.py
- Complete rewrite with command-line interface
- **New command-line arguments**:
  - `--no-ssl`: Force disable SSL (HTTP only)
  - `--ssl`: Force enable SSL (will fail if not possible)
  - `--port`: Specify port (default 8081)
  - `--debug`: Enable debug logging
  - `--nojson`: Disable automatic .json suffix redirects
  - `--repos`: Comma-separated list of repositories
  - `--zipfile`: Path to tar.gz file
  - `--copy`: Comma-separated list of local paths to copy
  - `--override`: Override existing repos without prompting

#### server_patched.py
- Standalone version with all SSL enhancements
- Can be used independently of offline.py

#### __main__.py
- Makes the server_tools module runnable as `python -m cmipld.utils.server_tools`

## Usage Examples

### Programmatic Usage
```python
# Auto-detect SSL (default behavior)
server = LD_server(repos=my_repos)

# Force disable SSL (HTTP only)
server = LD_server(repos=my_repos, use_ssl=False)

# Force enable SSL (will fail if OpenSSL/cryptography not available)
server = LD_server(repos=my_repos, use_ssl=True)
```

### Command Line Usage
```bash
# Auto-detect SSL capability (default)
python -m cmipld.utils.server_tools.offline --repos repo1,repo2

# Force disable SSL (HTTP only)
python -m cmipld.utils.server_tools.offline --no-ssl --repos repo1,repo2

# Force enable SSL
python -m cmipld.utils.server_tools.offline --ssl --repos repo1,repo2

# Custom port with debug logging
python -m cmipld.utils.server_tools.offline --port 9000 --debug --repos repo1,repo2
```

## Error Handling

### SSL Certificate Creation Failures:
1. **OpenSSL not found**: Falls back to Python cryptography library
2. **Cryptography library not available**: Disables SSL, uses HTTP
3. **Runtime SSL failures**: Gracefully falls back to HTTP with warning

### User-Friendly Messages:
- Clear logging about SSL status and fallback decisions
- Different colors for HTTP vs HTTPS server URLs
- Warnings when SSL setup fails but continues with HTTP

## Dependencies

### Required:
- Python standard library (http.server, ssl, subprocess, etc.)
- rich (for colored logging)

### Optional:
- **OpenSSL**: System command-line tool (preferred for SSL)
- **cryptography library**: Python package (fallback for SSL)

### Fallback Chain:
1. OpenSSL command-line tool
2. Python cryptography library  
3. HTTP-only mode (no SSL)

## Backward Compatibility

All existing code will continue to work without changes:
- Default behavior is auto-detection (same as before if OpenSSL available)
- Original method signatures preserved with new optional parameters
- Legacy `create_ssl_certificates()` method maintained for compatibility

## Security Considerations

- Self-signed certificates are created for local development only
- Certificates include localhost and 127.0.0.1 as valid names
- Private keys are generated with appropriate key sizes (RSA 2048/4096)
- SSL context uses secure defaults when available

## Testing the Patch

### Test SSL Auto-Detection:
```python
from cmipld.utils.server_tools.offline import LD_server

# This will auto-detect SSL capability
server = LD_server()
url = server.start_server()
print(f"Server running at: {url}")  # Will show http:// or https://
```

### Test Command Line Interface:
```bash
# Test without OpenSSL
python -m cmipld.utils.server_tools.offline --no-ssl --debug

# Test with SSL forced (will show if it fails)
python -m cmipld.utils.server_tools.offline --ssl --debug
```

### Test Different Scenarios:
1. **System with OpenSSL**: Should use HTTPS with OpenSSL-generated certificates
2. **System without OpenSSL but with cryptography**: Should use HTTPS with Python-generated certificates  
3. **System without either**: Should fallback to HTTP with clear warning messages
4. **Explicit `--no-ssl` flag**: Should always use HTTP regardless of available tools

## Installation Instructions

### For cryptography library (optional, for SSL fallback):
```bash
pip install cryptography
```

### Using the patched version:
```python
# Use the patched server directly
from cmipld.utils.server_tools.server_patched import LocalServer

# Or use the enhanced offline server
from cmipld.utils.server_tools.offline_patched import LD_server
```

## Migration Guide

### For existing code using LocalServer:
```python
# Old way (still works)
server = LocalServer("/path/to/files")

# New way with SSL control
server = LocalServer("/path/to/files", use_ssl=False)  # Force HTTP
server = LocalServer("/path/to/files", use_ssl=True)   # Force HTTPS
server = LocalServer("/path/to/files")                 # Auto-detect (default)
```

### For existing code using LD_server:
```python
# Old way (still works)
server = LD_server(repos=my_repos)

# New way with SSL control
server = LD_server(repos=my_repos, use_ssl=False)  # Force HTTP
```

## Files Modified/Created Summary

### Modified Files:
- `server.py`: Added SSL auto-detection and fallback capabilities
- `offline.py`: Added `use_ssl` parameter support

### New Files:
- `server_patched.py`: Standalone enhanced version
- `offline_patched.py`: Enhanced version with CLI
- `__main__.py`: Module runner
- `PATCH_SUMMARY.md`: This documentation

## Key Benefits

1. **No more OpenSSL dependency failures**: Works without OpenSSL installed
2. **Automatic fallback**: Gracefully handles SSL setup failures
3. **User control**: Explicit flags to force HTTP or HTTPS modes
4. **Better error messages**: Clear indication of what's happening
5. **Backward compatibility**: Existing code continues to work unchanged
6. **Command-line interface**: Easy testing and deployment options
7. **JSON-LD SSL compatibility**: Fixes "JsonLdError" SSL issues with context loading
8. **Protocol auto-switching**: Automatically tries HTTP/HTTPS alternatives for localhost

## JSON-LD SSL Error Fix

The patch specifically addresses the following error:
```
JsonLdError: ('Dereferencing a URL did not result in a valid JSON-LD object. Possible causes are an inaccessible URL perhaps due to a same-origin policy (ensure the server uses CORS if you are using client-side JavaScript), too many redirects, a non-JSON response, or more than one HTTP Link Header was provided for a remote context.',) Type: jsonld.InvalidUrl Code: loading remote context failed Details: {'url': 'http://localhost:58820/cmip7/experiment/_context_', 'cause': SSLError(MaxRetryError("HTTPSConnectionPool(host='localhost', port=58820): Max retries exceeded with url: /cmip7/experiment/_context_ (Caused by SSLError(SSLError(1, '[SSL] record layer failure (_ssl.c:997)')))"))}
```

### Root Cause:
- JSON-LD processors trying to access `http://` URLs when server is running on `https://`
- Self-signed SSL certificates causing verification failures
- Protocol mismatch between expected and actual server configuration

### Solution:
1. **Global requests patching**: Automatically disables SSL verification for localhost
2. **Protocol auto-switching**: Tries HTTP if HTTPS fails, and vice versa
3. **Enhanced error handling**: Graceful fallback with informative messages
4. **JSON-LD processor compatibility**: Works with pyld and other JSON-LD libraries

### New Files for JSON-LD Support:
- `jsonld_ssl_debug.py`: Diagnostic and fixing utilities
- `monkeypatch_requests_patched.py`: Enhanced request handling
- `test_ssl_patches.py`: Test suite for SSL scenarios
