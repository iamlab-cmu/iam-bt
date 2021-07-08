from distutils.core import setup
  

setup(name='iam_bt',
      version='0.1.0',
      install_requires=[
            'pillar_state',
            'pydot',
            'shortuuid'
      ],
      description='Behavior Tree Utilities for IAM Lab',
      author='Jacky Liang',
      author_email='jackyliang@cmu.edu',
      packages=['iam_bt']
     )