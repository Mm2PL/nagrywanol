import os
DEBUG = False


def debug_log(text: str):
    if DEBUG:
        print('[debug]', text)
    else:
        return


def safe_name(text: str):
    return os.path.basename(text).replace('.wav', '')
