from .git_core import url,url2io,toplevel
from .git_repo_metadata import getreponame
from ... import reverse_mapping
from ..json import DotAccessibleDict

from rich import box
from rich.panel import Panel
from rich.console import Console #, ConsoleOptions, Group, RenderableType, RenderResult
console = Console()

def cmip_info():
    repo_url = url()
    io_url = url2io(repo_url)

    # branch = getbranch()
    repopath = toplevel()
    reponame = getreponame()

    whoami = reverse_mapping()[io_url]
    
    console.print(Panel.fit(
        f"[bold cyan]Parsing repo:[/bold cyan] {whoami}\n"
        f"[bold magenta]Location:[/bold magenta] {repo_url}\n"
        f"[bold red]Github IO link:[/bold red] {io_url}",
        title="[bold yellow]Repository Info[/bold yellow]",
        border_style="blue"
        ), justify="center"
    )
    
# return a dot accesable dict with the following
# whoami, path, name, url, io

    
    return DotAccessibleDict(
        whoami=whoami,
        path=repopath,
        name=reponame,
        url=repo_url,
        io=io_url
    )


