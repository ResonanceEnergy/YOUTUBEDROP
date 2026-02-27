#!/usr/bin/env python3
"""
YOUTUBEDROP - Main CLI
=======================
YouTube content pipeline: ingest → generate → upload.

Usage:
  python main.py ingest <url> [--download] [--transcribe]
  python main.py search <query> [--limit 10]
  python main.py script <topic> [--duration 10] [--tone "educational"]
  python main.py upload <video_file> --title "..." --description "..."
  python main.py pipeline <topic>  # Full: script → (manual record) → upload
"""

import json
import logging
import sys
from pathlib import Path

import click
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [YOUTUBEDROP] %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))
from ingestor import YouTubeIngestor
from script_generator import ScriptGenerator
from upload_manager import UploadManager


@click.group()
def cli():
    """YOUTUBEDROP — YouTube Content Pipeline"""
    pass


@cli.command()
@click.argument("url")
@click.option("--download", is_flag=True, help="Download audio")
@click.option("--transcribe", is_flag=True, help="Transcribe with Whisper")
@click.option("--output", default=None, help="Save result to JSON file")
def ingest(url, download, transcribe, output):
    """Ingest a YouTube video — fetch metadata, optionally download and transcribe."""
    ingestor = YouTubeIngestor()
    result = ingestor.ingest_video(url, download=download, transcribe=transcribe)

    if output:
        Path(output).write_text(json.dumps(result, indent=2), encoding="utf-8")
        click.echo(f"Saved to {output}")
    else:
        click.echo(json.dumps(result, indent=2))


@cli.command()
@click.argument("query")
@click.option("--limit", default=10, help="Max results")
def search(query, limit):
    """Search YouTube for videos."""
    ingestor = YouTubeIngestor()
    results = ingestor.search_videos(query, max_results=limit)

    if not results:
        click.echo("No results found.")
        return

    for i, v in enumerate(results, 1):
        click.echo(f"\n{i}. {v['title']}")
        click.echo(f"   Channel: {v['channel']}")
        click.echo(f"   URL: {v['url']}")


@cli.command()
@click.argument("topic")
@click.option("--duration", default=10, help="Target duration in minutes")
@click.option("--tone", default="educational, energetic", help="Script tone")
@click.option("--context", default="", help="Additional context")
@click.option("--output", default=None, help="Save script to file")
def script(topic, duration, tone, context, output):
    """Generate a YouTube script from a topic."""
    generator = ScriptGenerator()
    click.echo(f"Generating script for: {topic}")

    result = generator.generate(topic, context=context, duration_min=duration, tone=tone)
    if not result:
        click.echo("Script generation failed — check API keys.")
        return

    # Also generate title/description
    meta = generator.generate_title_and_description(result, topic)

    full_output = f"""TOPIC: {topic}
TITLES:
{chr(10).join(f'  - {t}' for t in meta.get('titles', []))}

TAGS: {', '.join(meta.get('tags', []))}

DESCRIPTION:
{meta.get('description', '')}

---SCRIPT---
{result}
"""

    if output:
        Path(output).write_text(full_output, encoding="utf-8")
        click.echo(f"Script saved to {output}")
    else:
        click.echo(full_output)


@cli.command()
@click.argument("video_file")
@click.option("--title", required=True, help="Video title")
@click.option("--description", default="", help="Video description")
@click.option("--tags", default="", help="Comma-separated tags")
@click.option("--privacy", default="private", type=click.Choice(["private", "unlisted", "public"]))
@click.option("--thumbnail", default=None, help="Thumbnail image path")
def upload(video_file, title, description, tags, privacy, thumbnail):
    """Upload a video to YouTube."""
    manager = UploadManager()
    tag_list = [t.strip() for t in tags.split(",") if t.strip()]

    click.echo(f"Uploading: {title}")
    video_id = manager.upload(
        video_file,
        title=title,
        description=description,
        tags=tag_list,
        privacy=privacy,
    )

    if video_id:
        click.echo(f"Uploaded: https://youtube.com/watch?v={video_id}")
        if thumbnail:
            manager.set_thumbnail(video_id, thumbnail)
            click.echo("Thumbnail set.")
    else:
        click.echo("Upload failed.")


@cli.command()
@click.argument("topic")
@click.option("--duration", default=10, help="Target video length (minutes)")
@click.option("--output-dir", default="output", help="Where to save script and metadata")
def pipeline(topic, duration, output_dir):
    """
    Full content pipeline: generate script → save for recording → prep upload metadata.
    (Recording step is manual — this preps everything around it.)
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    # Step 1: Generate script
    click.echo(f"\n[1/3] Generating script for: {topic}")
    generator = ScriptGenerator()
    script_text = generator.generate(topic, duration_min=duration)
    if not script_text:
        click.echo("Script generation failed.")
        return

    script_file = out / "script.md"
    script_file.write_text(script_text, encoding="utf-8")
    click.echo(f"  Script saved: {script_file}")

    # Step 2: Generate metadata
    click.echo("\n[2/3] Generating title, description, tags...")
    meta = generator.generate_title_and_description(script_text, topic)
    meta_file = out / "metadata.json"
    meta_file.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    click.echo(f"  Metadata saved: {meta_file}")

    # Step 3: Instructions
    click.echo("\n[3/3] Pipeline ready!")
    click.echo(f"\n  Suggested titles:")
    for t in meta.get("titles", [])[:3]:
        click.echo(f"    - {t}")
    click.echo(f"\n  Next steps:")
    click.echo(f"    1. Record video using script: {script_file}")
    click.echo(f"    2. Upload with:")
    click.echo(f'       python main.py upload <video.mp4> --title "{meta["titles"][0] if meta["titles"] else topic}"')
    click.echo(f"    Output saved to: {out}/")


if __name__ == "__main__":
    cli()
