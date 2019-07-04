from setuptools import setup

setup(
    name="m4p0-rs-metadata-import",
    author="Martin Wagner",
    author_email="martin.x.wagner@posteo.de",
    packages=["rs_import"],
    install_requires=["Cerberus=~1.3", "PyYaml"],
    python_requires=">=3.6",
    entry_points={"console_scripts": ["rs-import=rs_import.main:main"]},
)
