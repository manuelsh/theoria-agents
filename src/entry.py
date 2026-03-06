"""Entry point for theoria-agents CLI."""


def main():
    """Main entry point."""
    from src.cli import main as cli_main
    return cli_main()


def generate_main():
    """Legacy entry point for theoria-generate command."""
    import sys
    sys.argv.insert(1, "generate")
    return main()
