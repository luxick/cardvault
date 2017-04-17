from setuptools import setup, find_packages
from cardvault import util

try:
    LONG_DESCRIPTION = open("README.rst").read()
except IOError:
    LONG_DESCRIPTION = __doc__


setup(
    name=util.APPLICATION_TITLE,
    version=util.VERSION,
    packages=find_packages(),

    # install_requires=['pygobject'],
    package_data={'cardvault': ['resources/images/*', 'resources/mana/*', 'gui/*']},

    author='luxick',
    author_email='cardvoult@luxick.de',
    description='Managing MTG card libraries and decks',
    long_description=LONG_DESCRIPTION,
    url='https://github.com/luxick/cardvault',
    keywords='card manager, gtk, MTG, Magic the Gathering',
    license="MIT",
    entry_points={
        'gui_scripts': [
            'cardvault = cardvault.application:main',
        ]
    },
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: End Users/Desktop',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'License :: OSI Approved :: MIT License',
    ]
    )
