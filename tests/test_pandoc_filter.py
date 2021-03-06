'''

The spawned pandoc processes can be debugged remotely with
something like the following:

    import remote_pdb; remote_pdb.RemotePdb('127.0.0.1', 4444).set_trace()


TODO FIXME: Rewrite all tests using calls like:

    import pypandoc
    pandoc_res = pypandoc.convert_text(source,
                                    to_format,
                                    format=from_format,
                                    extra_args=('-s', '-R'),
                                    filters=['PynowebFilter']
                                    )


'''
import os

import logging

import json
# import pytest

import pandocfilters
import pypandoc

import pynoweb_tools.pandoc_utils
from pynoweb_tools.pandoc_utils import latex_prefilter

# logging.basicConfig(level=logging.DEBUG)
logging.basicConfig(
    filename='test_pandoc_utils.log',
    filemode='w',
    level=logging.DEBUG)

# pandoc_logger = logging.getLogger('pandoc_utils')
# fh = logging.FileHandler('test_pandoc_utils.log')
# fh.setLevel(logging.DEBUG)
# pandoc_logger.addHandler(fh)


def debug_example():

    # pypandoc.__pandoc_path = '/home/bwillar0/.cabal/bin/pandoc'

    test_file = r'''
    \begin{document}
    %\graphicspath{{/tmp/bwillar0/}{../figures/}{./figures/}{./}}
    %\ref{fig:figure_with_label}

    \begin{figure}[htpb]
        %\center
        \includegraphics{figure_with_label.png}
        \caption{A figure caption!}
        \label{fig:figure_with_label}
    \end{figure}

    %\ref{fig:figure_with_label}

    \end{document}
    '''

    test_filename = '/home/bwillar0/projects/websites/brandonwillard.github.io/content/articles/src/more_proximal_estimation.tex'
    with open(test_filename, 'r') as f:
        test_file = ''.join(f.readlines())

    # For better filter debugging:
    json_res = pypandoc.convert_text(test_file,
                                     'json',
                                     format='latex',
                                     extra_args=('-s', '-R',
                                                 '--wrap=none',
                                                 '--metadata=bibliography=/home/bwillar0/projects/websites/brandonwillard.github.io/content/articles/src/more-proximal-estimation.bib'),
                                     filters=['pandoc-citeproc',
                                              'PynowebFilter'],
                                     )

    import json
    json_json_res = json.loads(json_res)

    # filter_res = json.dumps(json_json_res)

    # Apply our filter...
    # Make sure we clear out the global(s)...
    pynoweb_tools.pandoc_utils.processed_figures = dict()
    from pynoweb_tools.pandoc_utils import latex_prefilter
    filter_res = pandocfilters.applyJSONFilters(
        [latex_prefilter], json_res, format='json')

    filter_json_res = json.loads(filter_res)

    # Change some things...
    # Say we get a Pandoc error message with:
    #   $.blocks[47].c[1][0].c[1][0]
    problem_item = filter_json_res['blocks'][47]['c'][1][0]['c'][1][0]

    # problem_item['c'][0] = [u"pg_ls_plot", [], []]
    # problem_item['c'][1] = []
    # problem_item['c'][1] = [problem_item['c'][1]]

    # Hand-craft a test object...
    # from pandocfilters import (Math, Image, Div, RawInline, Span)
    # filter_json_res = {'blocks': [Para([Span(['blah', [], []], [Str('hi')])])],
    #                    'meta': {}, 'pandoc-api-version': [1, 17, 0, 5]}
    # filter_res = json.dumps(filter_json_res)

    html_res = pypandoc.convert_text(filter_res,
                                     'markdown_github+markdown_in_html_blocks+mmd_title_block+tex_math_dollars+tex_math_double_backslash+implicit_figures+citations+yaml_metadata_block+link_attributes+raw_html+raw_tex',
                                     format='json',
                                     extra_args=(
                                         '-s', '-R',
                                         '--wrap=none', '--verbose'
                                     )
                                     )

    print(html_res)

    # Old way:
    #   with open('test_file.tex', 'w') as f:
    #       f.write(test_file)
    #   !pandoc -s -R -f latex --verbose -t markdown --filter=PynowebFilter test_file.tex


