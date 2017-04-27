import os
from setuptools import setup, find_packages

version = __import__('pynoweb_tools').get_version()


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(name='pynoweb_tools',
      version=version,
      description=('Custom extensions and helper functions for processing'
                   'noweb files with Pweave and Pandoc.'),
      long_description=read('README.md'),
      url='http://github.com/brandonwillard/pynoweb_tools',
      author='Brandon T. Willard',
      author_email='brandonwillard@gmail.com',
      license='LICENSE.txt',
      classifiers=[
          'Development Status :: 1 - Alpha',
          'Programming Language :: Python :: 3',
          'Programming Language :: Python :: 3.5',
      ],
      keywords='latex, noweb, pandoc, pweave',
      packages=find_packages(),
      use_2to3=True,
      setup_requires=['pytest-runner', ],
      tests_requires=['pytest', ],
      install_requires=['pweave',
                        'pypandoc',
                        'pandocfilters>=1.4.1',
                        'jupyter_client',
                        'tornado',
                        'nbformat'
                        ],
      dependency_links=[
        'git+ssh://git@github.com/jgm/pandocfilters.git',
      ],
      extra_require={
          'neovim': ['neovim', ],
      },
      entry_points={
          'console_scripts':
              ['PynowebWeave = pynoweb_tools.scripts:weave',
               'PynowebFilter = pynoweb_tools.scripts:latex_json_filter'
               ]},
      )
