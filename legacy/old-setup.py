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
        "pytest",
        "pydantic",
        "p_tqdm"
    ],
    entry_points={
        "console_scripts": [
            "cmipld=cmipld.browse.__main__:main",
            "update_ctx=cmipld.generate.update_ctx:main",
            "update_all=cmipld.generate.update_all:main",
            "update_schema=cmipld.schema.update_schema:main",
            "update_issues=cmipld.schema.issue_template:main",
            "rewrite_type=cmipld.generate.rewritetype:main",
            "new_issue=cmipld.generate.new_issue:main"
            # "cmipgraph=cmipld.graph:main",
            # "updateld=cmipld.generate.update_new:init",
            # "makegraph=cmipld.generate.makegraph:run",
            # "reframe=cmipld.generate.reframe:run",
            # "updateelastic=cmipld.generate.elasticmipcvs:run",
            # "add_new=cmipld.git.actions.add:submit_dispatch",
            # "test_inputs=cmipld.tests.inputs:run",
            # "issue_templates=cmipld.generate.issue_template:run",
            # "new_element=cmipld.generate.new_element_from_issue:action",
            # "gencv=cmipld.cvs.generate:run",
        ],
    },
    scripts=[
        # "scripts/directory-utilities/combine-graphs",
        # "scripts/directory-utilities/compile-ld",
        "scripts/directory-utilities/dev",
        "scripts/directory-utilities/validjsonld",
        "scripts/directory-utilities/ld2graph",
        "scripts/jsonld-util/rmbak",
        "scripts/jsonld-util/rmgraph"
        
    ],
    include_package_data=True,
    package_data={
        "cmipld": ["scripts/*/*.sh"],
        'cmipld.frame_ld': ['examples/*/*.json'],
    },
    # package_data={
    #     'your_library': ['examples/*.json'],  # Adjust this to your actual package and files
    # },
)
