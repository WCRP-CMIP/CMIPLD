// State Manager - manages application state and data
export class StateManager {
  constructor() {
    this.initializeState();
  }

  // Initialize application state
  initializeState() {
    // Storage for all documents in their various forms
    this.documents = new Map(); // URL -> { raw, expanded, compacted, context, resolvedContext }
    this.mainDocumentUrl = null;
    this.mergedContext = {};
    this.isExpanded = false;
    this.currentViewData = null;
  }

  // Clear all state data
  clearData() {
    this.documents.clear();
    this.mainDocumentUrl = null;
    this.mergedContext = {};
    this.currentViewData = null;
  }

  // Store a document with all its forms
  storeDocument(url, documentData) {
    this.documents.set(url, documentData);
  }

  // Get a document by URL
  getDocument(url) {
    return this.documents.get(url);
  }

  // Get the main document
  getMainDocument() {
    return this.mainDocumentUrl ? this.documents.get(this.mainDocumentUrl) : null;
  }

  // Set the main document URL
  setMainDocumentUrl(url) {
    this.mainDocumentUrl = url;
  }

  // Set merged context
  setMergedContext(context) {
    this.mergedContext = context;
  }

  // Set current view data
  setCurrentViewData(data) {
    this.currentViewData = data;
  }

  // Get current view data
  getCurrentViewData() {
    return this.currentViewData;
  }

  // Set expanded state
  setExpanded(expanded) {
    this.isExpanded = expanded;
  }

  // Get expanded state
  getExpanded() {
    return this.isExpanded;
  }

  // Get all documents
  getAllDocuments() {
    return this.documents;
  }

  // Get merged context
  getMergedContext() {
    return this.mergedContext;
  }

  // Check if a document exists
  hasDocument(url) {
    return this.documents.has(url);
  }

  // Get document count
  getDocumentCount() {
    return this.documents.size;
  }

  // Get context terms count
  getContextTermsCount() {
    return Object.keys(this.mergedContext).length;
  }
}
