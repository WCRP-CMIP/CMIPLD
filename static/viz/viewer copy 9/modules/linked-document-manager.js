// Linked Document Manager - handles fetching and managing linked documents
export class LinkedDocumentManager {
  constructor(documentLoader, jsonldProcessor, referenceManager) {
    this.documentLoader = documentLoader;
    this.jsonldProcessor = jsonldProcessor;
    this.referenceManager = referenceManager;
  }

  // Load all linked documents recursively
  async loadLinkedDocuments(expandedData, context, baseUrl, depth, documents) {
    if (depth <= 0) return;
    
    const linkedUrls = new Set();
    
    // Find @id references in the expanded data
    this.findLinkedUrls(expandedData, linkedUrls);
    
    // Also check context for @type: @id properties and their values
    if (context) {
      await this.findLinkedUrlsFromContext(context, baseUrl, linkedUrls);
    }
    
    console.log(`🔗 Found ${linkedUrls.size} linked URLs to fetch:`, Array.from(linkedUrls));
    
    // Fetch each linked document with individual error handling
    const failedUrls = [];
    for (const url of linkedUrls) {
      if (documents.has(url)) continue; // Already loaded
      
      try {
        console.log(`📥 Fetching linked document: ${url}`);
        const rawLinkedDoc = await this.documentLoader.fetchDocument(url);
        
        // Resolve context for the linked document with property-specific contexts
        let resolvedLinkedContext = {};
        if (rawLinkedDoc['@context']) {
          try {
            resolvedLinkedContext = await this.documentLoader.buildResolvedContext(rawLinkedDoc, url);
            console.log(`✅ Resolved context for ${url} with`, Object.keys(resolvedLinkedContext).length, 'terms');
            
            // Log property-specific contexts if any
            const propSpecificContexts = Object.keys(resolvedLinkedContext).filter(key => 
              resolvedLinkedContext[key] && 
              typeof resolvedLinkedContext[key] === 'object' && 
              resolvedLinkedContext[key]['@resolvedContext']
            );
            if (propSpecificContexts.length > 0) {
              console.log(`✅ Found property-specific contexts in ${url} for:`, propSpecificContexts.join(', '));
            }
          } catch (contextError) {
            console.warn(`⚠️ Context resolution failed for ${url}:`, contextError.message);
          }
        }
        
        // Update processor context and expand the linked document
        const originalContext = this.jsonldProcessor.resolvedContext;
        this.jsonldProcessor.resolvedContext = resolvedLinkedContext;
        
        let expandedLinkedDoc;
        try {
          expandedLinkedDoc = await this.jsonldProcessor.safeExpand(rawLinkedDoc);
        } catch (expandError) {
          console.warn(`⚠️ JSON-LD expansion failed for ${url}, using manual expansion:`, expandError.message);
          expandedLinkedDoc = this.jsonldProcessor.createManualExpansion(rawLinkedDoc, url);
        }
        
        // Restore original context
        this.jsonldProcessor.resolvedContext = originalContext;
        
        console.log(`✅ Expanded linked document: ${url}`);
        
        // Store the linked document with resolved context
        documents.set(url, {
          raw: rawLinkedDoc,
          expanded: expandedLinkedDoc,
          compacted: null, // Will be computed on demand
          context: rawLinkedDoc['@context'] || null,
          resolvedContext: resolvedLinkedContext, // Store resolved context
          isMain: false
        });
        
        // Recursively load more linked documents
        if (depth > 1) {
          try {
            await this.loadLinkedDocuments(expandedLinkedDoc, rawLinkedDoc['@context'], url, depth - 1, documents);
          } catch (recursiveError) {
            console.warn(`⚠️ Failed to load nested documents from ${url}:`, recursiveError.message);
          }
        }
      } catch (error) {
        console.warn(`⚠️ Could not fetch linked document ${url}:`, error.message);
        failedUrls.push(url);
      }
    }
    
    if (failedUrls.length > 0) {
      console.warn(`⚠️ Failed to load ${failedUrls.length} linked documents:`, failedUrls);
    }
  }

