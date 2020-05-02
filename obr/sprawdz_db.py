import argparse
import sys

import pydub


class Args:
    input: str


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('input')
    args = p.parse_args(namespace=Args())
    print(f'Ładowanie pliku: {args.input}', file=sys.stderr)
    inp = pydub.AudioSegment.from_wav(args.input)
    print(f'Załadowano plik', file=sys.stderr)
    print(round(inp.dBFS, 3))
