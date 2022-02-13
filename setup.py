import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="spawk",
    version="0.0.1",
    author="Sean Reifschneider",
    author_email="jafo00@gmail.com",
    description="A text processing library",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/linsomniac/spawk",
    packages=setuptools.find_packages(),
    py_modules=["spawk"],
    install_requires=["click", "apache-log-parser"],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    entry_points="""
        [console_scripts]
        spawk=spawk.cli.main:cli
    """,
)
