"""Command line: download data, build the model, validate and write the weekly projections JSON."""
import argparse
import json
import os
import sys
import tempfile

from .constants import PARAMS
from .data import download, load
from .output import apply_starter_corrections, build_completed, build_games, build_payload, has_later_results, publish, validate
from .ratings import build_ratings, dropbacks, raw_values
from .simulate import simulate


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog='python3 -m projections.run')
    ap.add_argument('--season', type=int, required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--snapshots', required=True)
    ap.add_argument('--starters', required=True, help='JSON file mapping team code to starting QB')
    ap.add_argument('--corrections', default=None,
                    help='JSON file of starter corrections for completed games, {game_id: {"starters": {team: QB}, "note": str}}')
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

    previous = None
    if os.path.exists(args.out):
        try:
            with open(args.out) as f:
                previous = json.load(f)
        except ValueError as e:
            print(f"WARNING: existing {args.out} is unreadable ({e}); treating as no previous file")

    rs = build_ratings(done, pbp, overrides, PARAMS)
    raw = raw_values(dropbacks(pbp))
    games = build_games(todo, rs, PARAMS)
    sim = simulate(done, games)
    completed = build_completed(args.season, done, pbp, previous, args.snapshots, PARAMS)
    corrections = {}
    if args.corrections:
        with open(args.corrections) as f:
            corrections = json.load(f)
    for msg in apply_starter_corrections(completed, done, pbp, corrections, PARAMS):
        print(f"WARNING: {msg}")
    payload = build_payload(args.season, done, todo, rs, raw, games, sim, completed=completed)
    for w in payload['warnings']:
        print(f"WARNING: {w}")

    try:
        validate(payload, done, pbp, previous)
        changed = publish(payload, args.out, args.snapshots,
                          locked=has_later_results(done, payload['through_week']))
    except ValueError as e:
        print(f"FAILED: {e}", file=sys.stderr)
        return 1
    print(f"OK: through week {payload['through_week']}, {len(payload['games'])} games remaining, "
          f"{len(completed)} completed, changed={changed}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
