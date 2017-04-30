import re
import os
from copy import copy

import logging

import json
from functools import reduce

import pypandoc

# See https://hackage.haskell.org/package/pandoc-1.17.2
# and https://hackage.haskell.org/package/pandoc-types-1.16.1.1 for
# definitions.
# Or simply `cabal get pandoc-types -d /tmp` and look at the source.
from pandocfilters import (applyJSONFilters, Str, Math, Image, Div,
                           RawInline, Span, Para)

pandoc_logger = logging.getLogger('pandoc_utils')
pandoc_logger.addHandler(logging.NullHandler())

gpath_pattern_1 = r'\\graphicspath\{(.+)\}'
gpath_pattern_1 = re.compile(gpath_pattern_1)
gpath_pattern_2 = r'([^\{\}]+)+'
gpath_pattern_2 = re.compile(gpath_pattern_2)

graphics_pattern = re.compile(r'\\includegraphics(?:\[.+\])?\{(.*?)\}')

image_pattern = re.compile(r"(.*?)")

env_pattern = re.compile(
    r'\\begin\{(\w+)\}(\[.+\])?(.*)\\end\{\1\}', re.S)

label_pattern = re.compile(r'(\s*?\\label\{(\w*?:?\w+)\})')

env_conversions = {'Exa': 'example'}

environment_counters = {}

preserved_tex = ['\\eqref', '\\ref', '\\Cref', '\\cref', '\\includegraphics']

cleveref_dict = {r'fig:': (r'Figure~', ''),
                 r'eq:': (r'Equation~', r'eq'),
                 r'thm:': (r'Theorem~', r'eq'),
                 r'cor:': (r'Corollary~', r'eq'),
                 r'lem:': (r'Lemma~', r'eq'),
                 r'prop:': (r'Proposition~', ''),
                 r'exa:': (r'Example~', ''),
                 r'ex:': (r'Example~', ''),
                 r'sec:': (r'Section~', ''),
                 r'rem:': (r'Remark~', ''),
                 r'que:': (r'Question~', ''),
                 }

cleveref_re = re.compile(
    r'\\[Cc]ref{{\s*({})?'.format('|'.join(cleveref_dict.keys())))


def cleveref_sub(ma):
    key, = ma.groups()
    if key is None:
        key = ''
    prefix, ref_prefix = cleveref_dict.get(key, ('', ''))

    return r'{}\{}ref{{{}'.format(prefix, ref_prefix, key)


def cleveref_ast_sub(source):
    res = []
    sub_res = cleveref_re.sub(cleveref_sub, source)
    try:
        prefix_str, ref_str = sub_res.split('~')
        res += [Str(prefix_str + u'\xa0')]
    except:
        ref_str = sub_res

    res += [Math({'t': 'InlineMath', 'c': []}, ref_str)]
    return res


r""" Dictionary of custom inline math elements to preserve.

Elements with callable values must consist of functions that
take the string to convert, elements with with string values
(all keys should be strings, too) will call `str.replace`
with key and value as arguments.
In the former case, the return result must be a list of Pandoc
AST objects.
"""
custom_inline_math = {'cleveref': cleveref_ast_sub}

r""" Figure directories to search.

These are a combination of the meta data values and any
processed LaTeX `\graphicspath` directives.
"""
figure_dirs = set()

r""" Dictionary of processed AST Image objects.

The keys are the replaced/updated image filenames, the values
are lists with two elements: a string LaTeX label for the image,
and the figure number.
"""
processed_figures = dict()

r""" Figure filename extensions.
"""
fig_fname_ext = None


def rename_find_fig(fig_name,
                    fig_dirs='',
                    fig_ext=None):
    r''' Renames a figure (file, really), tries a list of extensions
    (or a single one) and looks for the one that exists (or uses
    the single one, regardless).
    '''

    fig_fname = os.path.split(fig_name)[-1]
    fig_fname_base = os.path.splitext(fig_fname)[0]
    new_fig_fname = fig_fname_base
    if fig_ext is not None:
        new_fig_fname = os.path.extsep.join([new_fig_fname,
                                             fig_ext])

    # XXX: We assume that `fig_dirs` is a collection.
    # See if we can find the file in one of the dirs.
    # Otherwise, if there's only one item in the collection,
    # use that (i.e. no check).
    if len(fig_dirs) == 1:
        fig_dir, = fig_dirs
        new_fig_fname = os.path.join(fig_dir, new_fig_fname)
    else:
        fig_files = map(lambda x: os.path.join(x, new_fig_fname),
                        fig_dirs)
        real_fig_files = filter(os.path.exists, fig_files)
        new_fig_fname = next(iter(real_fig_files), new_fig_fname)

    return new_fig_fname


