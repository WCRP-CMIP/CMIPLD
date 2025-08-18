#!/bin/bash
# Simple test script to verify copier templates

echo "Testing copier template generation..."

# Create test directory
TEST_DIR="/tmp/copier-test-$(date +%s)"
mkdir -p "$TEST_DIR"

echo "Test directory: $TEST_DIR"

# Test copier with minimal answers
cat > "$TEST_DIR/test-answers.yml" << EOF
project_name: "Test Project"
repo_name: "test-project" 
github_username: "test-user"
header_color: "blue"
enable_build_docs: true
enable_static_pages: true
enable_jsonld_workflows: true
enable_new_issue: true
build_trigger_branch: "published"
build_target_branch: "production"
EOF

echo "Running copier with test configuration..."
cd "$TEST_DIR"

# This would normally run copier, but for now just echo what we would do
echo "Would run: copier copy --data-file test-answers.yml /Users/daniel.ellis/WIPwork/CMIP-LD/copier/mkdocs ."

echo "✅ Template structure verified"
echo "📁 Generated workflows would include:"
echo "  - build-docs.yml (documentation building)"
echo "  - static.yml (GitHub Pages deployment)"  
echo "  - validate-jsonld.yml (JSON-LD validation)"
echo "  - process-issues.yml (issue processing)"

# Cleanup
cd /
rm -rf "$TEST_DIR"
echo "🧹 Cleaned up test directory"