  // Find linked URLs in expanded data - enhanced to handle resolved URLs
  findLinkedUrls(data, urls, visited = new Set()) {
    if (!data || visited.has(data)) return;
    
    if (typeof data === 'object') {
      visited.add(data);
      
      if (Array.isArray(data)) {
        data.forEach(item => this.findLinkedUrls(item, urls, visited));
      } else {
        // Check for @id references and resolve them if needed
        Object.entries(data).forEach(([key, value]) => {
          if (typeof value === 'object' && value !== null && !Array.isArray(value) &&
              Object.keys(value).length === 1 && value['@id'] && 
              typeof value['@id'] === 'string') {
            // Resolve the @id using reference manager to get the full URL
            const resolvedUrl = this.referenceManager.expandReference(value['@id'], '@id');
            if (resolvedUrl && resolvedUrl.startsWith('http')) {
              console.log(`🔍 Found @id reference: ${value['@id']} -> ${resolvedUrl}`);
              urls.add(resolvedUrl);
            }
          } else if (Array.isArray(value)) {
            value.forEach(item => {
              if (typeof item === 'object' && item !== null && !Array.isArray(item) &&
                  Object.keys(item).length === 1 && item['@id'] && 
                  typeof item['@id'] === 'string') {
                // Resolve the @id using reference manager
                const resolvedUrl = this.referenceManager.expandReference(item['@id'], '@id');
                if (resolvedUrl && resolvedUrl.startsWith('http')) {
                  console.log(`🔍 Found @id reference in array: ${item['@id']} -> ${resolvedUrl}`);
                  urls.add(resolvedUrl);
                }
              } else {
                this.findLinkedUrls(item, urls, visited);
              }
            });
          } else if (typeof value === 'string') {
            // Check if this property is marked as a link property and resolve the string value
            if (this.referenceManager.isLinkedProperty(key)) {
              const resolvedUrl = this.referenceManager.expandReference(value, key);
              if (resolvedUrl && resolvedUrl.startsWith('http') && resolvedUrl !== value) {
                console.log(`🔍 Found linked property reference: ${key}=${value} -> ${resolvedUrl}`);
                urls.add(resolvedUrl);
              }
            }
          } else {
            this.findLinkedUrls(value, urls, visited);
          }
        });
      }
      
      visited.delete(data);
    }
  }

  // Find linked URLs from context definitions
  async findLinkedUrlsFromContext(context, baseUrl, urls) {
    // Process context to find properties marked as @type: @id
    const processContext = async (ctx) => {
      if (typeof ctx === 'string' && ctx.startsWith('http')) {
        // Load external context
        try {
          const contextDoc = await this.documentLoader.fetchDocument(ctx);
          if (contextDoc && contextDoc['@context']) {
            await processContext(contextDoc['@context']);
          }
        } catch (e) {
          console.warn(`Could not load context: ${ctx}`, e.message);
        }
      } else if (Array.isArray(ctx)) {
        for (const item of ctx) {
          await processContext(item);
        }
      } else if (typeof ctx === 'object' && ctx !== null) {
        // Check for link properties
        for (const [key, value] of Object.entries(ctx)) {
          if (typeof value === 'object' && value !== null && value['@type'] === '@id') {
            // This is a link property - mark it
            this.referenceManager.markAsLinkProperty(key);
          }
        }
      }
    };
    
    try {
      await processContext(context);
    } catch (error) {
      console.warn('⚠️ Error processing context for linked URLs:', error.message);
    }
  }

