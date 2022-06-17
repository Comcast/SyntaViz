from setuptools import setup, find_packages
import re


def get_version():
    """
    Extract the version from the module's root __init__.py file
    """
    root_init_file = open("syntaviz/__init__.py").read()
    match = re.search("__version__[ ]+=[ ]+[\"'](.+)[\"']", root_init_file)
    return match.group(1) if match is not None else "unknown"


setup(
    name="syntaviz",
    version=get_version(),
    description="SyntaViz",

    packages=find_packages(),

    package_data={},

    python_requires='>=2.7, <3',

    install_requires=["flask==1.1.1",
                      "matplotlib==2.0.2",
                      "numpy==1.21.0",
                      "scikit-learn==0.18.2",
                      "scipy==0.19.1",
                      "ipython==7.16.3",
                      "bokeh==0.12.5",
                      "nltk==3.4.5",
                      "pandas==0.20.2",
                      "torch"],
    setup_requires=['pytest-runner'],
    tests_require=['pytest', 'pytest-cov'],
)
