// Iterative linked item insertion (core algorithm)
import { Utils } from './utils.js';

export class LinkedItemResolver {
  constructor(referenceManager, jsonldProcessor, prefixMapping) {
    this.referenceManager = referenceManager;
    this.jsonldProcessor = jsonldProcessor;
    this.prefixMapping = prefixMapping;
  }

  // Store original linked field values before expansion
  storeOriginalLinkedFieldValues(data, storage, visited = new Set()) {
    if (typeof data !== 'object' || data === null || visited.has(data)) {
      return;
    }
    visited.add(data);

    if (Array.isArray(data)) {
      data.forEach(item => this.storeOriginalLinkedFieldValues(item, storage, visited));
      visited.delete(data);
      return;
    }

    // Store ID for this object if it has one
    const objId = data['@id'];
    if (objId) {
      // Check each property to see if it's a linked field
      for (const [key, value] of Object.entries(data)) {
        if (this.referenceManager.linkProperties && this.referenceManager.linkProperties.has(key)) {
          // This is a linked field - store its original value
          const storageKey = `${objId}:::${key}`;
          storage.set(storageKey, value);
        }
      }
    }

    // Recursively process nested objects
    for (const value of Object.values(data)) {
      this.storeOriginalLinkedFieldValues(value, storage, visited);
    }

    visited.delete(data);
  }

  // Process linked fields to substitute references with entities FROM EXPANDED DATA
  processLinkedFields(data, expandedEntityIndex, depth = 2, visited = new Set()) {
    if (typeof data !== 'object' || data === null || visited.has(data) || depth <= 0) {
      return data;
    }
    visited.add(data);

    if (Array.isArray(data)) {
      const result = data.map(item => this.processLinkedFields(item, expandedEntityIndex, depth, visited));
      visited.delete(data);
      return result;
    }

    const result = {};
    
    for (const [key, value] of Object.entries(data)) {
      // Check if this is an object with only @id (typical of expanded linked values)
      if (typeof value === 'object' && value !== null && !Array.isArray(value) && 
          Object.keys(value).length === 1 && value['@id']) {
        // This is a linked reference - try to resolve it from expanded data
        const entity = expandedEntityIndex.get(value['@id']);
        if (entity) {
          console.log(`🔗 Substituting linked reference '${key}': ${value['@id']} -> expanded entity`);
          result[key] = depth > 1 ? this.processLinkedFields(entity, expandedEntityIndex, depth - 1, new Set()) : entity;
        } else {
          result[key] = value;
        }
      } else if (Array.isArray(value)) {
        // Process each item in the array
        result[key] = value.map((item, index) => {
          if (typeof item === 'object' && item !== null && !Array.isArray(item) &&
              Object.keys(item).length === 1 && item['@id']) {
            // This is a linked reference in an array
            const entity = expandedEntityIndex.get(item['@id']);
            if (entity) {
              console.log(`🔗 Substituting linked reference '${key}[${index}]': ${item['@id']} -> expanded entity`);
              return depth > 1 ? this.processLinkedFields(entity, expandedEntityIndex, depth - 1, new Set()) : entity;
            }
            return item;
          } else if (typeof item === 'object' && item !== null && item['@id'] && Object.keys(item).length > 1) {
            // Object with @id and other properties - try to expand it
            const entity = expandedEntityIndex.get(item['@id']);
            if (entity && entity !== item) {
              console.log(`🔗 Expanding object with @id '${key}[${index}]': ${item['@id']} -> expanded entity`);
              const expanded = depth > 1 ? this.processLinkedFields(entity, expandedEntityIndex, depth - 1, new Set()) : entity;
              // Merge with original properties
              return { ...expanded, ...item };
            }
          }
          return this.processLinkedFields(item, expandedEntityIndex, depth, visited);
        });
      } else {
        // Process recursively
        result[key] = this.processLinkedFields(value, expandedEntityIndex, depth, visited);
      }
    }
    
    visited.delete(data);
    return result;
  }

