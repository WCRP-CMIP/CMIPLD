from setuptools import setup, find_packages

setup(
    name="cmip-ld",
    author="Daniel Ellis",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "requests",
        "pyld",
        "jmespath",
    ],
    entry_points={
        "console_scripts": [
            "cmipld=cmipld.cmipld:main",
        ],
    },
    include_package_data=True,
    package_data={
        "cmipld": ["scripts/*.sh"],
    },
)
