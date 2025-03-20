name: action output

on:
  workflow_call:
    inputs:
      content:
        required: true
        type: string


jobs:
  action-output:
    # runs-on: ubuntu-latest
    steps:
    - name: Write updated directories to summary
      run: |
        # Write Markdown to the GitHub Actions summary
        echo "${{inputs.content}}" >> $GITHUB_STEP_SUMMARY

        