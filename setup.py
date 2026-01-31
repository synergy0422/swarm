#!/usr/bin/env python3
"""
Setup configuration for AI Swarm package
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="ai-swarm",
    version="0.1.0",
    author="AI Swarm Team",
    description="Multi-Agent Task Processing System with Anthropic Claude",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/ai-swarm",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.8",
    install_requires=[
        "requests>=2.28.0",
        "libtmux>=0.9.0",
    ],
    entry_points={
        "console_scripts": [
            "swarm=swarm.cli:main",
        ],
    },
    include_package_data=True,
)
