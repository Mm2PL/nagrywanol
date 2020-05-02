import os
import argparse

import pydub.silence

# noinspection PyUnresolvedReferences
from .util import debug_log, safe_name


def split(input_: pydub.AudioSegment, export_directory: str, min_silence_len: int, silence_thresh: float,
          input_name: str) -> None:
    input_name = safe_name(input_name)
    debug_log('spl')
    chunks = pydub.silence.split_on_silence(
        input_,
        min_silence_len=min_silence_len,
        silence_thresh=silence_thresh
    )
    debug_log('spl po')

    for i, chunk in enumerate(chunks):
        debug_log(f'{i} {chunk}')
        silence_chunk = pydub.AudioSegment.silent(duration=500)

        audio_chunk = silence_chunk + chunk + silence_chunk

        normalized_chunk = normalize(audio_chunk, -20.0)

        e_path = os.path.join(export_directory, f'{input_name}_{i}.wav')
        print(f"Eksportownie dźwięku do {e_path}")
        normalized_chunk.export(
            e_path,
            format="wav"
        )


def normalize(chk, target_dbfs):
    change_in_dbfs = target_dbfs - chk.dBFS
    return chk.apply_gain(change_in_dbfs)


class Args:
    input: str
    output: str
    silence_threshold: float
    min_silence_len: int


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('input')
    p.add_argument('output')
    p.add_argument('-t', '--silence-threshold', dest='silence_threshold', type=float, default=-30,
                   help='Próg ciszy, domyślnie -30db')
    p.add_argument('-m', '--min-silence-length', dest='min_silence_len', type=int, default=1_000,
                   help='Wymagana długość ciszy w milisekundach, domyślnie 1 000ms')
    args = p.parse_args(namespace=Args())
    try:
        os.mkdir(args.output)
    except FileExistsError:
        pass
    print(f'Ładowanie pliku: {args.input}')
    song = pydub.AudioSegment.from_wav(args.input)
    print(f'Załadowano plik')
    split(song, args.output, args.min_silence_len, args.silence_threshold, args.input)
