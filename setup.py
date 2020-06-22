# -*- coding: utf-8 -*-

from setuptools import find_packages, setup


with open('README.rst', 'r') as f:
    long_description = f.read()


with open('requirements.txt', 'r') as f:
    install_requires = [
        line.rstrip() for line in f if not line.startswith('#')
    ]


setup(
    name='message-tagging-service',
    version='0.8.1',
    description='Tag Koji build with correct tag which is triggered by message bus',
    long_description=long_description,
    maintainer='Factory 2 Team',
    # Not sure which email address is proper here, so just using a fake email
    # address. But, probably this could be a real some day, or another one.
    maintainer_email='message-tagging-service@fedoraproject.org',
    license='GPLv2+',
    url='https://github.com/fedora-modularity/message-tagging-service',
    keywords='messaging,module,tag,koji',
    packages=find_packages(),
    install_requires=install_requires,
    classifiers=[
        'License :: OSI Approved :: GNU Lesser General Public License v2 or later (LGPLv2+)',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
    data_files=[
        ('/etc/mts/', ['conf/config.py']),
    ],
)
