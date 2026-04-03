from rich.console import Console
from rich.progress import (
    Progress, BarColumn, DownloadColumn, TransferSpeedColumn,
    TimeRemainingColumn, TextColumn, SpinnerColumn
)
from rich.prompt import Confirm
from rich.table import Table
from rich.theme import Theme

theme = Theme({
    "info": "cyan",
    "success": "green",
    "warning": "yellow",
    "error": "bold red",
    "package": "bold cyan",
    "phase": "bold blue",
})

console = Console(theme=theme, highlight=False)


def success(msg):
    console.print("[success]\u2713[/] {}".format(msg))


def error(msg):
    console.print("[error]\u2717 {}[/]".format(msg))


def warning(msg):
    console.print("[warning]! {}[/]".format(msg))


def info(msg):
    console.print("[info]\u25cf[/] {}".format(msg))


def phase(msg):
    console.print("  [phase]\u25b8 {}[/]".format(msg))


def verbose(msg):
    console.print("  [dim]$ {}[/]".format(msg))


def pkg(name):
    return "[package]{}[/]".format(name)


def status(msg):
    return console.status("[bold]{}[/]".format(msg), spinner="dots")


def create_download_progress():
    return Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(bar_width=40),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        DownloadColumn(),
        TransferSpeedColumn(),
        TimeRemainingColumn(),
        console=console,
    )


def confirm(msg):
    return Confirm.ask("[bold]{}[/]".format(msg), default=False, console=console)


def package_table(packages):
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("name", style="bold cyan")
    for name in packages:
        table.add_row(name)
    return table
