"""
setup.py for doc_parser package
"""

from setuptools import setup, find_packages
import os

# Read README
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# Read requirements
with open("requirements.txt", "r", encoding="utf-8") as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]

setup(
    name="doc-parser",
    version="1.0.0",
    author="Document Parser Team",
    author_email="",
    description="OCR and Structured Extraction Integrated Tool",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/l236/image_recognization_processing",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Scientific/Engineering :: Image Recognition",
        "Topic :: Text Processing :: General",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=6.0",
            "black",
            "flake8",
            "mypy",
        ],
        "api": [
            "fastapi",
            "uvicorn",
        ],
        "web": [
            "streamlit",
        ],
    },
    entry_points={
        "console_scripts": [
            "doc-parser-api=doc_parser.api.service:app",
            "doc-parser-batch=doc_parser.utils.batch:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
