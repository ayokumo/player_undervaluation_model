"""Ask the scouting assistant a question from the terminal.

Usage (once step 4 is done):
    python -m rag.cli "which wingers outside the top five leagues match this profile?"
"""

import argparse

from rag.chain import answer


def main() -> None:
    parser = argparse.ArgumentParser(description="Ask the RAG scouting assistant a question.")
    parser.add_argument("question", help="Your recruitment question in plain language")
    args = parser.parse_args()
    result = answer(args.question)
    print(result["answer"])
    print("\nSources:", ", ".join(result["sources"]))


if __name__ == "__main__":
    main()
