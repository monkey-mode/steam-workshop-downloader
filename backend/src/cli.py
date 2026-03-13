"""CLI commands for Steam Workshop Downloader."""

import asyncio
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

from .api import browse_workshop, get_item_details, parse_workshop_id, parse_app_id
from .downloader import stream_download, find_steamcmd, get_install_instructions

console = Console()

SORT_TYPES = {
    "trend": 1,
    "top": 0,
    "new": 3,
    "favorites": 2,
}


def print_items_table(items, show_index: bool = False):
    table = Table(box=box.ROUNDED, show_header=True, header_style="bold cyan")
    if show_index:
        table.add_column("#", style="dim", width=4)
    table.add_column("ID", style="cyan", width=12)
    table.add_column("Title", min_width=30)
    table.add_column("Size", justify="right", width=10)
    table.add_column("Subscriptions", justify="right", width=14)
    table.add_column("Tags", width=30)

    for i, item in enumerate(items, 1):
        tags = ", ".join(item.tags[:3])
        row = [item.workshop_id, item.title, item.size_human(),
               f"{item.subscriptions:,}", tags]
        if show_index:
            row.insert(0, str(i))
        table.add_row(*row)

    console.print(table)


@click.group()
def cli():
    """Steam Workshop Downloader - Browse and download Workshop mods."""
    pass


@cli.command()
@click.argument("url_or_appid")
@click.option("--sort", default="trend", type=click.Choice(list(SORT_TYPES.keys())),
              help="Sort order (default: trend)")
@click.option("--page", default=1, show_default=True, help="Page number")
@click.option("--count", default=20, show_default=True, help="Items per page")
@click.option("--search", default="", help="Search query")
def browse(url_or_appid, sort, page, count, search):
    """Browse Workshop items for an app.

    URL_OR_APPID can be an app ID (e.g. 255710) or a Workshop URL.

    Examples:\n
      swdl browse 255710\n
      swdl browse 255710 --sort new --count 10\n
      swdl browse 255710 --search "road"\n
      swdl browse "https://steamcommunity.com/app/255710/workshop/"
    """
    app_id = parse_app_id(url_or_appid) if url_or_appid.startswith("http") else url_or_appid
    if not app_id:
        console.print("[red]Could not determine app ID from input.[/red]")
        raise SystemExit(1)

    with console.status(f"Fetching workshop items for app {app_id}..."):
        total, items = browse_workshop(
            app_id,
            query_type=SORT_TYPES[sort],
            page=page,
            count=count,
            search_text=search,
            sort=sort,
        )

    if not items:
        console.print("[yellow]No items found.[/yellow]")
        return

    console.print(Panel(
        f"App ID: [cyan]{app_id}[/cyan]  |  Sort: [cyan]{sort}[/cyan]  |  "
        f"Page: [cyan]{page}[/cyan]  |  Total: [cyan]{total:,}[/cyan]",
        title="Steam Workshop",
    ))
    print_items_table(items)
    console.print(f"\n[dim]Showing {len(items)} of {total:,} items. Use --page to navigate.[/dim]")


@cli.command()
@click.argument("workshop_url_or_id", nargs=-1, required=True)
@click.option("--output", "-o", default="./downloads", show_default=True,
              help="Output directory")
@click.option("--app-id", "-a", default=None,
              help="App ID (required if ID cannot be inferred from URL)")
@click.option("--username", "-u", default="anonymous", show_default=True,
              help="Steam username (use 'anonymous' for F2P games)")
def download(workshop_url_or_id, output, app_id, username):
    """Download one or more Workshop items via SteamCMD.

    Accepts Workshop item URLs or IDs.

    Examples:\n
      swdl download 123456789\n
      swdl download 123456789 987654321\n
      swdl download "https://steamcommunity.com/sharedfiles/filedetails/?id=123456789"\n
      swdl download 123456789 -a 255710 -o ~/mods -u mysteamuser
    """
    if not find_steamcmd():
        console.print(f"[red]SteamCMD not found.[/red]\n{get_install_instructions()}")
        raise SystemExit(1)

    workshop_ids = []
    inferred_app_id = app_id
    for item in workshop_url_or_id:
        wid = parse_workshop_id(item)
        if not wid:
            console.print(f"[red]Could not parse workshop ID from: {item}[/red]")
            raise SystemExit(1)
        workshop_ids.append(wid)
        if not inferred_app_id:
            inferred_app_id = parse_app_id(item)

    if not inferred_app_id:
        console.print("[yellow]App ID not specified; fetching from Steam API...[/yellow]")
        items = get_item_details(workshop_ids[:1])
        if items:
            inferred_app_id = items[0].app_id
        if not inferred_app_id:
            console.print("[red]Could not determine app ID. Use --app-id.[/red]")
            raise SystemExit(1)

    console.print(f"[cyan]App ID:[/cyan]  {inferred_app_id}")
    console.print(f"[cyan]Items:[/cyan]   {', '.join(workshop_ids)}")
    console.print(f"[cyan]Output:[/cyan]  {output}")
    console.print(f"[cyan]User:[/cyan]    {username}")
    console.print()

    async def run():
        success = False
        async for line in stream_download(inferred_app_id, workshop_ids, output, username=username):
            if line.startswith("SUCCESS:"):
                path = line[len("SUCCESS:"):]
                console.print(f"\n[green]Download complete![/green] Files saved to:\n  {path}")
                success = True
            elif line.startswith("ERROR:"):
                msg = line[len("ERROR:"):]
                console.print(f"\n[red]Download failed:[/red] {msg}")
            else:
                console.print(f"[dim]{line}[/dim]")
        return success

    ok = asyncio.run(run())
    if not ok:
        raise SystemExit(1)


@cli.command()
@click.argument("workshop_url_or_id", nargs=-1, required=True)
def info(workshop_url_or_id):
    """Show details for one or more Workshop items.

    Examples:\n
      swdl info 123456789\n
      swdl info "https://steamcommunity.com/sharedfiles/filedetails/?id=123456789"
    """
    ids = []
    for item in workshop_url_or_id:
        wid = parse_workshop_id(item)
        if not wid:
            console.print(f"[red]Could not parse workshop ID from: {item}[/red]")
            raise SystemExit(1)
        ids.append(wid)

    with console.status("Fetching item details..."):
        items = get_item_details(ids)

    if not items:
        console.print("[yellow]No items found.[/yellow]")
        return

    for item in items:
        console.print(Panel(
            f"[bold]{item.title}[/bold]\n\n"
            f"[cyan]ID:[/cyan]            {item.workshop_id}\n"
            f"[cyan]App ID:[/cyan]        {item.app_id}\n"
            f"[cyan]Size:[/cyan]          {item.size_human()}\n"
            f"[cyan]Subscriptions:[/cyan] {item.subscriptions:,}\n"
            f"[cyan]Favorited:[/cyan]     {item.favorited:,}\n"
            f"[cyan]Tags:[/cyan]          {', '.join(item.tags) or 'None'}\n\n"
            f"[dim]{item.description[:300]}{'...' if len(item.description) > 300 else ''}[/dim]",
            title="Workshop Item",
        ))


@cli.command()
def check():
    """Check if SteamCMD is installed and available."""
    cmd = find_steamcmd()
    if cmd:
        console.print(f"[green]SteamCMD found:[/green] {cmd}")
    else:
        console.print(f"[red]SteamCMD not found.[/red]\n{get_install_instructions()}")
