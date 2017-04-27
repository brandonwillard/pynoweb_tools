import neovim
import os
from .pweave_objs.formatters import PwebMintedPandoc
from .utils import weave_retry_cache


def nvim_weave(outext="tex",
               docmode=True,
               pweb_shell="ipython_ext",
               rel_figdir="../../figures",
               rel_outdir="../tex",
               format_opts={'width': r'\linewidth'},
               formatter=PwebMintedPandoc):
    r''' Weave a file within the current neovim session.

    Parameters
    ==========
    outext: string
        Extension of output file.
    docmode: bool
        Enable docmode?
    rel_figdir: string
        Figure output directory relative to the cwd.
    rel_outdir: string
        Pweave file output directory relative to the cwd.

    Example
    =======

    In a noweb file, one can associate the following
    chunk to a vim map and it would run Pweave and, subsequently,
    a make objective on the current file to produce a pure tex
    and Markdown file:

        <<pweave_code, echo=False, evaluate=False>>=
        from pweave_ext.editor_utils import nvim_weave
        input_file_base = pweave_nvim_weave(rel_outdir="../tex")
        assert os.system('make {}.md'.format(input_file_base)) == 0
        @

    '''

    nvim = neovim.attach('socket', path=os.getenv("NVIM_LISTEN_ADDRESS"))
    currbuf = nvim.current.buffer

    from pweave import rcParams

    project_dir, input_file = os.path.split(currbuf.name)
    input_file_base, input_file_ext = os.path.splitext(input_file)
    output_filename = input_file_base + os.path.extsep + outext

    output_file = os.path.join(rel_outdir, output_filename)

    # TODO: Search for parent 'figures' (and 'output') dir by default.
    rcParams['figdir'] = os.path.abspath(os.path.join(
        project_dir, rel_figdir))

    rcParams['storeresults'] = docmode
    # rcParams['chunk']['defaultoptions']['engine'] = 'ipython'

    pweb_formatter = formatter(file=input_file,
                               format=outext,
                               shell=pweb_shell,
                               figdir=rcParams['figdir'],
                               output=output_file,
                               docmode=docmode)

    if format_opts is not None:
        pweb_formatter.updateformat(format_opts)

    # Catch cache issues and start fresh when they're found.
    weave_retry_cache(pweb_formatter)

    return input_file_base
