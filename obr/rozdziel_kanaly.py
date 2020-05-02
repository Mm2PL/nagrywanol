import argparse
import os
import sys

import pydub

from util import safe_name, debug_log


class Args:
    input: str
    output: str


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('input')
    p.add_argument('output')
    args = p.parse_args(namespace=Args())
    try:
        os.mkdir(args.output)
    except FileExistsError:
        pass
    print(f'Ładowanie pliku: {args.input}', file=sys.stderr)
    inp = pydub.AudioSegment.from_wav(args.input)
    print(f'Załadowano plik', file=sys.stderr)
    channels = inp.split_to_mono()
    n = safe_name(args.input)
    for i, ch in enumerate(channels):
        debug_log(f'{i} {ch}')
        e_path = os.path.join(args.output, f'{n}_{i}.wav')
        print(f"Eksportownie dźwięku do {e_path}")
        ch.export(
            e_path,
            format="wav"
        )
