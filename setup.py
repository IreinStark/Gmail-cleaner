from setuptools import setup, find_packages

setup(
    name="gmail-cleaner",
    version="0.1.0",
    description="Gmail AI Cleaner using Gemini and Gmail API",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.8",
    install_requires=[
        "google-generativeai>=0.7.0",
        "google-api-python-client>=2.134.0",
        "google-auth>=2.35.0",
        "google-auth-oauthlib>=1.2.1",
        "python-dotenv>=1.0.1",
        "tenacity>=9.0.0",
        "typer>=0.12.3",
        "rich>=13.7.1",
        "dataclasses-json>=0.6.7",
    ],
    entry_points={
        "console_scripts": [
            "gmail-cleaner=gmail_cleaner.main:app",
        ]
    },
)

