"""
Setup-Script für YouTube Investigator
Ermöglicht Installation als CLI-Tool
"""
from setuptools import setup, find_packages

setup(
    name='youtube-investigator',
    version='0.1.0',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'google-api-python-client>=2.100.0',
        'google-auth>=2.23.0',
        'click>=8.1.0',
        'rich>=13.0.0',
        'python-dotenv>=1.0.0',
        'pytz>=2024.1',
        'sqlite-utils>=3.35.0',
    ],
    entry_points={
        'console_scripts': [
            'yt-investigate=src.main:cli',
        ],
    },
    author='YouTube Investigator Team',
    description='CLI-Tool für investigative Analysen von YouTube-Kanälen',
    python_requires='>=3.10',
)
