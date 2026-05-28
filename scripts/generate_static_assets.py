from pathlib import Path

from ba_monitor.cards import render_help_card
from ba_monitor.config import get_settings


def main() -> None:
    settings = get_settings()
    render_help_card(Path(settings.image_public_dir) / "help.png")


if __name__ == "__main__":
    main()
