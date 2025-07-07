// JSON-LD Validator - validates and fixes common JSON-LD issues
export class JSONLDValidator {
  constructor() {
    this.validationErrors = [];
    this.fixedErrors = [];
  }

  // Validate and optionally fix a JSON-LD document
  validateAndFix(document, options = { fix: true, logErrors: true }) {
    this.validationErrors = [];
    this.fixedErrors = [];
    
    console.log('🔍 === STARTING JSON-LD VALIDATION ===');
    
    const result = this.processDocument(document, [], options);
    
    if (this.validationErrors.length > 0 && options.logErrors) {
      console.warn(`⚠️ Found ${this.validationErrors.length} JSON-LD validation errors:`);
      this.validationErrors.forEach((error, index) => {
        console.warn(`  ${index + 1}. ${error.message} at path: ${error.path}`);
      });
    }
    
    if (this.fixedErrors.length > 0 && options.logErrors) {
      console.log(`🔧 Fixed ${this.fixedErrors.length} JSON-LD errors:`);
      this.fixedErrors.forEach((fix, index) => {
        console.log(`  ${index + 1}. ${fix.message} at path: ${fix.path}`);
      });
    }
    
    return {
      document: result,
      errors: this.validationErrors,
      fixes: this.fixedErrors,
      isValid: this.validationErrors.length === 0
    };
  }

  // Process document recursively
  processDocument(obj, path = [], options = {}) {
    if (obj === null || typeof obj !== 'object') {
      return obj;
    }

    if (Array.isArray(obj)) {
      return obj.map((item, index) => 
        this.processDocument(item, [...path, `[${index}]`], options)
      );
    }

    const result = {};
    
    for (const [key, value] of Object.entries(obj)) {
      const currentPath = [...path, key];
      const pathString = currentPath.join('.');
      
      // Validate @id fields
      if (key === '@id') {
        const validationResult = this.validate_at_id(value, pathString, options);
        result[key] = validationResult;
      }
      // Validate @type fields
      else if (key === '@type') {
        const validationResult = this.validate_at_type(value, pathString, options);
        result[key] = validationResult;
      }
      // Validate @context fields
      else if (key === '@context') {
        const validationResult = this.validate_at_context(value, pathString, options);
        result[key] = validationResult;
      }
      // Process other values recursively
      else {
        result[key] = this.processDocument(value, currentPath, options);
      }
    }
    
    return result;
  }

  // Validate @id field
  validate_at_id(value, path, options) {
    if (typeof value === 'string') {
      // Valid @id
      return value;
    }
    
    if (typeof value === 'object' && value !== null) {
      this.validationErrors.push({
        type: 'invalid_at_id',
        message: '@id must be a string IRI, found object',
        path: path,
        value: value
      });
      
      if (options.fix) {
        // Try to extract a valid IRI from the object
        const fixedValue = this.extractIriFromObject(value, path);
        if (fixedValue) {
          this.fixedErrors.push({
            type: 'fixed_at_id',
            message: `Extracted IRI from object: "${fixedValue}"`,
            path: path,
            originalValue: value,
            fixedValue: fixedValue
          });
          return fixedValue;
        } else {
          // If we can't extract a valid IRI, convert to a string representation
          const fallbackValue = this.createFallbackIri(value, path);
          this.fixedErrors.push({
            type: 'fallback_at_id',
            message: `Created fallback IRI: "${fallbackValue}"`,
            path: path,
            originalValue: value,
            fixedValue: fallbackValue
          });
          return fallbackValue;
        }
      }
    }
    
    if (value === null || value === undefined) {
      this.validationErrors.push({
        type: 'null_at_id',
        message: '@id cannot be null or undefined',
        path: path,
        value: value
      });
      
      if (options.fix) {
        const fallbackValue = `urn:invalid:${path.replace(/\./g, '-')}`;
        this.fixedErrors.push({
          type: 'fixed_null_at_id',
          message: `Replaced null @id with fallback: "${fallbackValue}"`,
          path: path,
          fixedValue: fallbackValue
        });
        return fallbackValue;
      }
    }
    
    return value;
  }

