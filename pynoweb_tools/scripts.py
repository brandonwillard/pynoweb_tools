import sys
import os
from optparse import OptionParser

import pweave
from pweave import rcParams

from pandocfilters import toJSONFilter

from .pweave_objs.formatters import PwebMintedPandocFormatter
from .utils import weave_retry_cache
from .pandoc_utils import latex_prefilter


def weave():
    r""" This provides a callable script that mimics the `Pweave` command but
    uses our specially purposed Pandoc formatter and cache retry wrapper.

    TODO: Much of this isn't needed anymore, so refactor.  Especially
    since the retry stuff should just be in a `Pweave.Processor`.

    Could we use `os.execvp('Pweave', ['Pweave'] + opts)`?

    """

    if len(sys.argv) == 1:
        print("Enter PynowebWeave -h for help")
        sys.exit()

    parser = OptionParser(usage="PynowebWeave [options] sourcefile")
    parser.add_option("-d", "--documentation-mode",
                      dest="docmode",
                      action="store_true",
                      default=False,
                      help=("Use documentation mode, chunk code and results"
                            " will be loaded from cache and inline code will"
                            " be hidden"))
    parser.add_option("-c", "--cache-results",
                      dest="cache", action="store_true",
                      default=False,
                      help="Cache results to disk for documentation mode")
    parser.add_option("-F", "--figure-directory",
                      dest="figdir",
                      default='figures',
                      help=("Directory path for matplolib graphics: "
                            "Default 'figures'"))
    parser.add_option("-o", "--output-file",
                      dest="output",
                      default=None,
                      help="Path and filename for output file")
    parser.add_option("-k", "--kernel",
                      dest="kernel",
                      default="python3",
                      help="Jupyter kernel in which to process code")

    (options, args) = parser.parse_args()

    try:
        infile = args[0]
    except IndexError:
        infile = ""

    opts_dict = vars(options)

    # set some global options
    rcParams['figdir'] = opts_dict.pop('figdir', None)
    rcParams['storeresults'] = opts_dict.pop('cache', None)
    rcParams["chunk"]["defaultoptions"].update({'wrap': False})

    weave_kernel = opts_dict.pop('kernel')

    # pweb_formatter = PwebMintedPandoc(infile,
    #                                   format="tex",
    #                                   shell=shell_opt,
    #                                   figdir=rcParams['figdir'],
    #                                   output=opts_dict.pop('output', None),
    #                                   docmode=opts_dict.pop('docmode', None))

    out_file = opts_dict.pop('output', None)
    out_dir, out_filename = os.path.split(out_file)
    _, out_filename_ext = os.path.splitext(out_filename)

    weaver = pweave.Pweb(infile,
                         doctype=out_filename_ext[1:],
                         kernel=weave_kernel,
                         # XXX: Pydoc is super confusing; this
                         # should be the output dir and filename.
                         output=out_file,
                         figdir=rcParams['figdir'])

    weaver.documentationmode = opts_dict.pop('docmode', None)

    weaver.setformat(Formatter=PwebMintedPandocFormatter)

    # if weave_format_opts is not None:
    #     weaver.updateformat(weave_format_opts)

    weave_retry_cache(weaver)


def latex_json_filter():
    r""" A Pandoc filter for additional and custom LaTeX processing
    functionality.

    .. see: pandoc_utils.latex_prefilter
    """
    toJSONFilter(latex_prefilter)
