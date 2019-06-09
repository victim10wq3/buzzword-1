from setuptools import setup


setup(name='buzz',
      version='1.0.5',  # DO NOT EDIT THIS LINE MANUALLY. LET bump2version UTILITY DO IT
      description='Sophisticated corpus linguistics',
      url='http://github.com/interrogator/buzz',
      author='Daniel McDonald',
      include_package_data=True,
      zip_safe=False,
      packages=['buzz'],
      scripts=['buzz/parse'],
      package_data={'buzz': ['*.sh',
                             'buzz/*.sh',
                             '*.p',
                             'dictionaries/*.p',
                             '*.py',
                             'dictionaries/*.py']},
      author_email='mcddjx@gmail.com',
      license='MIT',
      keywords=['corpus', 'linguistics', 'nlp'],
      install_requires=['nltk',
                        'bllipparser',
                        'scipy',
                        'cython',
                        # 'benepar',
                        # 'benepar[cpu]',
                        'tensorflow>=1.12.1',
                        'spacy',
                        'pandas',
                        'tqdm',
                        'pyparsing',
                        'tabview'],
      dependency_links=['https://github.com/interrogator/tabview/archive/master.zip'])
