import sys
from optparse import OptionParser

from pweave import rcParams

from pandocfilters import toJSONFilter

from .pweave_objs.formatters import PwebMintedPandoc
from .utils import weave_retry_cache
from .pandoc_utils import latex_prefilter


def weave():
    r""" This provides a callable script that mimics the `Pweave` command but
    uses our specially purposed Pandoc formatter and cache retry wrapper.

    TODO: Much of this isn't needed anymore, so refactor.  Especially
    since the retry stuff should just be in a `Pweave.Processor`.
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
    parser.add_option("-s", "--shell",
                      dest="shell",
                      default="ipython_ext",
                      help="Shell in which to process python")

    (options, args) = parser.parse_args()

    try:
        infile = args[0]
    except IndexError:
        infile = ""

    opts_dict = vars(options)

    # set some global options
    rcParams['figdir'] = opts_dict.pop('figdir', None)
    rcParams['storeresults'] = opts_dict.pop('cache', None)
    rcParams["chunk"]["defaultoptions"].update({'wrap' : False})
    # rcParams['chunk']['defaultoptions']['engine'] = 'ipython'
    shell_opt = opts_dict.pop('shell')

    pweb_formatter = PwebMintedPandoc(infile,
                                      format="tex",
                                      shell=shell_opt,
                                      figdir=rcParams['figdir'],
                                      output=opts_dict.pop('output', None),
                                      docmode=opts_dict.pop('docmode', None))

    weave_retry_cache(pweb_formatter)


def latex_json_filter():
    r""" A Pandoc filter for additional and custom LaTeX processing
    functionality.

    .. see: pandoc_utils.latex_prefilter
    """
    toJSONFilter(latex_prefilter)
