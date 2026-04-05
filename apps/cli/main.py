import argparse
from .commands import seed_templates

parser = argparse.ArgumentParser(description='CLI for Conversational CV Builder')
parser.add_argument('--seed', action='store_true', help='Seed templates')

if __name__ == '__main__':
    args = parser.parse_args()
    if args.seed:
        seed_templates.run()
