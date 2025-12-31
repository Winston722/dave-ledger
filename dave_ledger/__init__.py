import argparse

def main() -> int:
    parser = argparse.ArgumentParser(prog="dave-ledger")
    parser.add_argument("--version", action="store_true")
    args = parser.parse_args()

    if args.version:
        print("DAVE Ledger v0.1.0")
        return 0

    parser.print_help()
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
