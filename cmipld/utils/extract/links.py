from pyld import jsonld
from urllib.parse import urljoin
from typing import Any, Dict, List, Union, Set
from ...locations import mapping



def depends(url: str, prefix: bool = False, relative: bool = False, graph=False) -> Set[str]:
        """
        Extract all dependencies (@id references) from a JSON-LD document.

        Args:
            url: URL of the JSON-LD document
            relative: If True, returns relative URLs, if False returns absolute URLs
            graph: Returns the location of the graph object - incompatible with relative

        Returns:
            Set of dependency URLs found in the document
        """
        try:
            # Frame the document to extract all @id references
            # query = self.replace_prefix(url)
            
            # "@context":url
            frm = {'@explicit': True}
            
            if prefix: # use the context to apply prefixes to the dependancies. 
                frm['@context'] = mapping
                # {'wcrpo':'https://wcrp-cmip.github.io/'}
            
            framed = jsonld.frame(url, frm)
            
            ids = framed.get('@graph', [])

            # Process URLs based on relative flag
            if relative:
                return {item['@id'] for item in ids if '@id' in item}

            elif graph:
                return list(set({urljoin(url, self.graphify(item['@id'])) for item in ids if '@id' in item}))

            else:
                return {urljoin(url, item['@id']) for item in ids if '@id' in item}

        except Exception as e:
            print(f"Error extracting dependencies: {str(e)}")
            return set()

def display_depends(url: str, prefix: bool = True, relative: bool = False) -> None:
    """
    Display dependencies of a JSON-LD document in a formatted panel.

    Args:
        url: URL of the JSON-LD document
        prefix: If True, uses prefixes for formatting
        relative: If True, displays relative URLs
    """

    from rich.console import Console, Group
    from rich.panel import Panel
    from rich.text import Text
    import re
    # Define colors for styled output
    colours = {
        "PacificCyan": "#26A3C1",
        "SteelPink": "#B74EB6",
        "Aero": "#28B7D8",
        "Aureolin": "#E5E413",
        "Imperial red": "#F04D4C",
        "Jade": "#0DA66B",
        "Azul": "#2372C7"
    }

    # Import dependencies (assumes extract.depends is defined elsewhere)
    dep = list(depends(url, relative=relative, prefix=prefix))
    dep.sort()

    # Define regex based on format type (prefix vs full URL)
    if prefix:
        # Match: prefix:folder/filename(.jsonld)?
        pattern = re.compile(r'(\w+:)([\w\-/]+\/)([\w\-/]+)(\.jsonld)?')
    else:
        # Match: full URL with domain, folder/, and filename(.jsonld)?
        pattern = re.compile(r'https?://([\w\-.]+/[\w\-/]+/)([\w\-/]+/)([\w\-/]+)(\.jsonld)?')

    # Set fixed widths for aligned display
    widths = [42, 4, 50]

    # Format each match into aligned colored segments using Rich markup
    def replace(m: re.Match) -> str:
        part1 = (m.group(1)[:-1] + '[/]' + m.group(1)[-1])  # Close style before last char (e.g., colon)
        return (
            f"  [bold {colours['Aureolin']}]{part1.rjust(widths[0])}"
            f"[{colours['Aero']}]{m.group(2).rjust(widths[1])}[/]"
            f"[{colours['Imperial red']}]{(m.group(3) or '').ljust(widths[2])}[/]"
            
        )

    # Apply regex substitution and wrap each in a Rich Text object
    text_sections: List[Text] = [Text.from_markup(pattern.sub(replace, d)) for d in dep]

    # Build panel with grouped lines
    panel = Panel(
        Group(*text_sections),
        title=f"Dependencies for {url}",
        # title_style=f"bold {colours['Jade']}",
        border_style=colours['Azul'],
        padding=(1, 2)
    )

    # Display in console
    console = Console()
    console.print(panel)