from setuptools import setup, find_packages
import os
import sys

setup(
    name='stocks',
    version='0.1',
    author='rigidlab',
    description='A tool to download and analyze stocks data',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/rigidlab/stocks',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6',
    package_dir={'':'src'},
    packages=find_packages(where='src'),
    install_requires=[
        'click',
        'yfinance==0.2.63',
        'pandas',
        'bokeh'
    ],
    include_package_data=True,
    entry_points = {
        'console_scripts':[
            'stocks=stocks.cli:main',
         ]
    }
)