"""Command-line interface for freetrans."""

import argparse
import asyncio
import sys

from freetrans import __version__
from freetrans.client import Translator


async def _run_cli(args: argparse.Namespace) -> None:
    ipv4 = getattr(args, "ipv4", False)
    provider = getattr(args, "provider", "google")
    async with Translator(ipv4=ipv4, provider=provider) as translator:
        if args.detect:
            result = await translator.detect(args.text)
            print(f"[{result.lang}, {result.confidence}] {args.text}")
            return

        result = await translator.translate(args.text, dest=args.dest, src=args.src)
        output = f"""[{result.src}] {result.origin}
    ->
[{result.dest}] {result.text}
[pron.] {result.pronunciation}"""
        print(output)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="freetrans: Free open translation across providers from the command line"
    )
    parser.add_argument("text", help="The text you want to translate.")
    parser.add_argument(
        "-d",
        "--dest",
        default="en",
        help="The destination language you want to translate into. (Default: en)",
    )
    parser.add_argument(
        "-s",
        "--src",
        default="auto",
        help="The source language of the text. (Default: auto)",
    )
    parser.add_argument(
        "-c", "--detect", action="store_true", default=False, help="Detect language"
    )
    parser.add_argument(
        "-4",
        "--ipv4",
        action="store_true",
        default=False,
        help="Force IPv4 resolution to prevent DNS timeout on networks with broken IPv6",
    )
    parser.add_argument(
        "-p",
        "--provider",
        default="google",
        help="Translation provider (default: google)",
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    args = parser.parse_args()
    asyncio.run(_run_cli(args))


if __name__ == "__main__":
    main()
