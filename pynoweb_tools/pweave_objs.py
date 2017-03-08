from pweave import (
    Pweb,
    PwebTexFormatter,
    PwebIPythonProcessor,
    PwebFormats,
    PwebProcessors)


class PwebMintedPandocFormatter(PwebTexFormatter):
    r""" Custom output format that handles figures for Pandoc and Pelican.

    TODO: Describe changes to figure handling.
    """
    def initformat(self):
        self.formatdict = dict(
            codestart=(r'\begin{minted}[mathescape, xleftmargin=0.5em]{%s}'),
            codeend='\end{minted}\n',
            outputstart=(r'\begin{minted}[xleftmargin=0.5em'
                         r', mathescape, frame = leftline]{text}'),
            outputend='\end{minted}\n',
            termstart=(r'\begin{minted}[xleftmargin=0.5em, '
                       r'mathescape]{%s}'),
            termend='\end{minted}\n',
            figfmt='.png',
            extension='tex',
            width='',
            doctype='tex')

    def formatfigure(self, chunk):
        fignames = chunk['figure']
        caption = chunk['caption']
        width = chunk['width']
        result = ""
        figstring = ""

        fig_root = chunk.get('fig_root', None)

        if chunk["f_env"] is not None:
            result += "\\begin{%s}\n" % chunk["f_env"]

        for fig in fignames:
            if width is not None and width != '':
                width_str = "[width={}]".format(width)
            else:
                width_str = ''
            if fig_root is not None and fig_root != '':
                import os
                fig = os.path.basename(fig)
                fig = os.path.join(fig_root, fig)

            figstring += ("\\includegraphics%s{%s}\n" % (width_str, fig))

        # Figure environment
        if chunk['caption']:
            result += ("\\begin{figure}[%s]\n"
                       "\\center\n"
                       "%s"
                       "\\caption{%s}\n" % (chunk['f_pos'],
                                            figstring, caption))
            if 'name' in chunk:
                result += "\label{fig:%s}\n" % chunk['name']
            result += "\\end{figure}\n"

        else:
            result += figstring

        if chunk["f_env"] is not None:
            result += "\\end{%s}\n" % chunk["f_env"]

        return result


class PwebIPythonExtProcessor(PwebIPythonProcessor):
    r""" A processor that runs code chunks in the current Ipython session.
    If there isn't one, then it creates one.

    TODO: This is rather old; the newer Jupyter processor might be sufficient?
    """

    def __init__(self, *args, **kwargs):
        super(PwebIPythonExtProcessor, self).__init__(*args, **kwargs)
        import IPython

        self.IPy = IPython.get_ipython()
        if self.IPy is None:
            x = IPython.core.interactiveshell.InteractiveShell()
            self.IPy = x.get_ipython()

        self.prompt_count = 1

    #def loadstring(self, code, **kwargs):
    #    tmp = StringIO()
    #    sys.stdout = tmp
    #    self.IPy.run_cell('%%cache code)
    #    result = "\n" + tmp.getvalue()
    #    tmp.close()
    #    sys.stdout = self._stdout
    #    return result


PwebProcessors.formats.update({'ipython_ext':
                               {'class': PwebIPythonExtProcessor,
                                'description':
                                ('IPython shell that uses'
                                 ' an existing IPython instance')
                                }})


class PwebMintedPandoc(Pweb):

    def __init__(self, *args, **kwargs):
        #self.destination = kwargs.get('output', None)
        #if self.destination is not None:
        #    self.destination = os.path.abspath(self.destination)
        docmode = kwargs.pop('docmode', None)

        super(PwebMintedPandoc, self).__init__(*args, **kwargs)

        self.formatter = PwebMintedPandocFormatter()
        #self.sink = os.path.join(self.output,
        #                         os.path.basename(self._basename()) + '.' +
        #                         self.formatter.getformatdict()['extension'])
        self.documentationmode = docmode

PwebFormats.formats.update({'pweb_minted_pandoc': {
    'class': PwebMintedPandocFormatter,
    'description': ('Minted environs with Pandoc and Pelican'
                    ' figure output considerations')}})
