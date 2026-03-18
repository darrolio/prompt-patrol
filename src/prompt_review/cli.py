"""CLI commands for Prompt Review administration."""
import argparse
import asyncio
import secrets
import sys
from datetime import date
from pathlib import Path


def generate_api_key() -> str:
    return secrets.token_hex(32)


async def cmd_register_developer(args):
    from sqlalchemy import select
    from prompt_review.database import async_session_factory
    from prompt_review.models import Developer

    api_key = generate_api_key()

    async with async_session_factory() as session:
        # Check if username already exists
        result = await session.execute(
            select(Developer).where(Developer.username == args.username)
        )
        existing = result.scalar_one_or_none()
        if existing:
            print(f"Error: Developer '{args.username}' already exists.")
            print(f"Existing API key: {existing.api_key}")
            sys.exit(1)

        dev = Developer(
            username=args.username,
            display_name=args.display_name or args.username,
            api_key=api_key,
        )
        session.add(dev)
        await session.commit()

    print(f"Developer registered: {args.username}")
    print(f"API Key: {api_key}")
    print()
    print("Configure the hook on the developer's machine:")
    print(f'  export PROMPT_REVIEW_API_KEY="{api_key}"')
    print(f'  export PROMPT_REVIEW_URL="http://your-server:8000"')


async def cmd_import_docs(args):
    from prompt_review.database import async_session_factory
    from prompt_review.schemas.product_doc import ProductDocCreate
    from prompt_review.services.product_docs import create_doc

    path = Path(args.path)
    if not path.exists():
        print(f"Error: Path '{path}' does not exist.")
        sys.exit(1)

    files = [path] if path.is_file() else sorted(path.glob("*"))
    files = [f for f in files if f.is_file() and f.suffix in (".md", ".txt", ".rst")]

    if not files:
        print(f"No .md/.txt/.rst files found in '{path}'")
        sys.exit(1)

    async with async_session_factory() as session:
        for f in files:
            content = f.read_text(encoding="utf-8")
            data = ProductDocCreate(
                filename=f.name,
                display_name=f.stem.replace("-", " ").replace("_", " ").title(),
                content=content,
                doc_type=args.doc_type,
                uploaded_by="cli-import",
            )
            try:
                await create_doc(session, data)
                print(f"  Imported: {f.name} ({len(content)} chars)")
            except Exception as e:
                print(f"  Skipped: {f.name} ({e})")

    print(f"Done. Imported from '{path}'")


async def cmd_run_review(args):
    from prompt_review.database import async_session_factory
    from prompt_review.services.review_engine import run_review

    target = date.fromisoformat(args.date) if args.date else date.today()

    print(f"Running review for {target}...")
    async with async_session_factory() as session:
        report = await run_review(session, target)

    print(f"Status: {report.status}")
    print(f"Prompts: {report.total_prompts}")
    print(f"Flagged: {report.flagged_count}")
    if report.error_message:
        print(f"Error: {report.error_message}")


def main():
    parser = argparse.ArgumentParser(prog="prompt-review", description="Prompt Review CLI")
    sub = parser.add_subparsers(dest="command")

    # register-developer
    reg = sub.add_parser("register-developer", help="Register a new developer and generate API key")
    reg.add_argument("username", help="Developer username (machine/git username)")
    reg.add_argument("--display-name", help="Friendly display name")

    # import-docs
    imp = sub.add_parser("import-docs", help="Import product documents from filesystem")
    imp.add_argument("path", help="File or directory to import")
    imp.add_argument("--doc-type", default="general", choices=["vision", "roadmap", "story", "general"])

    # run-review
    rev = sub.add_parser("run-review", help="Manually trigger a review")
    rev.add_argument("--date", help="Date to review (YYYY-MM-DD, default: today)")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    commands = {
        "register-developer": cmd_register_developer,
        "import-docs": cmd_import_docs,
        "run-review": cmd_run_review,
    }

    asyncio.run(commands[args.command](args))


if __name__ == "__main__":
    main()
