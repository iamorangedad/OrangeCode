#!/usr/bin/env python3
"""
Setup script for Orange Code - AI Coding Assistant
"""

from setuptools import setup, find_packages
import os

# Read the README file
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# Read requirements
with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [
        line.strip()
        for line in fh
        if line.strip() and not line.startswith("#") and not line.startswith("pytest")
    ]

setup(
    name="orange-code",
    version="0.2.0",
    author="Orange Code Team",
    author_email="team@orangecode.com",
    description="A minimal coding agent for local or remote OpenAI-compatible models",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/iamorangedad/OrangeCode",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Topic :: Software Development :: Code Generators",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "orangecode=orangecode:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
