from pweave import Pweb, PwebTexFormatter


class PwebMintedPandocFormatter(PwebTexFormatter):
    r""" Custom output format that handles figures for Pandoc and Pelican.

    TODO: Describe changes to figure handling.
    """
    def __init__(self, *args, **kwargs):
        self.after_code_newline = kwargs.pop('after_code_newline', True)
        self.after_output_newline = kwargs.pop('after_output_newline', False)
        self.after_term_newline = kwargs.pop('after_term_newline', True)

        self.minted_code_chunk_options = kwargs.pop(
            'minted_code_chunk_options', 'xleftmargin=0.5em')
        self.minted_output_chunk_options = kwargs.pop(
            'minted_code_chunk_options',
            'xleftmargin=0.5em,frame=leftline')
        self.minted_term_chunk_options = kwargs.pop(
            'minted_code_chunk_options',
            'xleftmargin=0.5em')

        self.minted_output_id = kwargs.pop('minted_output_id', 'text')
        super(PwebMintedPandocFormatter, self).__init__(*args, **kwargs)

    def initformat(self):
        self.formatdict = dict(
            codestart=(r'\begin{{minted}}[{}]{{%s}}'.format(
                self.minted_code_chunk_options)),
            codeend=r'\end{minted}' + (
                '\n' if self.after_code_newline else ''),
            outputstart=(r'\begin{{minted}}[{}]{{{}}}'.format(
                self.minted_output_chunk_options, self.minted_output_id)),
            outputend=r'\end{minted}' + (
                '\n' if self.after_output_newline else ''),
            termstart=(r'\begin{{minted}}[{}]{{%s}}'.format(
                self.minted_term_chunk_options)),
            termend=r'\end{minted}' + (
                '\n' if self.after_term_newline else ''),
            figfmt='.png',
            extension='tex',
            width=r'\textwidth',
            doctype='tex')

    def formatfigure(self, chunk):
        fignames = chunk['figure']
        caption = chunk['caption']
        width = chunk.get('width',
                          self.formatdict.get('width'))
        result = ""
        figstring = ""

        fig_root = chunk.get('fig_root', None)
        # TODO: Get rid of `width`; no longer needed.
        graphics_opts = chunk.get('graphics_opts', '')

        if chunk["f_env"] is not None:
            result += "\\begin{%s}\n" % chunk["f_env"]

        for fig in fignames:
            opts_str = ''
            if width != '':
                opts_str = "width={}".format(width)

            if graphics_opts != '':
                opts_str += ',' + graphics_opts

            opts_str = opts_str.replace(' ', '')

            if opts_str != '':
                opts_str = "[{}]".format(opts_str)

            if fig_root is not None and fig_root != '':
                import os
                fig = os.path.basename(fig)
                fig = os.path.join(fig_root, fig)

            figstring += ("\\includegraphics%s{%s}\n" % (opts_str, fig))

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


class PwebMintedPandoc(Pweb):

    def __init__(self, *args, **kwargs):
        # docmode = kwargs.pop('docmode', None)

        super(PwebMintedPandoc, self).__init__(*args, **kwargs)

        self.formatter = PwebMintedPandocFormatter()
        #self.sink = os.path.join(self.output,
        #                         os.path.basename(self._basename()) + '.' +
        #                         self.formatter.getformatdict()['extension'])
        # self.documentationmode = docmode
