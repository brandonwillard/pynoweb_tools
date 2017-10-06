from pweave import (PwebFormats, PwebProcessors)
from .formatters import (PwebMintedPandocFormatter, PwebMintedPandoc)


PwebFormats.formats.update(
    {
        'pweb_minted_pandoc':
        {'class': PwebMintedPandocFormatter,
         'description':
         ('Minted environs with Pandoc and Pelican figure output considerations.')
         }
    })
