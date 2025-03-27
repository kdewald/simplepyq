from setuptools import setup, find_packages

setup(
    name="simplepyq",
    version="0.1.0",
    packages=find_packages(),
    install_requires=["msgpack"],
    author="Kevin Dewald",
    author_email="kevin@dewald.me",
    description="A lightweight task scheduler for small projects",
    long_description=open("README.rst").read(),
    long_description_content_type="text/x-rst",
    url="https://github.com/kdewald/simplepyq",
    license="Apache-2.0",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
)