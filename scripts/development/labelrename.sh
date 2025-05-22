#!/bin/bash

# Ensure jq is installed
if ! command -v jq &> /dev/null; then
  echo "Error: jq is not installed. Please install jq and try again."
  exit 1
fi

# Function to rename keys
transform_json_keys() {
  jq '
    def walk(f):
      . as $in
      | if type == "object" then
          reduce keys[] as $key
            ({}; . + {
              ($key
                | if . == "long-label" then "ui-label"
                  elif . == "long_label" then "ui-label"
                  elif . == "label" then "validation-key"
                  else .
                end): ($in[$key] | walk(f))
            })
        elif type == "array" then map(walk(f))
        else .
      end;
    walk(.)
  ' "$1"
}

# Find and process each JSON file
find . -type f -name "*.json" | while read -r file; do
  echo "Processing: $file"
  tmp=$(mktemp)
  if transform_json_keys "$file" > "$tmp"; then
    mv "$tmp" "$file"
  else
    echo "Failed to process $file"
    rm -f "$tmp"
  fi
done


