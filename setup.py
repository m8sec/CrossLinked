from setuptools import setup, find_packages

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name='crosslinked',
    version='0.2.0',
    author='m8sec',
    license='GPLv3',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url='https://github.com/m8sec/CrossLinked',
    packages=find_packages(include=[
        "crosslinked", "crosslinked.*"
    ]),
    install_requires=[
        'bs4>=0.0.1',
        'lxml>=4.9.1',
        'requests>=2.28.1',
        'Unidecode>=1.3.4'
    ],
    classifiers=[
        "Environment :: Console",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Topic :: Security"
    ],
    entry_points={
        'console_scripts': ['crosslinked=crosslinked:main']
    }
)
