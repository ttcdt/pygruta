from setuptools import setup
import os
import pygruta

with open("README", "r") as r:
    long_desc = r.read()

setup(
    name="pygruta",
    version=pygruta.__version__,
    description="A blogging tool",
    long_description=long_desc,
    author="ttcdt",
    author_email="dev@triptico.com",
    packages=["pygruta"],
    url="https://triptico.com/software/pygruta.html",
    license="Public Domain",
    entry_points={
        "console_scripts": [
            "pygruta = pygruta.__main__:main"
        ]
    }
)
