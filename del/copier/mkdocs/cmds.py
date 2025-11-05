python /Users/daniel.ellis/WIPwork/CMIP-LD/copier/mkdocs/auto-setup.py --no-confirm --force-overwrite

mkdocs build -f .src/mkdocs/mkdocs.yml 
mkdocs serve -f .src/mkdocs/mkdocs.yml






python /Users/daniel.ellis/WIPwork/CMIP-LD/copier/mkdocs/auto-setup.py --no-confirm --force-overwrite && mkdocs build -f .src/mkdocs/mkdocs.yml && python3 -m http.server -d .src/mkdocs/site 8000
