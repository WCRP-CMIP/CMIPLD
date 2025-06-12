from ..locations import mapping, matches


class ProcessURL:

    @staticmethod
    def _extract_base_url(url: str) -> str:
        """
        Extract the base URL from a full URL path.

        Args:
            url: The full URL to process

        Returns:
            The base URL containing protocol and domain
        """
        parts = url.split('/')
        return '/'.join(parts[:3])

    @staticmethod
    def id2ctx(id: str) -> str:
        """
        Convert an ID to a context URL.

        Args:
            id: The ID to convert

        Returns:
            The context URL
        """
        return "/".join(id.split("/")[:-1] + ["_context_"])

    @staticmethod
    def resolve_prefix(query):
        if isinstance(query, str) and not query.startswith('http'):
            m = matches.search(query+':')
            if m:
                match = m.group()
                if len(match)-1 == len(query):
                    query = f"{mapping[match]}graph.jsonld"
                else:
                    query = query.replace(match, mapping[match[:-1]])
                print('Substituting prefix:')
                print(match, query)
        return query
