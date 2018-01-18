from setuptools import setup, find_packages

setup(
    name='panem',
    version='0.1.1.dev0',
    description='panemd',
    url='https://gitlab.bearstech.com/factory/panem',
    install_requires=[
        'pyaml',
        'requests',
        'raven[flask]',
        'flask',
        'flask-restplus',
        'flask-sqlalchemy',
        'pg8000',
        'passlib',
    ],
    licence="GPLv3",
    classifiers=[
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
    ],
    packages=find_packages(exclude=['contrib', 'docs', 'tests']),
    extras_require={
        'test': ['pytest', 'pytest-cov', 'responses', 'webtest'],
    },
    entry_points='''
    [console_scripts]
    panem-password = panem.password:main
    panem-web = panem.app:main
    ''',
)
