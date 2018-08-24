from setuptools import setup, find_packages

with open('README.md', mode='r', encoding='utf-8') as f:
    readme = f.read()

test_requirements = [
    'appdirs', 'daiquiri', 'pytest', 'pytest-cov>=2.5.1', 'pytest-mock',
    'codecov'
]
required = ['repomate-plug', 'daiquiri', 'colored']

setup(
    name='repomate-junit4',
    version='0.1.0',
    description=(
        'A CLI tool for managing large amounts of GitHub repositories'),
    long_description=readme,
    long_description_content_type='text/markdown',
    author='Simon Larsén',
    author_email='slarse@kth.se',
    #url='https://github.com/slarse/repomate-junit4',
    #download_url='https://github.com/slarse/repomate-junit4/archive/v0.1.0.tar.gz',
    license='MIT',
    packages=find_packages(exclude=('tests', 'docs')),
    tests_require=test_requirements,
    install_requires=required,
    extras_require=dict(TEST=test_requirements),
    include_package_data=True,
    zip_save=False,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Education',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: Implementation :: CPython',
        'License :: OSI Approved :: MIT License',
        'Operating System :: POSIX',
    ])
