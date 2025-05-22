
jq -r 'recurse(.[]? // empty) | objects | keys_unsorted[]' *.json | sort | uniq -c | sort -nr

