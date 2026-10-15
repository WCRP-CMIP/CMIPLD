```bash
      
      - name: LOG RUN
        uses: WCRP-CMIP/CMIPLD/actions/matomo@main
        with:
          site-id: "4"
          base-url: "${{ github.server_url }}/${{ github.repository }}"
          path: "/issues/${{ github.event.inputs.issue_number || github.event.issue.number }}?author=${{ github.event.sender.login || 'unknown' }}"
          title: "${{ github.event.issue.title }}"

```
