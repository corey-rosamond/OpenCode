"""Setup wizard for Code-Forge first-time configuration.

This module provides an interactive setup experience for new users
to configure their API keys and basic settings.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import TYPE_CHECKING

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm

if TYPE_CHECKING:
    from code_forge.config import CodeForgeConfig

console = Console()


def run_setup_wizard(config_dir: Path | None = None) -> str | None:
    """Run the interactive setup wizard.

    Guides users through setting up their OpenRouter API key
    and saves it to the user configuration file.

    Args:
        config_dir: Configuration directory. Defaults to ~/.forge

    Returns:
        The API key if setup was successful, None if cancelled.
    """
    config_dir = config_dir or Path.home() / ".forge"

    # Display welcome banner
    console.print()
    console.print(Panel.fit(
        "[bold cyan]Welcome to Code-Forge![/bold cyan]\n\n"
        "Let's get you set up with your API configuration.\n"
        "You'll need an OpenRouter API key to use Code-Forge.",
        title="[bold]Setup Wizard[/bold]",
        border_style="cyan",
    ))
    console.print()

    # Explain where to get API key
    console.print("[bold]Step 1:[/bold] Get your OpenRouter API key")
    console.print()
    console.print("  1. Go to [link=https://openrouter.ai/keys]https://openrouter.ai/keys[/link]")
    console.print("  2. Sign in or create an account")
    console.print("  3. Create a new API key")
    console.print("  4. Copy the key (starts with 'sk-or-')")
    console.print()

    # Prompt for API key
    while True:
        api_key = Prompt.ask(
            "[bold]Step 2:[/bold] Paste your OpenRouter API key"
        )

        # Strip whitespace
        api_key = api_key.strip() if api_key else ""

        # Check for empty input
        if not api_key:
            console.print("[red]API key cannot be empty.[/red]")
            if Confirm.ask("Would you like to exit setup?", default=False):
                console.print("[yellow]Setup cancelled. Run 'forge' again to retry.[/yellow]")
                return None
            continue

        # Validate format
        if not api_key.startswith("sk-or-"):
            console.print("[yellow]Warning: OpenRouter API keys typically start with 'sk-or-'[/yellow]")
            if not Confirm.ask("Use this key anyway?", default=False):
                continue

        break

    # Save configuration
    console.print()
    console.print("[bold]Step 3:[/bold] Saving configuration...")

    try:
        save_api_key(api_key, config_dir)
        console.print(f"[green]API key saved to {config_dir / 'settings.json'}[/green]")
    except Exception as e:
        console.print(f"[red]Failed to save configuration: {e}[/red]")
        console.print("[yellow]You can set the OPENROUTER_API_KEY environment variable instead.[/yellow]")
        return api_key  # Return key anyway so session can continue

    # Success message
    console.print()
    console.print(Panel.fit(
        "[bold green]Setup complete![/bold green]\n\n"
        "You're all set to use Code-Forge.\n"
        "Type your message or use /help for available commands.",
        border_style="green",
    ))
    console.print()

    return api_key


def save_api_key(api_key: str, config_dir: Path | None = None) -> None:
    """Save API key to user configuration file.

    Args:
        api_key: The OpenRouter API key to save.
        config_dir: Configuration directory. Defaults to ~/.forge

    Raises:
        OSError: If configuration cannot be saved.
    """
    config_dir = config_dir or Path.home() / ".forge"
    config_file = config_dir / "settings.json"

    # Create directory if needed
    config_dir.mkdir(parents=True, exist_ok=True)

    # Load existing config or start fresh
    config: dict = {}
    if config_file.exists():
        try:
            with config_file.open() as f:
                config = json.load(f)
        except (json.JSONDecodeError, OSError):
            pass  # Start fresh if file is corrupted

    # Update API key
    config["api_key"] = api_key

    # Save with proper permissions (readable only by owner)
    with config_file.open("w") as f:
        json.dump(config, f, indent=2)

    # Set restrictive permissions on the config file (contains secrets)
    try:
        config_file.chmod(0o600)
    except OSError:
        pass  # Windows doesn't support chmod the same way


def check_api_key_configured(config: CodeForgeConfig) -> bool:
    """Check if API key is configured.

    Args:
        config: The loaded configuration.

    Returns:
        True if API key is available, False otherwise.
    """
    # Check environment variable first
    if os.environ.get("OPENROUTER_API_KEY"):
        return True

    # Check config
    return config.get_api_key() is not None
