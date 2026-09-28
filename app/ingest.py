import argparse
from .rag import KnowledgeBase
from .openai_client import OpenAIError


def main():
    parser = argparse.ArgumentParser(description="Build Lukomorie knowledge index")
    parser.add_argument("--rebuild", action="store_true")
    args = parser.parse_args()
    kb = KnowledgeBase()
    if args.rebuild:
        kb.ensure_loaded(rebuild=True)
    try:
        kb.build_embeddings()
        print("Knowledge index is ready.")
    except OpenAIError as exc:
        # The lexical index remains usable. A temporary API or regional error
        # must not prevent the web service from starting.
        print(f"Embedding build skipped: {exc}")
        print("Lexical knowledge index is ready.")


if __name__ == "__main__":
    main()
