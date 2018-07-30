import setuptools, re

with open("README.md", "r") as fh:
    long_description = fh.read()

with open("guidmint/__init__.py") as f:
    content = f.read()
    match = re.findall(r"__([a-z0-9_]+)__\s*=\s*\"([^\"]+)\"", content)
    print(match)
    metadata = dict(match)

setuptools.setup(
    name=metadata.get("name"),
    version=metadata.get("version"),
    author=metadata.get("author"),
    author_email=metadata.get("author_email"),
    description="Global unique ID and pseudonym generator",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/derekmerck/diana_plus",
    packages=setuptools.find_packages(),
    include_package_data=True,
    classifiers=(
        'Development Status :: 3 - Alpha',
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ),
    license='MIT',
    install_requires=['python-dateutil']
)