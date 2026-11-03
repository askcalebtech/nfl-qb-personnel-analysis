"""Command line: download data, build the model, validate and write the weekly projections JSON."""
import argparse
import json
import os
import sys
import tempfile

from .constants import PARAMS
from .data import download, load
from .output import build_games, build_payload, publish, validate
from .ratings import build_ratings, dropbacks, raw_values
from .simulate import simulate


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog='python3 -m projections.run')
    ap.add_argument('--season', type=int, required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--snapshots', required=True)
    ap.add_argument('--starters', required=True, help='JSON file mapping team code to starting QB')
    ap.add_argument('--data-dir', default=None, help='download location (default: a new temp directory)')
    ap.add_argument('--no-download', action='store_true', help='reuse files already in --data-dir')
    args = ap.parse_args(argv)
    if args.no_download and not args.data_dir:
        ap.error('--no-download requires --data-dir')
    data_dir = args.data_dir or tempfile.mkdtemp(prefix='nfl_projections_')

    with open(args.starters) as f:
        overrides = json.load(f)
    if not args.no_download:
        download(args.season, data_dir)
    done, todo, pbp = load(args.season, data_dir)

    rs = build_ratings(done, pbp, overrides, PARAMS)
    raw = raw_values(dropbacks(pbp))
    games = build_games(todo, rs, PARAMS)
    sim = simulate(done, games)
    payload = build_payload(args.season, done, todo, rs, raw, games, sim)
    for w in payload['warnings']:
        print(f"WARNING: {w}")

    previous = None
    if os.path.exists(args.out):
        try:
            with open(args.out) as f:
                previous = json.load(f)
        except ValueError as e:
            print(f"WARNING: existing {args.out} is unreadable ({e}); treating as no previous file")
    try:
        validate(payload, done, pbp, previous)
        changed = publish(payload, args.out, args.snapshots)
    except ValueError as e:
        print(f"FAILED: {e}", file=sys.stderr)
        return 1
    print(f"OK: through week {payload['through_week']}, {len(payload['games'])} games remaining, changed={changed}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
