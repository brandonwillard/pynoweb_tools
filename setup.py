from setuptools import setup, find_packages

version = __import__('pynoweb_tools').get_version()

setup(name='pynoweb_tools',
      version=version,
      description=('Custom extensions and helper functions for processing'
                   'noweb files with Pweave and Pandoc.'),
      long_description=('Custom extensions and helper functions for processing'
                        'noweb files with Pweave and Pandoc.'),
      url='http://github.com/brandonwillard/pynoweb_tools',
      author='Brandon T. Willard',
      author_email='brandonwillard@gmail.com',
      classifiers=[
          'Development Status :: 1 - Alpha',
          'Programming Language :: Python :: 2',
          'Programming Language :: Python :: 3',
      ],
      keywords='latex, noweb, pandoc',
      packages=find_packages(),
      setup_requires=['pytest-runner', ],
      tests_requires=['pytest', ],
      install_requires=['pweave',
                        'pypandoc',
                        'pandocfilters',
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
