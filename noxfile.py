# Copyright 2016 Alethea Katherine Flowers
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import functools
import os
import platform
import sys

import nox

ON_WINDOWS_CI = "CI" in os.environ and platform.system() == "Windows"


def is_python_version(session, version):
    if not version.startswith(session.python):
        return False
    py_version = session.run("python", "-V", silent=True)
    py_version = py_version.partition(" ")[2].strip()
    return py_version.startswith(version)


@nox.session(python=["3.6", "3.7", "3.8", "3.9", "3.10"])
def tests(session):
    """Run test suite with pytest."""
    session.create_tmp()
    session.install("-r", "requirements-test.txt")
    session.install("-e", ".[tox_to_nox]")
    tests = session.posargs or ["tests/"]
    if is_python_version(session, "3.6.0"):
        session.run("pytest", *tests)
        return
    session.run(
        "pytest",
        "--cov=nox",
        "--cov-config",
        "pyproject.toml",
        "--cov-report=",
        *tests,
        env={"COVERAGE_FILE": f".coverage.{session.python}"},
    )
    session.notify("cover")


@nox.session(python=["3.6", "3.7", "3.8", "3.9", "3.10"], venv_backend="conda")
def conda_tests(session):
    """Run test suite with pytest."""
    session.create_tmp()
    session.conda_install(
        "--file", "requirements-conda-test.txt", "--channel", "conda-forge"
    )
    session.install("-e", ".", "--no-deps")
    tests = session.posargs or ["tests/"]
    session.run("pytest", *tests)


@nox.session
def cover(session):
    """Coverage analysis."""
    if ON_WINDOWS_CI:
        return

    # 3.10 produces different coverage results for some reason
    # see https://github.com/theacodes/nox/issues/478
    fail_under = 100
    py_version = sys.version_info
    if py_version.major == 3 and py_version.minor == 10:
        fail_under = 99

    session.install("coverage[toml]")
    session.run("coverage", "combine")
    session.run("coverage", "report", f"--fail-under={fail_under}", "--show-missing")
    session.run("coverage", "erase")


@nox.session(python="3.8")
def blacken(session):
    """Run black code formatter."""
    session.install("black==21.5b2", "isort==5.8.0")
    files = ["nox", "tests", "noxfile.py", "docs/conf.py"]
    session.run("black", *files)
    session.run("isort", *files)


@nox.session(python="3.8")
def lint(session):
    session.install(
        "flake8==3.9.2",
        "black==21.6b0",
        "isort==5.8.0",
        "mypy==0.902",
        "types-jinja2",
        "packaging",
        "importlib_metadata",
    )
    session.run("mypy")
    files = ["nox", "tests", "noxfile.py", "docs/conf.py"]
    session.run("black", "--check", *files)
    session.run("isort", "--check", *files)
    session.run("flake8", *files)


@nox.session(python="3.8")
def docs(session):
    """Build the documentation."""
    output_dir = os.path.join(session.create_tmp(), "output")
    doctrees, html = map(
        functools.partial(os.path.join, output_dir), ["doctrees", "html"]
    )
    session.run("rm", "-rf", output_dir, external=True)
    session.install("-r", "requirements-test.txt")
    session.install(".")
    session.cd("docs")
    sphinx_args = ["-b", "html", "-W", "-d", doctrees, ".", html]

    if not session.interactive:
        sphinx_cmd = "sphinx-build"
    else:
        sphinx_cmd = "sphinx-autobuild"
        sphinx_args.insert(0, "--open-browser")

    session.run(sphinx_cmd, *sphinx_args)
