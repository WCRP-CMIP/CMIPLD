import re 

def get_doi(text):
	# Regex pattern to find DOI
	doi_pattern = r'\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b'
	matches = re.findall(doi_pattern, text, flags=re.IGNORECASE)
	#print(matches)  # ['10.1000/xyz123']
	return matches
