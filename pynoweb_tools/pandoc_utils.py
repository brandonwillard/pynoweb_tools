import re
import os
from copy import copy

import logging

import json
from collections import Iterable
from functools import reduce

import pypandoc

# See https://hackage.haskell.org/package/pandoc-1.17.2
# and https://hackage.haskell.org/package/pandoc-types-1.16.1.1 for
# definitions.
from pandocfilters import (
    Math,
    Image,
    Div,
    Str,
    Plain,
    RawInline,
    RawBlock)


logging.basicConfig(level=logging.DEBUG)

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

# TODO: Automatically track and replace \[Cc]ref with \[eq]ref.
preserved_conversions = {'\\cref': '\\ref',
                         '\\Cref': '\\ref'}

figure_dirs = set()


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

    # See if we can find the file in one of the dirs
    if isinstance(fig_dirs, Iterable):
        fig_files = map(lambda x: os.path.join(x, new_fig_fname),
                        fig_dirs)
        real_fig_files = filter(os.path.exists, fig_files)
        new_fig_fname = next(real_fig_files, new_fig_fname)
    else:
        new_fig_fname = os.path.join(fig_dirs, new_fig_fname)

    return new_fig_fname


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
    logging.debug(("Filter key:{}, value:{}, meta:{},"
                   "args:{}, kwargs:{}\n").format(
                       key, value, meta, args, kwargs))

    global preserved_conversions, preserved_tex, env_conversions, figure_dirs

    preserved_conversions = preserved_conversions.copy()
    preserved_conversions.update(meta.get(
        'preserved_conversions', {}).get('c', {}))

    env_conversions = env_conversions.copy()
    env_conversions.update(meta.get(
        'env_conversions', {}).get('c', {}))

    preserved_tex += meta.get('preserved_tex', {}).get('c', [])

    figure_dir_meta = meta.get('figure_dir', {}).get('c', None)
    if figure_dir_meta is not None:
        figure_dirs.add(figure_dir_meta)

    logging.debug("figure_dir_meta: {}\tfigure_dirs: {}\n".format(
        figure_dir_meta, figure_dirs))

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

            for from_, to_ in preserved_conversions.items():
                new_value = new_value.replace(from_, to_)

            return Math({'t': 'InlineMath', 'c': []}, new_value)
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

        # TODO: Find and use labels.
        # TODO: Perhaps check that it's a valid file?
        new_value = copy(value[2])

        new_fig_fname = rename_find_fig(new_value[0],
                                        figure_dirs,
                                        fig_fname_ext)
        new_value[0] = new_fig_fname

        return Image(value[0], value[1], new_value)

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

                hack_div_label = env_label+"_math"
                # XXX: We're hijacking MathJax's numbering system.
                ref_hack = (r'$$\begin{{equation}}'
                            r'\tag{{{}}}'
                            r'\label{{{}}}'
                            r'\end{{equation}}$$'
                            ).format(env_num, env_label)

                label_div = Div([hack_div_label, [],
                                 [#['markdown', ''],
                                  ["style",
                                   "display:none;visibility:hidden"]]],
                                [RawBlock('latex', ref_hack)])

                # Now, remove the latex label string
                env_body = env_body.replace(label_info.group(1), '')


            # type Attr = (String, [String], [(String, String)])
            # Attributes: identifier, classes, key-value pairs
            div_attr = [env_label, [env_name], [['markdown', ''],
                                                ["env-number", str(env_num)],
                                                ['title-name', env_title]
                                                ]]

            # TODO: Should we evaluate nested environments?
            env_body = pypandoc.convert_text(env_body, 'json',
                                             format='latex',
                                             filters=['PynowebFilter']
                                             )

            div_block = json.loads(env_body)[1]

            if label_div is not None:
                div_block = [label_div] + div_block

            return Div(div_attr, div_block)
        else:
            return []

    elif "Raw" in key:
        return []
