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
with open("requirements_no_rag.txt", "r", encoding="utf-8") as fh:
    requirements = [
        line.strip() for line in fh if line.strip() and not line.startswith("#")
    ]

setup(
    name="orange-code",
    version="1.0.0",
    author="Orange Code Team",
    author_email="team@orangecode.com",
    description="An autonomous AI coding assistant with advanced scheduler functionality",
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