  // Validate @type field
  validate_at_type(value, path, options) {
    if (typeof value === 'string') {
      return value;
    }
    
    if (Array.isArray(value)) {
      // @type can be an array
      return value.map((item, index) => {
        if (typeof item !== 'string') {
          this.validationErrors.push({
            type: 'invalid_at_type_item',
            message: '@type array items must be strings',
            path: `${path}[${index}]`,
            value: item
          });
          
          if (options.fix) {
            const fixedValue = String(item);
            this.fixedErrors.push({
              type: 'fixed_at_type_item',
              message: `Converted @type item to string: "${fixedValue}"`,
              path: `${path}[${index}]`,
              fixedValue: fixedValue
            });
            return fixedValue;
          }
        }
        return item;
      });
    }
    
    this.validationErrors.push({
      type: 'invalid_at_type',
      message: '@type must be a string or array of strings',
      path: path,
      value: value
    });
    
    if (options.fix) {
      const fixedValue = String(value);
      this.fixedErrors.push({
        type: 'fixed_at_type',
        message: `Converted @type to string: "${fixedValue}"`,
        path: path,
        fixedValue: fixedValue
      });
      return fixedValue;
    }
    
    return value;
  }

  // Validate @context field
  validate_at_context(value, path, options) {
    // @context can be string, object, or array
    if (typeof value === 'string' || 
        typeof value === 'object' || 
        Array.isArray(value)) {
      return value;
    }
    
    this.validationErrors.push({
      type: 'invalid_at_context',
      message: '@context must be a string, object, or array',
      path: path,
      value: value
    });
    
    // @context is complex, don't try to fix automatically
    return value;
  }

  // Try to extract a valid IRI from an object that's incorrectly used as @id
  extractIriFromObject(obj, path) {
    // Common patterns to look for IRI-like values
    const candidateKeys = ['id', 'url', 'uri', 'href', '@id', 'identifier'];
    
    for (const key of candidateKeys) {
      if (obj[key] && typeof obj[key] === 'string') {
        console.log(`🔧 Extracting IRI from object.${key}: "${obj[key]}" at ${path}`);
        return obj[key];
      }
    }
    
    // Look for any string value that looks like a URL
    for (const [key, value] of Object.entries(obj)) {
      if (typeof value === 'string' && this.looksLikeIri(value)) {
        console.log(`🔧 Found IRI-like value in object.${key}: "${value}" at ${path}`);
        return value;
      }
    }
    
    return null;
  }

  // Create a fallback IRI when we can't extract a valid one
  createFallbackIri(obj, path) {
    // Try to create a meaningful identifier from the object
    let identifier = '';
    
    // Look for common identifier fields
    const idFields = ['id', 'name', 'title', 'label', 'key'];
    for (const field of idFields) {
      if (obj[field] && typeof obj[field] === 'string') {
        identifier = obj[field];
        break;
      }
    }
    
    // If no identifier found, use a hash of the object keys
    if (!identifier) {
      identifier = Object.keys(obj).sort().join('-');
    }
    
    // Clean the identifier for use in IRI
    identifier = identifier.toLowerCase()
                          .replace(/[^a-z0-9-]/g, '-')
                          .replace(/-+/g, '-')
                          .replace(/^-|-$/g, '');
    
    const fallbackIri = `urn:invalid-id:${identifier}:${Date.now()}`;
    console.log(`🔧 Created fallback IRI: "${fallbackIri}" for object at ${path}`);
    
    return fallbackIri;
  }

  // Check if a string looks like an IRI
  looksLikeIri(str) {
    if (typeof str !== 'string') return false;
    
    // URL pattern
    if (str.startsWith('http://') || str.startsWith('https://')) {
      return true;
    }
    
    // URN pattern
    if (str.startsWith('urn:')) {
      return true;
    }
    
    // Prefixed name pattern (prefix:localname)
    if (/^[a-zA-Z][a-zA-Z0-9]*:[^:\s]+$/.test(str)) {
      return true;
    }
    
    return false;
  }

  // Get validation summary
  getValidationSummary() {
    return {
      totalErrors: this.validationErrors.length,
      totalFixes: this.fixedErrors.length,
      errorTypes: this.getErrorTypeCounts(),
      fixTypes: this.getFixTypeCounts()
    };
  }

  // Get error type counts
  getErrorTypeCounts() {
    const counts = {};
    this.validationErrors.forEach(error => {
      counts[error.type] = (counts[error.type] || 0) + 1;
    });
    return counts;
  }

  // Get fix type counts
  getFixTypeCounts() {
    const counts = {};
    this.fixedErrors.forEach(fix => {
      counts[fix.type] = (counts[fix.type] || 0) + 1;
    });
    return counts;
  }
}