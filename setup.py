from setuptools import setup, find_packages

VERSION = '0.0.2'

def get_requires(filename):
    requirements = []
    with open(filename) as req_file:
        for line in req_file.read().splitlines():
            if not line.strip().startswith("#"):
                requirements.append(line)
    return requirements

project_requirements = get_requires("requirements.txt")

setup(
    name="cget",
    version=VERSION,
    url='https://github.com/pfultz2/cget',
    license='boost',
    description='Cmake package retrieval',
    author='Paul Fultz II',
    author_email='pfultz2@yahoo.com',
    packages=find_packages(),
    install_requires=project_requirements,
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'cget = cget.cli:cli',
        ]
    },
    zip_safe=False
)