  // Iteratively insert linked items by pulling @id fields FROM EXPANDED DATA
  iterativelyInsertLinkedItems(data, expandedEntityIndex, depth = 2, preserveLinkedFields = false) {
    console.log(`🔗 === STARTING ITERATIVE INSERTION FROM EXPANDED DATA (depth: ${depth}) ===`);
    
    if (depth <= 0 || !expandedEntityIndex) {
      return data;
    }
    
    let workingData = Utils.deepClone(data);
    
    // Process linked fields using the expanded entity index
    console.log(`🔗 Processing linked fields using expanded entity index with ${expandedEntityIndex.size} entities...`);
    workingData = this.processLinkedFields(workingData, expandedEntityIndex, depth);
    
    console.log(`🔗 === ITERATIVE INSERTION COMPLETE ===`);
    return workingData;
  }

  // Insert a linked item into the data structure
  insertLinkedItem(data, idRef, entity, depth, visited = new Set(), isRootObject = true, parentId = null) {
    if (typeof data !== 'object' || data === null || visited.has(data)) {
      return data;
    }
    visited.add(data);

    if (Array.isArray(data)) {
      const result = data.map(item => this.insertLinkedItem(item, idRef, entity, depth, visited, false, parentId));
      visited.delete(data);
      return result;
    }

    // Track the current object's ID
    const currentObjectId = data['@id'] || parentId;
    
    // Check if this is the root object and if it has the same ID we're trying to substitute
    if (isRootObject && currentObjectId === idRef) {
      // Process children but don't substitute the root object itself
      const result = {};
      for (const [key, value] of Object.entries(data)) {
        result[key] = this.insertLinkedItem(value, idRef, entity, depth, visited, false, currentObjectId);
      }
      visited.delete(data);
      return result;
    }

    const result = {};
    
    for (const [key, value] of Object.entries(data)) {
      if (key === '@id' && value === idRef && this.referenceManager.shouldExpandReference(data)) {
        // Expand @id reference
        const expandedEntity = depth > 1 ? this.iterativelyInsertLinkedItems(entity, depth - 1) : entity;
        
        // Preserve additional properties
        const originalProps = { ...data };
        delete originalProps['@id'];
        
        const merged = { ...expandedEntity, ...originalProps };
        visited.delete(data);
        return merged;
        
      } else if (typeof value === 'string' && value === idRef && this.referenceManager.isExpandableReference(value, key)) {
        // Check if this is a self-reference (non-nested key pointing to parent's ID)
        if (currentObjectId === idRef) {
          console.log(`🔗 Skipping self-reference expansion for key '${key}' pointing to same object: ${idRef}`);
          result[key] = value; // Keep the reference as-is
        } else {
          // Expand string reference
          console.log(`🔗 Expanding linked key '${key}' from reference: ${idRef}`);
          const expandedEntity = depth > 1 ? this.iterativelyInsertLinkedItems(entity, depth - 1) : entity;
          result[key] = expandedEntity;
        }
        
      } else if (typeof value === 'string' && this.referenceManager.isExpandableReference(value, key)) {
        // Handle cases where the string needs to be expanded first
        const expandedRef = this.referenceManager.expandReference(value, key);
        if (expandedRef === idRef) {
          // Check if this is a self-reference (non-nested key pointing to parent's ID)
          if (currentObjectId === idRef) {
            console.log(`🔗 Skipping self-reference expansion for key '${key}' pointing to same object: ${idRef}`);
            result[key] = value; // Keep the reference as-is
          } else {
            // Expand string reference
            console.log(`🔗 Expanding linked key '${key}' from reference: ${value} -> ${idRef}`);
            const expandedEntity = depth > 1 ? this.iterativelyInsertLinkedItems(entity, depth - 1) : entity;
            result[key] = expandedEntity;
          }
        } else {
          // Not this reference, keep processing
          result[key] = this.insertLinkedItem(value, idRef, entity, depth, visited, false, currentObjectId);
        }
        
      } else if (Array.isArray(value)) {
        // Process array items
        result[key] = value.map((item, index) => {
          if (typeof item === 'string' && item === idRef && this.referenceManager.isExpandableReference(item, key)) {
            // Check if this is a self-reference
            if (currentObjectId === idRef) {
              console.log(`🔗 Skipping self-reference expansion for key '${key}[${index}]' pointing to same object: ${idRef}`);
              return item; // Keep the reference as-is
            } else {
              console.log(`🔗 Expanding linked key '${key}[${index}]' from reference: ${idRef}`);
              const expandedEntity = depth > 1 ? this.iterativelyInsertLinkedItems(entity, depth - 1) : entity;
              return expandedEntity;
            }
          } else if (typeof item === 'string' && this.referenceManager.isExpandableReference(item, key)) {
            // Handle cases where the string needs to be expanded first
            const expandedRef = this.referenceManager.expandReference(item, key);
            if (expandedRef === idRef) {
              // Check if this is a self-reference
              if (currentObjectId === idRef) {
                console.log(`🔗 Skipping self-reference expansion for key '${key}[${index}]' pointing to same object: ${idRef}`);
                return item; // Keep the reference as-is
              } else {
                console.log(`🔗 Expanding linked key '${key}[${index}]' from reference: ${item} -> ${idRef}`);
                const expandedEntity = depth > 1 ? this.iterativelyInsertLinkedItems(entity, depth - 1) : entity;
                return expandedEntity;
              }
            }
          }
          return this.insertLinkedItem(item, idRef, entity, depth, visited, false, currentObjectId);
        });
        
      } else {
        // Recursively process
        result[key] = this.insertLinkedItem(value, idRef, entity, depth, visited, false, currentObjectId);
      }
    }
    
    visited.delete(data);
    return result;
  }