def label_to_mathjax(env_label, label_postfix='_span', env_tag=None):
    r""" Replace labels with MathJax-based hack that
    preserves LaTeX-like functionality and rendering.

    This works by creating a hidden Span with a labeled dummy
    MathJax equation environment.  References like `\ref{env_label}`
    will then automatically resolve to the containing Div.

    Arguments
    =========
    env_label: str
        The label token (i.e. `\label{env_label}`).
    label_postfix: str (Optional)
        String to append to the generated Span's id
        (env_label + label_postfix).
    env_tag: int (Optional)
        Tag for the labeled content (e.g. equation number).

    Returns
    =======
    The Para(Span) AST object that links to our label (i.e.
    the new MathJax "label" object).
    """
    hack_span_id = env_label + label_postfix

    # This is how we're hijacking MathJax's numbering system:
    ref_hack = r'$$\begin{equation}'
    if env_tag is not None:
        ref_hack += r'\tag{{{}}}'.format(env_tag)
    ref_hack += r'\label{{{}}}'.format(env_label)
    ref_hack += r'\end{equation}$$'

    # Hide the display of our equation hack in a Span:
    label_div = Span([hack_span_id, [],
                      [["style", "display:none;visibility:hidden"]]
                      ],
                     [RawInline('latex', ref_hack)])

    return label_div


def process_image(key, value, oformat, meta):
    r''' Rewrite filename in Image AST object--adding paths from the
    meta information and/or LaTeX `\graphicspaths` directive.

    This can be used to reassign paths to image file names when the
    meta information has only one entry.  It will also wrap
    LaTeX-labeled Image objects in a Span--for later
    referencing/linking, say.
    '''
    if key != "Image":
        return None

    global figure_dirs, fig_fname_ext, processed_figures

    # TODO: Find and use labels.
    # TODO: Perhaps check that it's a valid file?
    new_value = copy(value[2])

    new_fig_fname = rename_find_fig(new_value[0],
                                    figure_dirs,
                                    fig_fname_ext)

    pandoc_logger.debug("figure_dirs: {}\tfig_fname_ext: {}\n".format(
        figure_dirs, fig_fname_ext))
    pandoc_logger.debug("new_value: {}\tnew_fig_fname: {}\n".format(
        new_value, new_fig_fname))

    # XXX: Avoid an endless loop of Image replacements.
    if new_fig_fname in processed_figures.keys():
        return None

    processed_figures[new_fig_fname] = [None, None]

    new_value[0] = new_fig_fname

    # Wrap the image in a div with an `id`, so that we can
    # reference it in HTML.
    new_image = Image(value[0], value[1], new_value)
    wrapped_image = new_image
    try:
        fig_label_obj = value[1][-1]['c'][0][-1][0]

        pandoc_logger.debug("fig_label_obj: {}\n".format(fig_label_obj))

        if fig_label_obj[0] == 'data-label':
            fig_label = fig_label_obj[1]

            processed_figures[new_fig_fname][0] = fig_label
            env_num = len(processed_figures)
            processed_figures[new_fig_fname][1] = env_num

            hack_span = label_to_mathjax(fig_label, env_tag=env_num)

            wrapped_image = Span([copy(fig_label), [], []],
                                 [hack_span, new_image])
    except:
        pass

    pandoc_logger.debug("wrapped_image: {}\n".format(wrapped_image))

    return [wrapped_image]


def process_latex_envs(key, value, oformat, meta):
    r''' Check LaTeX RawBlock AST objects for environments (i.e.
    `\begin{env_name}` and `\end{env_name}`) and converts
    them to Div's with class attribute set to their LaTeX names
    (i.e. `env_name`).

    The new Div has a `markdown` attribute set so that its contents
    can be processed again by Pandoc.  This is needed for custom environments
    (e.g. and example environment with more text and math to be processed),
    which also means that *recursive Pandoc calls are needed* (since Pandoc
    already stopped short producing the RawBlocks we start with).
    For the recursive Pandoc calls to work, we need the Pandoc extension
    `+markdown_in_html_blocks` enabled, as well.
    '''

    if key != 'RawBlock' or value[0] != 'latex':
        return None

    global environment_counters

    env_info = env_pattern.search(value[1])
    if env_info is not None:
        env_groups = env_info.groups()
        env_name = env_groups[0]
        env_name = env_conversions.get(env_name, env_name)
        env_title = env_groups[1]

        if env_title is None:
            env_title = ""

        env_body = env_groups[2]

        env_num = environment_counters.get(env_name, 0)
        env_num += 1
        environment_counters[env_name] = env_num

        label_info = label_pattern.search(env_body)
        env_label = ""
        label_div = None
        if label_info is not None:
            env_label = label_info.group(2)
            label_div = label_to_mathjax(env_label, env_tag=env_num)

            # XXX: For the Pandoc-types we've been using, there's
            # a strict need to make Div values Block elements and not
            # Inlines, which Span is.  We wrap the Span in Para to
            # produce the requisite Block value.
            label_div = Para([label_div])

            # Now, remove the latex label string from the original
            # content:
            env_body = env_body.replace(label_info.group(1), '')

        # Div AST objects:
        # type Attr = (String, [String], [(String, String)])
        # Attributes: identifier, classes, key-value pairs
        div_attr = [env_label, [env_name], [['markdown', ''],
                                            ["env-number", str(env_num)],
                                            ['title-name', env_title]
                                            ]]

        pandoc_logger.debug(u"env_body (pre-processed): {}\n".format(
            str(env_body)))

        # XXX: Nested processing!
        env_body_proc = pypandoc.convert_text(env_body, 'json',
                                              format='latex',
                                              extra_args=(
                                                  '-s', '-R',
                                                  '--wrap=none'),
                                              )

        pandoc_logger.debug(u"env_body (pandoc processed): {}\n".format(
            env_body_proc))

        env_body_filt = applyJSONFilters(
            [latex_prefilter], env_body_proc, format='json')

        div_blocks = json.loads(env_body_filt)['blocks']

        if label_div is not None:
            div_blocks = [label_div] + div_blocks

        div_res = Div(div_attr, div_blocks)

        pandoc_logger.debug("div_res: {}\n".format(div_res))

        return div_res
    else:
        return []


