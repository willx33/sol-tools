"""Type stub for setuptools."""

from typing import Any, Dict, List, Optional, Union, Callable, Sequence

def setup(
    name: str = ...,
    version: str = ...,
    description: str = ...,
    long_description: str = ...,
    author: str = ...,
    author_email: str = ...,
    maintainer: str = ...,
    maintainer_email: str = ...,
    url: str = ...,
    download_url: str = ...,
    packages: List[str] = ...,
    py_modules: List[str] = ...,
    scripts: List[str] = ...,
    ext_modules: List[Any] = ...,
    classifiers: List[str] = ...,
    distclass: Any = ...,
    script_name: str = ...,
    script_args: List[str] = ...,
    options: Dict[str, Any] = ...,
    license: str = ...,
    keywords: Union[List[str], str] = ...,
    platforms: Union[List[str], str] = ...,
    cmdclass: Dict[str, Any] = ...,
    data_files: List[Any] = ...,
    package_dir: Dict[str, str] = ...,
    include_package_data: bool = ...,
    exclude_package_data: Dict[str, List[str]] = ...,
    package_data: Dict[str, List[str]] = ...,
    zip_safe: bool = ...,
    install_requires: List[str] = ...,
    entry_points: Dict[str, List[str]] = ...,
    extras_require: Dict[str, List[str]] = ...,
    python_requires: str = ...,
    **kwargs: Any
) -> None: ...

def find_packages(
    where: str = '.',
    exclude: Union[Sequence[str], str] = (),
    include: Union[Sequence[str], str] = ('*',)
) -> List[str]: ... 