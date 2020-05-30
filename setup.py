from setuptools import setup, find_namespace_packages
from baboossh import version as baboossh_version

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name="baboossh",
    version=baboossh_version,
    packages=find_namespace_packages(include=['baboossh*']),
    scripts=['bin/baboossh'],

    install_requires=['cmd2','tabulate','fabric','paramiko','python-libnmap'],

    package_data={
        # If any package contains *.txt or *.rst files, include them:
        '': ['*.txt', '*.rst'],
    },

    # metadata to display on PyPI
    author="Cybiere - Akerva",
    author_email="nicolas@cosnard.io",
    description="SSH spreader made easy for red teams in a hurry",
    long_description=long_description,
    long_description_content_type="text/markdown",
    keywords="ssh spread redteam pentest",
    url="https://github.com/cybiere/BabooSSH",   # project home page, if any
    project_urls={
        "Bug Tracker": "https://github.com/cybiere/BabooSSH/issues",
        "Documentation": "https://baboossh.cybiere.fr/",
        "Source Code": "https://github.com/cybiere/BabooSSH",
    },
    classifiers=[
        'Programming Language :: Python :: 3.5',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Environment :: Console',
        'Natural Language :: English',
        'Operating System :: POSIX',
        'Topic :: Security'
    ]

    # could also include long_description, download_url, etc.
)
