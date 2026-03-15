"""
YouTube Investigator - CLI Entry Point
"""
import click
import json
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from datetime import timedelta

from src.config import config
from src.quota.tracker import QuotaTracker
from src.api.youtube_client import YouTubeClient
from src.analysis.channel_stats import ChannelAnalyzer
from src.export.json_export import JSONExporter
from src import shared_sync

console = Console()


@click.group()
@click.version_option(version='0.1.0', prog_name='yt-investigate')
def cli():
    """
    YouTube Channel Investigator - Investigative Analysen von YouTube-Kanälen
    mit intelligentem Quota-Management
    """
    pass


@cli.group()
def quota():
    """Quota-Management Befehle"""
    pass


@quota.command('status')
def quota_status():
    """
    Zeigt aktuellen Quota-Status an
    """
    try:
        tracker = QuotaTracker()
        status = tracker.get_status()

        # Farbcodierung basierend auf Verbrauch
        if status['percentage'] >= 0.9:
            color = 'red'
            emoji = '[!]'
        elif status['percentage'] >= status['warning_threshold']:
            color = 'yellow'
            emoji = '[!]'
        else:
            color = 'green'
            emoji = '[OK]'

        # Header
        console.print()
        console.print(Panel.fit(
            f"[bold]YouTube API Quota Status[/bold]\n"
            f"Datum: {status['date']} (Pacific Time)",
            border_style=color
        ))

        # Quota-Übersicht Tabelle
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Metrik", style="cyan", width=20)
        table.add_column("Wert", style="white", width=30)

        # Verbrauchte Units
        table.add_row(
            "Verbrauchte Units",
            f"[{color}]{status['used']:,}[/{color}]"
        )

        # Limit
        table.add_row(
            "Tägliches Limit",
            f"{status['limit']:,}"
        )

        # Verbleibend
        remaining_style = color if status['remaining'] < 1000 else 'green'
        table.add_row(
            "Verbleibend",
            f"[{remaining_style}]{status['remaining']:,}[/{remaining_style}]"
        )

        # Prozentsatz
        percentage_display = f"{status['percentage']*100:.1f}%"
        table.add_row(
            "Verbrauch",
            f"[{color}]{percentage_display}[/{color}]"
        )

        # Zeit bis Reset
        hours = int(status['time_until_reset'].total_seconds() // 3600)
        minutes = int((status['time_until_reset'].total_seconds() % 3600) // 60)
        table.add_row(
            "Reset in",
            f"{hours}h {minutes}m"
        )

        console.print(table)

        # Warnung falls Threshold überschritten
        if status['is_warning']:
            console.print()
            console.print(
                f"[bold {color}]{emoji} Warnung: Quota-Limit fast erreicht![/bold {color}]"
            )
            console.print(
                f"Verbleibende Units: {status['remaining']:,} "
                f"({(1-status['percentage'])*100:.1f}% verfügbar)"
            )

        # Erfolgs-Status
        if status['percentage'] < 0.5:
            console.print()
            console.print(f"[green][OK] Quota-Status: Gut ({percentage_display} verwendet)[/green]")

        console.print()

    except Exception as e:
        console.print(f"[red][X] Fehler beim Abrufen des Quota-Status: {e}[/red]")
        raise click.Abort()


@quota.command('history')
@click.option('--days', default=7, help='Anzahl Tage zurück (Standard: 7)')
def quota_history(days):
    """
    Zeigt Quota-Verlauf der letzten N Tage
    """
    console.print(f"[yellow][i] Quota-Verlauf (letzte {days} Tage) - Coming soon![/yellow]")


@quota.command('estimate')
@click.argument('identifier')
@click.option('--days', default=90, help='Zeitraum in Tagen')
@click.option('--max-videos', type=int, help='Maximale Anzahl Videos')
def quota_estimate(identifier, days, max_videos):
    """
    Schätzt Quota-Kosten für eine Kanal-Analyse
    """
    try:
        analyzer = ChannelAnalyzer()
        costs = analyzer.estimate_quota_cost(identifier, days, max_videos)

        console.print()
        console.print(Panel.fit(
            f"[bold]Quota-Kosten Schätzung für {identifier}[/bold]",
            border_style="cyan"
        ))

        table = Table(show_header=True)
        table.add_column("Operation", style="cyan")
        table.add_column("Kosten", style="white", justify="right")

        table.add_row("Channel-ID Auflösung", f"{costs['channel_id_resolution']} Units")
        table.add_row("Kanal-Info", f"{costs['channel_info']} Units")
        table.add_row("Playlist Items", f"{costs['playlist_items']} Units")
        table.add_row("Video Details", f"{costs['video_details']} Units")
        table.add_row("[bold]Gesamt", f"[bold]{costs['total']} Units")

        console.print(table)

        # Warnung falls zu teuer
        tracker = QuotaTracker()
        remaining = tracker.get_remaining()

        if costs['total'] > remaining:
            console.print(
                f"\n[red][!] Warnung: Nicht genug Quota verfügbar! "
                f"Benötigt: {costs['total']}, Verfügbar: {remaining}[/red]"
            )
        else:
            console.print(
                f"\n[green][OK] Genug Quota verfügbar "
                f"(verbleibend nach Analyse: {remaining - costs['total']:,})[/green]"
            )

        console.print()

    except Exception as e:
        console.print(f"[red][X] Fehler bei der Schätzung: {e}[/red]")
        raise click.Abort()


@cli.command()
@click.argument('identifier')
@click.option('--days', default=90, help='Zeitraum in Tagen (Standard: 90, 0 = alle)')
@click.option('--max-videos', type=int, help='Maximale Anzahl Videos')
@click.option('--export', type=click.Choice(['json']), help='Export als Datei')
@click.option('--output', '-o', type=click.Path(), help='Output-Dateipfad')
def channel(identifier, days, max_videos, export, output):
    """
    Analysiert einen YouTube-Kanal

    IDENTIFIER kann sein:
    - Channel-ID (UC...)
    - Handle (@username)
    - YouTube URL

    Beispiele:
      yt-investigate channel @RealCandaceO
      yt-investigate channel UCxxx123... --days 30
      yt-investigate channel https://youtube.com/@TurningPointUSA --export json
    """
    try:
        # Config validieren
        config.validate()

        # Analyzer initialisieren
        tracker = QuotaTracker()
        analyzer = ChannelAnalyzer(quota_tracker=tracker)

        # Progress Spinner
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:

            # Schritt 1: Channel-ID auflösen
            task = progress.add_task(f"[cyan]Löse Channel-ID auf für {identifier}...", total=None)

            try:
                # Analyse durchführen
                progress.update(task, description=f"[cyan]Analysiere Kanal {identifier}...")

                analysis = analyzer.analyze_channel(
                    identifier=identifier,
                    lookback_days=days,
                    max_videos=max_videos
                )

                progress.update(task, description="[green]Analyse abgeschlossen!")
                progress.stop()

            except Exception as e:
                progress.stop()
                console.print(f"\n[red][X] Fehler bei der Analyse: {e}[/red]\n")
                raise click.Abort()

        # Ergebnisse anzeigen
        console.print()
        console.print(Panel.fit(
            f"[bold]Kanal-Analyse: {analysis['channel']['title']}[/bold]",
            border_style="cyan"
        ))

        # Channel Info Tabelle
        info_table = Table(show_header=False, box=None)
        info_table.add_column("Label", style="cyan")
        info_table.add_column("Value", style="white")

        info_table.add_row("Kanal-ID", analysis['channel']['id'])
        info_table.add_row("Abonnenten", f"{analysis['channel']['subscribers']:,}")
        info_table.add_row("Gesamt-Videos", f"{analysis['channel']['total_videos']:,}")
        info_table.add_row("Gesamt-Views", f"{analysis['channel']['total_views']:,}")
        info_table.add_row("Erstellt am", analysis['channel']['created_at'][:10])

        console.print(info_table)
        console.print()

        # Statistiken Tabelle
        stats = analysis['statistics']
        period = analysis['analysis_period']

        stats_table = Table(title=f"Statistiken (letzte {days} Tage)", show_header=True)
        stats_table.add_column("Metrik", style="cyan")
        stats_table.add_column("Wert", style="white", justify="right")

        stats_table.add_row("Videos im Zeitraum", f"{stats['videos_in_period']:,}")
        stats_table.add_row("Gesamt-Views", f"{stats['total_views']:,}")
        stats_table.add_row("Durchschn. Views/Video", f"{stats['avg_views_per_video']:,}")
        stats_table.add_row("Median Views", f"{stats['median_views']:,}")
        stats_table.add_row("Max Views", f"{stats['max_views']:,}")
        stats_table.add_row("Min Views", f"{stats['min_views']:,}")
        stats_table.add_row("Engagement Rate", f"{stats['engagement_rate']}%")

        console.print(stats_table)
        console.print()

        # Quota Info
        meta = analysis['meta']
        quota_color = "green" if meta['quota_remaining'] > 5000 else "yellow"
        console.print(
            f"[{quota_color}]Quota verwendet: {meta['quota_used']} Units "
            f"(verbleibend: {meta['quota_remaining']:,})[/{quota_color}]"
        )

        # Export?
        if export == 'json' or output:
            exporter = JSONExporter()

            if output:
                filepath = exporter.export_to_file(analysis, filename=output)
            else:
                filepath = exporter.export_to_file(analysis)

            console.print(f"\n[green][OK] Exportiert nach: {filepath}[/green]")

        # JSON zu stdout falls kein Export
        if not export and not output:
            console.print("\n[dim]JSON-Ausgabe:[/dim]")
            exporter = JSONExporter()
            summary = exporter.create_summary(analysis)
            console.print(json.dumps(summary, indent=2, ensure_ascii=False))

        # Sync to shared database
        locked = False
        try:
            if shared_sync.is_available():
                locked = shared_sync.acquire_lock_with_warning()
                synced = shared_sync.sync_analysis(analysis)
                console.print(
                    f"\n[dim]Shared DB: Kanal + {synced} Videos synchronisiert[/dim]"
                )
                shared_sync.show_gaps()
        finally:
            if locked:
                shared_sync.release_lock()

        console.print()

    except Exception as e:
        console.print(f"\n[red][X] Unerwarteter Fehler: {e}[/red]\n")
        raise click.Abort()


@cli.command()
def test():
    """
    Testet die API-Verbindung
    """
    try:
        console.print("\n[cyan][i] Teste YouTube API Verbindung...[/cyan]\n")

        # Config validieren
        try:
            config.validate()
            console.print("[green][OK] Konfiguration OK[/green]")
        except ValueError as e:
            console.print(f"[red][X] Konfigurationsfehler: {e}[/red]")
            raise click.Abort()

        # API-Verbindung testen
        client = YouTubeClient()
        if client.test_connection():
            console.print("[green][OK] API-Verbindung erfolgreich[/green]")
        else:
            console.print("[red][X] API-Verbindung fehlgeschlagen[/red]")
            raise click.Abort()

        # Quota-Tracker testen
        tracker = QuotaTracker()
        status = tracker.get_status()
        console.print(
            f"[green][OK] Quota-Tracker OK "
            f"({status['remaining']:,} Units verfügbar)[/green]"
        )

        console.print("\n[bold green][OK] Alle Tests erfolgreich![/bold green]\n")

    except Exception as e:
        console.print(f"\n[red][X] Test fehlgeschlagen: {e}[/red]\n")
        raise click.Abort()


if __name__ == '__main__':
    cli()
