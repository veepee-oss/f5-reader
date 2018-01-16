import os
from distutils.core import setup

if __name__ == '__main__':
    readme_file = os.path.join(os.path.dirname(__file__), 'README.rst')
    release = "0.1.0"
    setup(
        name="f5reader",
        version=release,
        url="https://git.vpgrp.io/core/f5-reader",
        author="Denis Pompilio (jawa)",
        author_email="dpompilio@vente-privee.com",
        maintainer="Denis Pompilio (jawa)",
        maintainer_email="denis.pompilio@gmail.com",
        description="F5 BigIP configuration reader",
        long_description=open(readme_file).read(),
        license="MIT",
        platforms=['UNIX'],
        scripts=['bin/f5reader'],
        packages=['f5reader'],
        package_dir={'f5reader': 'f5reader'},
        data_files=[
            ('share/doc/f5reader', ['README.rst', 'LICENSE', 'CHANGES']),
        ],
        keywords=['loadbalancer', 'shell', 'big-ip', 'f5', 'configuration'],
        classifiers=[
            'Development Status :: 5 - Production/Stable',
            'Operating System :: POSIX :: BSD',
            'Operating System :: POSIX :: Linux',
            'License :: OSI Approved :: MIT License',
            'Programming Language :: Python',
            'Environment :: Console',
            'Topic :: Utilities',
            'Topic :: System :: Systems Administration'
            ]
    )
