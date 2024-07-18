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
            "cmipgraph=cmipld.graph:main",
            "updateld=cmipld.generate.update_new:init",
            "ldcontext=cmipld.generate.update_new:init",
        ],
    },
    scripts=[
        "scripts/directory-utilities/combine-graphs",
        "scripts/directory-utilities/compile-ld",
    ],
    include_package_data=True,
    package_data={
        "cmipld": ["scripts/*/*.sh"],
    },
)
