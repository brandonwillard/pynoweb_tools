from pweave import (PwebFormats, PwebProcessors)
from .processors import (PwebIPythonExtProcessor, JupyterAwareProcessor)
from .formatters import PwebMintedPandocFormatter


PwebFormats.formats.update(
    {
        'texmintedpandoc':
        {'class': PwebMintedPandocFormatter,
         'description':
         ('Minted code environments with Pandoc and Pelican '
          'figure output formatting.')
         }
    })

PwebProcessors.formats.update(
    {
        'ipython_ext':
        {'class': PwebIPythonExtProcessor,
         'description':
         ('IPython shell that uses an existing IPython instance.')
         },
        'jupyter_aware':
        {'class': JupyterAwareProcessor,
            'description':
            ('Jupyter kernel that checks for existing session instance.')
         }
    })
