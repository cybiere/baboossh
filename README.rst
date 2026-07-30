.. image:: https://raw.githubusercontent.com/cybiere/baboossh/master/logo.png

.. image:: https://github.com/cybiere/BabooSSH/actions/workflows/test.yml/badge.svg
   :target: https://github.com/cybiere/BabooSSH/actions/workflows/test.yml

SSH spreading made easy for red teams in a hurry.


BabooSSH allows you, from a simple SSH connection to a compromised host, to quickly gather info on other SSH endpoints to pivot and compromise them.

Licence
+++++++

BabooSSH is developped by `Cybiere <https://infosec.exchange/@cybiere>`_ and provided for free under the GNU/GPLv3 licence.

Note on AI assisted development
+++++++++++++++++++++++++++++++

Up until this commit, no AI has been used in this project. From now on I'll try to spend some time on this project and I will use Claude Code. Code will be reviewed and the AI tool will have small, defined, iterative instructions. If you do not want to have AI-written code, feel free to fork this repo or to contribute to the code :)

| Last version without AI assisted dev : v1.2.1

Install
+++++++

It's as easy as a::

   pip install baboossh


Development
+++++++++++

The project uses `uv <https://docs.astral.sh/uv/>`_ for dependency management. To set up a dev environment::

   uv sync
   uv run baboossh

Tests
+++++

Tests are written with `pytest <https://docs.pytest.org/>`_ and live under ``tests/``. Run them with::

   uv sync --group dev
   uv run pytest

Tests run automatically on every push and pull request via `GitHub Actions <https://github.com/cybiere/BabooSSH/actions/workflows/test.yml>`_. See ``todo.md`` for known gaps in current test coverage.


Documentation
+++++++++++++

The documentation is under redaction and some things might be missing, but you can find it there: `<https://baboossh.cybiere.fr>`_ .
