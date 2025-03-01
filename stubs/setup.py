from setuptools import setup, find_packages

setup(
    name="sol-tools-stubs",
    version="0.1.0",
    description="PEP 561 type stubs for sol-tools modules",
    packages=find_packages(),
    package_data={
        "Dragon": ["py.typed", "*.pyi"],
        "sol_tools": ["py.typed", "**/*.pyi"],
    },
    zip_safe=False,  # Required for PEP 561 type stubs
) 