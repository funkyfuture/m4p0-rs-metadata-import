from setuptools import setup

setup(
    name="m4p0-rs-metadata-import",
    author="Martin Wagner",
    author_email="martin.x.wagner@posteo.de",
    packages=["rs_import"],
    install_requires=["Cerberus~=1.3", "httpx==0.11.*", "PyYaml~=5.1", "rdflib~=4.2"],
    python_requires=">=3.6",
    entry_points={"console_scripts": ["rs-import=rs_import.main:main"]},
)
