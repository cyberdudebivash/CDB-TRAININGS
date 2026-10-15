from setuptools import find_packages, setup

setup(
    name="tinycsv",
    version="0.3.1",
    description="Summarise a CSV file",
    packages=find_packages(),
    install_requires=[],
    entry_points={"console_scripts": ["tinycsv-summary=tinycsv.cli:main"]},
)