def test_eqref():
    test_file_eqref = r'''
    \title{A title}
    \author{me}
    \date{2016-11-01}
    \begin{document}
        \maketitle

        \begin{equation}
        \label{eq1}
        hey
        \end{equation}

        \begin{Exa}
        \label{ex:prior_extension}
        \begin{equation}
            y_t
            \label{eq:endogenous_model}
        \end{equation}
        \end{Exa}
        \begin{Exa}
        \begin{equation}
            X_t \sim \operatorname{N}(d(t)^\top \beta, I \sigma_x^2)
            \label{eq:exogenous_model}
        \end{equation}
        \end{Exa}
        yo yo \eqref{eq1}
        $\alpha$
    \end{document}
    '''

    pandoc_res = pypandoc.convert_text(test_file_eqref,
                                       'markdown',
                                       format='latex',
                                       extra_args=('-s', '-R', '--wrap=none'),
                                       filters=['PynowebFilter']
                                       )

    # Make sure our equation references stay in there, and
    # get wrapped in mathjax delimiters.
    assert r'$\eqref{eq1}$' in pandoc_res

    eq_div = (r'<div id="eq:exogenous_model" class="example" '
              r'markdown="" env-number="2" title-name="">')

    # Make sure our custom environment gets converted to a div
    # with the correct class information, markdown attribute and
    # environment numbering.
    assert eq_div in pandoc_res

    eq_ref_hack_1 = (r'<div id="eq:exogenous_model_math" '
                     r'style="display:none;visibility:hidden">')
    eq_ref_hack_2 = (r'$$\begin{equation}\tag{2}'
                     r'\label{eq:exogenous_model}'
                     r'\end{equation}$$')

    # Make sure our weird little Mathjax equation referencing
    # hijack hack works for environments.
    assert eq_ref_hack_1 in pandoc_res\
        and eq_ref_hack_2 in pandoc_res


def test_fig():
    from tempfile import NamedTemporaryFile
    tfig_file = NamedTemporaryFile()

    test_file_fig = r'''
    \begin{document}
    \graphicspath{{/tmp/bwillar0/}{../figures/}{./figures/}{./}}

    \ref{fig:figure_with_label}

    \begin{figure}[htpb]
        \center
        \includegraphics[width=\linewidth]{figure_with_label.png}
        \caption{A figure caption!}
        \label{fig:figure_with_label}
    \end{figure}

    \ref{fig:figure_with_label}

    \begin{figure}
        \centering
        {\includegraphics[width=2.5in]{figure_without_label.png}}
        \caption{Another figure caption!}
    \end{figure}
    '''
    test_file_fig += r'''
    \begin{{figure}}
        \includegraphics{{{}}}
    \end{{figure}}
    \end{{document}}
    '''.format(os.path.split(tfig_file.name)[-1])

    # print(test_file_fig)

    extra_args = ('-s', '-R', '--wrap=none', '--verbose', '--trace')
    # metadata = r'figure_dir=/tmp/figures'
    metadata = r'figure_dir={attach}/articles/figures/'
    extra_args += (r'--metadata={}'.format(metadata),)

    md_exts = ['+implicit_figures',
               '+link_attributes',
               '+markdown_in_html_blocks'
               ]
    pandoc_res = pypandoc.convert_text(test_file_fig,
                                       'markdown' + ''.join(md_exts),
                                       format='latex',
                                       extra_args=extra_args,
                                       filters=['PynowebFilter']
                                       )

    figure_str = (r'![A figure caption!<span data-label='
                  r'"fig:figure_with_label"></span>]'
                  r'(figure_with_label "fig:")')
    # Make sure our figures
    assert figure_str in pandoc_res

    # Make sure it finds and uses the path for our tempfile figure.
    assert r'![image](/tmp/bwillar0/tmpy6udajxi)' in pandoc_res


