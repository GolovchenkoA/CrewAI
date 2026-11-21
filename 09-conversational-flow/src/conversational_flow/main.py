"""CLI: chat_run [--session ID] [--say "message" ...]"""

import argparse
import sys

from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv(usecwd=True))

from conversational_flow.flow import build_flow


def run(argv: list[str] | None = None) -> None:
    # CrewAI prints emoji in its console panels; the default Windows console encoding cannot show them.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="Conversational flow demo")
    parser.add_argument(
        "--session", default="demo", help="session id; reuse it to continue a chat"
    )
    parser.add_argument(
        "--say",
        nargs="+",
        metavar="MESSAGE",
        help="send these messages one after another instead of opening a prompt",
    )
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)

    flow = build_flow()
    if args.say:
        try:
            for message in args.say:
                print(f"you: {message}")
                print(f"bot: {flow.handle_turn(message, session_id=args.session)}")
        finally:
            flow.finalize_session_traces()
        print(
            f"\n[session {args.session}: {flow.state.turns} turns, name={flow.state.customer_name!r}]"
        )
    else:
        print(f"session {args.session} (type exit to quit)")
        flow.chat(session_id=args.session)
    # must return None: console scripts do sys.exit(run())