def latex_prefilter(key, value, oformat, meta, *args, **kwargs):
    r""" A prefilter that adds more latex capabilities to Pandoc's tex to
    markdown features.

    Currently implemented:
        * Keeps unmatched `\eqref` (drops the rest)
        * Wraps equation blocks with `equation[*]` environment depending on
          whether or not their body contains a `\label`
        * Converts custom environments to div objects

    Set the variables `preserved_tex` and `env_conversions` to
    allow more raw latex commands and to convert latex environment names
    to CSS class names, respectively.

    # TODO: Describe more.

    # XXX: This filter does some questionable recursive calling at the
    # shell level.

    Parameters
    ==========
    TODO: Document parameters.

    """
    pandoc_logger.debug((u"Filter key:{}, value:{}, meta:{},"
                   "args:{}, kwargs:{}\n").format(
                       key, value, meta, args, kwargs))

    global custom_inline_math, preserved_tex,\
        env_conversions, figure_dirs, fig_fname_ext

    custom_inline_math = custom_inline_math.copy()
    custom_inline_math.update(meta.get(
        'custom_inline_math', {}).get('c', {}))

    env_conversions = env_conversions.copy()
    env_conversions.update(meta.get(
        'env_conversions', {}).get('c', {}))

    preserved_tex += meta.get('preserved_tex', {}).get('c', [])

    figure_dir_meta = meta.get('figure_dir', {}).get('c', None)
    if figure_dir_meta is not None:
        figure_dirs.add(figure_dir_meta)

    fig_fname_ext = meta.get('figure_ext', {}).get('c', None)

    if key == 'RawInline' and value[0] == 'latex':
        if any(c_ in value[1] for c_ in preserved_tex):
            # Check for `\includegraphics` commands and their
            # corresponding files.
            new_value = copy(value[1])
            figure_files = graphics_pattern.findall(new_value)

            def repstep(x, y):
                new_y = rename_find_fig(y, figure_dirs, fig_fname_ext)
                return x.replace(y, new_y)

            new_value = reduce(repstep, figure_files, new_value)

            pandoc_logger.debug("figure_files: {}\tnew_value: {}\n".format(
                figure_files, new_value))

            for from_, to_ in custom_inline_math.items():
                if callable(to_):
                    new_value = to_(new_value)
                else:
                    new_value = new_value.replace(from_, to_)
                    new_value = [Math({'t': 'InlineMath', 'c': []},
                                      new_value)]

            return new_value
        else:
            # Check for `\graphicspaths` commands to parse for
            # new paths.
            gpaths_matches = gpath_pattern_1.search(value[1])
            if gpaths_matches is not None:
                for gpaths in gpaths_matches.groups():
                    gpaths = gpath_pattern_2.findall(gpaths)
                    figure_dirs.update(gpaths)

            # Do not include `\graphicspath` in output.
            return []

    elif key == "Image":

        return process_image(key, value, oformat, meta)

    elif key == "Math" and value[0]['t'] == "DisplayMath":

        star = '*'
        if '\\label' in value[1]:
            star = ''
        wrapped_value = ("\\begin{{equation{}}}\n"
                         "{}\n"
                         "\\end{{equation{}}}").format(
                             star, value[1], star)
        return Math(value[0], wrapped_value)

    if key == 'RawBlock' and value[0] == 'latex':

        return process_latex_envs(key, value, oformat, meta)

    elif "Raw" in key:
        return []
