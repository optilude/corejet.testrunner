from setuptools import setup, find_packages

version = '1.0a3'

requires = [
    'setuptools',
    'lxml',
    'zope.testrunner',
    'corejet.core',
    'corejet.visualization',
    'zc.recipe.egg',
    'zope.dottedname',
]

setup(name='corejet.testrunner',
      version=version,
      description="A test runner which can output an XML report compatible "
                  "with JUnit and Hudson/Jenkins as well as XML and HTML "
                  "reports compatible with the CoreJet BDD standard",
      long_description=open("README.txt").read() + "\n" +
                       open("CHANGES.txt").read(),
      classifiers=[
        "Programming Language :: Python",
        ],
      keywords='hudson jenkins junit xml corejet zope.testing',
      author='Martin Aspeli',
      author_email='optilude@gmail.com',
      url='http://corejet.org',
      license='ZPL 2.1',
      packages=find_packages(exclude=['ez_setup']),
      namespace_packages=['corejet'],
      include_package_data=True,
      zip_safe=False,
      install_requires=requires,
      entry_points="""
      [zc.buildout]
      default = corejet.testrunner.recipe:TestRunner
      
      [corejet.repositorysource]
      file = corejet.testrunner.filesource:fileSource
      """,
      )