  // Create substitution map from documents - use resolved URLs as keys
  createSubstitutionMap(documents, mainDocumentUrl) {
    const substitutionMap = new Map();
    
    for (const [url, doc] of documents) {
      if (url === mainDocumentUrl) continue; // Skip main doc
      
      // Find the main entity in the expanded document
      if (doc.expanded && doc.expanded.length > 0) {
        const entity = doc.expanded.find(item => item['@id'] === url) || doc.expanded[0];
        if (entity) {
          // Store both the entity and its source document context for proper resolution
          // Use the URL as the key (it's already resolved when stored in documents)
          substitutionMap.set(url, {
            entity: entity,
            sourceContext: doc.resolvedContext || {},
            sourceUrl: url
          });
          
          // Also create entries for any @id variations that might resolve to this URL
          // This handles cases where the same resource might be referenced differently
          if (entity['@id'] && entity['@id'] !== url) {
            const entityId = entity['@id'];
            // Try to find if any unresolved references would resolve to this URL
            // This is a reverse lookup to handle different ways of referencing the same resource
            substitutionMap.set(entityId, {
              entity: entity,
              sourceContext: doc.resolvedContext || {},
              sourceUrl: url
            });
            console.log(`📦 Added substitution mapping: ${entityId} -> ${url}`);
          }
        }
      }
    }
    
    console.log('📦 Built substitution map with', substitutionMap.size, 'entities');
    return substitutionMap;
  }

  // Substitute links with context-aware resolution and depth control
  substituteLinksWithContext(data, substitutionMap, currentDepth = 0, maxDepth = 10, visited = new Set()) {
    if (!data || visited.has(data) || currentDepth >= maxDepth) {
      if (currentDepth >= maxDepth) {
        console.log(`🛑 Maximum substitution depth (${maxDepth}) reached, stopping recursion`);
      }
      return data;
    }
    
    if (typeof data === 'object') {
      visited.add(data);
      
      if (Array.isArray(data)) {
        const result = data.map(item => this.substituteLinksWithContext(item, substitutionMap, currentDepth, maxDepth, visited));
        visited.delete(data);
        return result;
      } else {
        const result = {};
        
        Object.entries(data).forEach(([key, value]) => {
          // Check if this is a link reference that we can substitute
          if (typeof value === 'object' && value !== null && !Array.isArray(value) &&
              Object.keys(value).length === 1 && value['@id'] && 
              typeof value['@id'] === 'string') {
            
            // Resolve the @id to get the full URL for lookup
            const resolvedUrl = this.referenceManager.expandReference(value['@id'], '@id');
            
            if (substitutionMap.has(resolvedUrl)) {
              const substitutionInfo = substitutionMap.get(resolvedUrl);
              console.log(`🔄 Substituting ${key}: ${value['@id']} -> ${resolvedUrl} (depth: ${currentDepth})`);
              
              // Recursively substitute with increased depth
              result[key] = this.substituteLinksWithContext(
                substitutionInfo.entity, 
                substitutionMap, 
                currentDepth + 1, 
                maxDepth, 
                new Set()
              );
            } else {
              // Keep the original reference if no substitution available
              result[key] = value;
            }
          } else if (Array.isArray(value)) {
            // Process array items
            result[key] = value.map(item => {
              if (typeof item === 'object' && item !== null && !Array.isArray(item) &&
                  Object.keys(item).length === 1 && item['@id'] && 
                  typeof item['@id'] === 'string') {
                
                const resolvedUrl = this.referenceManager.expandReference(item['@id'], '@id');
                
                if (substitutionMap.has(resolvedUrl)) {
                  const substitutionInfo = substitutionMap.get(resolvedUrl);
                  console.log(`🔄 Substituting ${key}[]: ${item['@id']} -> ${resolvedUrl} (depth: ${currentDepth})`);
                  
                  return this.substituteLinksWithContext(
                    substitutionInfo.entity, 
                    substitutionMap, 
                    currentDepth + 1, 
                    maxDepth, 
                    new Set()
                  );
                } else {
                  return item;
                }
              }
              return this.substituteLinksWithContext(item, substitutionMap, currentDepth, maxDepth, visited);
            });
          } else {
            // Recursively process other values
            result[key] = this.substituteLinksWithContext(value, substitutionMap, currentDepth, maxDepth, visited);
          }
        });
        
        visited.delete(data);
        return result;
      }
    }
    
    return data;
  }
}
