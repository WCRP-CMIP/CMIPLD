find . -type f -name '*.json' -exec sh -c '
  for file; do
    jq 'walk(
      if type == "object" then with_entries(
        if .key == "label" then .key = "validation-key"
        elif .key == "long-label" then .key = "ui-label"
        else .
        end
      ) else . end
    )' "$file" > "$file.tmp" && mv "$file.tmp" "$file"
  done
' sh {} +
