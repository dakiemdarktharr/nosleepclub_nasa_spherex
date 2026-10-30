"""Guard completed phase artifacts while retaining safe partial-field resume."""
import argparse
from . import ablation_study as study

COMPLETION={'design':['design.json'],'develop':['selection.json','development-summary.json'],
    'calibrate':['calibrator.json','calibration-summary.json'],'seal':['validation-protocol.json'],
    'validate':['validation-summary.json']}


def guard(phase,folder):
    existing=[name for name in COMPLETION[phase] if (folder/name).exists()]
    if existing:raise RuntimeError('Completed/locked artifacts already exist: '+', '.join(existing)+'. Do not overwrite opened science products.')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=list(COMPLETION));args=parser.parse_args()
    guard(args.phase,study.OUT);study.OUT.mkdir(parents=True,exist_ok=True)
    if args.phase=='design':study.design()
    elif args.phase=='seal':study.seal()
    else:study.run({'develop':'development','calibrate':'calibration','validate':'validation'}[args.phase])


if __name__=='__main__':main()
