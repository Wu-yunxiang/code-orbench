import argparse
import os
import shutil
from pathlib import Path


def merge_judged_dirs(input_dirs, output_dir, overwrite=False):
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    copied = []
    skipped = []
    for input_dir in input_dirs:
        for path in sorted(Path(input_dir).glob("*_judged.jsonl")):
            target = output_path / path.name
            if target.exists() and not overwrite:
                skipped.append(str(target))
                continue
            shutil.copy2(path, target)
            copied.append(str(target))

            report = path.with_name(path.name.replace("_judged.jsonl", "_report.txt"))
            if report.exists():
                shutil.copy2(report, output_path / report.name)

    print(f"Copied judged files: {len(copied)}")
    for path in copied:
        print(f"  + {path}")
    if skipped:
        print(f"Skipped existing files: {len(skipped)}")
        for path in skipped:
            print(f"  = {path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dirs", nargs="+", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    merge_judged_dirs(args.input_dirs, args.output_dir, overwrite=args.overwrite)


if __name__ == "__main__":
    main()
