#!/usr/bin/env python3
"""Install the bundled skill locally, without network or lifecycle hooks."""
import argparse
from pathlib import Path
import os
import shutil

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--dest',type=Path,help='Skills root; default $CODEX_HOME/skills or ~/.codex/skills')
args=parser.parse_args()
base=args.dest or Path(os.environ.get('CODEX_HOME',str(Path.home()/'.codex')))/'skills'
name='cad-cabinet-white-model'
source=Path(__file__).resolve().parent/'skills'/name
destination=base/name
if destination.exists():
    raise SystemExit(f'Already exists; not overwritten: {destination}')
shutil.copytree(source,destination,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
print(f'Installed {name} to {destination}. Available on your next Codex turn.')