  // Expand objects that have @id properties by merging with fetched entity data
  expandObjectsWithIds(data, depth, visited = new Set(), currentContextId = null) {
    if (typeof data !== 'object' || data === null || visited.has(data)) {
      return data;
    }
    visited.add(data);

    if (Array.isArray(data)) {
      const result = data.map(item => this.expandObjectsWithIds(item, depth, visited, currentContextId));
      visited.delete(data);
      return result;
    }

    // Track the current object's ID if it's the top-level object being processed
    const thisObjectId = data['@id'] || null;
    const contextId = currentContextId || thisObjectId;

    // Check if this object has an @id and should be expanded
    if (data['@id'] && typeof data['@id'] === 'string') {
      const idRef = data['@id'];
      
      // IMPORTANT: Don't self-substitute - skip if this is the same ID as the context object
      if (contextId && idRef === contextId) {
        console.log(`🔗 Skipping self-substitution for: ${idRef}`);
        // Still recursively process properties, but don't substitute the object itself
        const result = {};
        for (const [key, value] of Object.entries(data)) {
          result[key] = this.expandObjectsWithIds(value, depth, visited, contextId);
        }
        visited.delete(data);
        return result;
      }
      
      const resolvedEntity = this.jsonldProcessor.getEntityFromIndex(idRef, this.prefixMapping);
      
      if (resolvedEntity && resolvedEntity !== data) {
        console.log(`🔗 Expanding object with @id: ${idRef}`);
        
        // Recursively expand the fetched entity if depth allows
        const expandedEntity = depth > 1 ? 
          this.iterativelyInsertLinkedItems(Utils.deepClone(resolvedEntity), depth - 1) : 
          resolvedEntity;
        
        // Merge: start with expanded entity, then overlay current object's properties
        const merged = { ...expandedEntity };
        
        // Preserve all properties from the current object
        for (const [key, value] of Object.entries(data)) {
          if (key === '@id') {
            // Keep the @id
            merged[key] = value;
          } else if (key in merged) {
            // Property exists in both - keep the local version
            console.log(`🔗 Preserving local property '${key}' over fetched value`);
            merged[key] = value;
          } else {
            // Property only in local object
            merged[key] = value;
          }
        }
        
        visited.delete(data);
        return merged;
      }
    }

    // Recursively process all properties
    const result = {};
    for (const [key, value] of Object.entries(data)) {
      result[key] = this.expandObjectsWithIds(value, depth, visited, contextId);
    }

    visited.delete(data);
    return result;
  }
}
