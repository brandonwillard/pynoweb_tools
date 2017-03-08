import os
import glob


def weave_retry_cache(pweb_formatter):
    r''' Catch cache issues and start fresh when they're found.

    Parameters
    ==========
    pweb_formatter: Pweb
        Pweb formatter to be run.
    '''

    try:
        pweb_formatter.weave()
    except IndexError:
        input_file = pweb_formatter.source

        cache_dir = os.path.abspath(pweb_formatter.cachedir)
        input_file_base, input_file_ext = os.path.splitext(input_file)
        cache_glob = input_file_base + '*'
        cache_pattern = os.path.join(cache_dir, cache_glob)
        _ = map(os.unlink, glob.glob(cache_pattern))  # noqa
        pweb_formatter.weave()