def test_nested_envir():
    test_file_exa = r'''
    \title{A Title}
    \author{Me}
    \begin{document}
    \textit{some text}
    \begin{Exa}
        Blah, blah, blah
        \textit{some more text}
        \label{ex:some_example}
    \end{Exa}
    \begin{Exa}
        Blahhhhhhhhhhh
        \textit{blohhhhhhh}
        \label{ex:some_example_2}
    \end{Exa}

    Example~\ref{ex:some_example} is blah.
    Example~\ref{ex:some_example_2} is blah.
    \end{document}
    '''
    # Without the `markdown_in_html_blocks` option, `markdown_github`
    # format will throw away our custom div environments.
    # pandoc_res = pypandoc.convert_text(test_file_exa,
    #                                    'markdown_github+yaml_metadata_block',
    #                                    format='latex',
    #                                    extra_args=('-s', '-R', '--wrap=none'),
    #                                    filters=['PynowebFilter']
    #                                    )
    pandoc_res = pypandoc.convert_text(test_file_exa,
                                       'markdown_github+markdown_in_html_blocks',
                                       format='latex',
                                       extra_args=('-s', '-R', '--wrap=none'),
                                       filters=['PynowebFilter']
                                       )
    # print(pandoc_res)

    # Make sure our div environments made it into the output.
    div_env_str = (r'<div id="ex:some_example" class="example"'
                   r' markdown="" env-number="1" title-name="">')
    assert div_env_str in pandoc_res

    # Make sure nested markdown was actually processed.
    div_nested_md_str = r'Blah, blah, blah *some more text*'
    assert div_nested_md_str in pandoc_res


def test_nested_envir_2():
    test_file_exa = r'''
    \begin{document}

    \begin{lemma}
        \label{lem:a_lemma}
        \begin{equation}
            1 = 1
        \end{equation}
        \begin{proof}
            Obviously true!
        \end{proof}
    \end{lemma}

    \begin{remark}
        \label{rem:a_remark}
        The property in \Cref{lem:a_lemma} can used with other\dots
    \end{remark}

    \end{document}
    '''
    json_res = pypandoc.convert_text(test_file_exa,
                                     # 'markdown_github+markdown_in_html_blocks',
                                     'json',
                                     format='latex',
                                     extra_args=('-s', '-R', '--wrap=none'),
                                     )
    # json_json_res = json.loads(json_res)

    pynoweb_tools.pandoc_utils.processed_figures = dict()

    filter_res = pandocfilters.applyJSONFilters(
        [latex_prefilter], json_res, format='json')

    # filter_json_res = json.loads(filter_res)

    pandoc_res = pypandoc.convert_text(filter_res,
                                       'markdown_github+markdown_in_html_blocks',
                                       format='json',
                                       extra_args=('-s', '-R', '--wrap=none'),
                                       )

    # print(pandoc_res)

    # Make sure our nested div environments made it into the output.
    div_env_str = (r'<div class="proof" markdown="" env-number="1"'
                   r' title-name="">')
    assert div_env_str in pandoc_res

    # Make sure our nested lemma reference made it in.
    div_lemma_str = r'Lemma $\\eqref{lem:a\_lemma}$ '
    assert div_lemma_str in pandoc_res


def test_citations():
    test_bib_file = r'''
    @inproceedings{willard_title_2017,
        title = {Title},
        author = {Willard, Brandon T.},
        date = {2017}
    }
    '''
    with open('/tmp/test-refs.bib', 'w') as f:
        f.write(test_bib_file)

    test_file_cite = r'''
    \usepackage[authoryear]{natbib}

    \title{A Title}
    \author{Me}
    \date{2017-1-1}

    \begin{document}
        \cite{willard_title_2017}
        \citep{willard_title_2017}
        \autocite{willard_title_2017}

        \bibliographystyle{plainnat}
        \bibliography{test-refs}
    \end{document}
    '''

    pandoc_res = pypandoc.convert_text(test_file_cite,
                                       'markdown_github',
                                       format='latex',
                                       extra_args=('-s', '-R',
                                                   '--wrap=none',
                                                   '--bibliography=/tmp/test-refs.bib'),
                                       filters=['PynowebFilter',
                                                'pandoc-citeproc']
                                       )
    # print(pandoc_res)

    cites_str = r'(Willard 2017) (Willard 2017) (Willard 2017)'

    # Make sure our citation commands are honored.
    assert cites_str in pandoc_res

    refs_str = r'Willard, Brandon T. 2017. “Title.” In.'

    # Make sure our references are actually printed in the document.
    assert refs_str in pandoc_res
