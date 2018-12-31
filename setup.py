from setuptools import setup
setup(name='spotinst',
      version='1.0',
      py_modules=['spotinst'],
      install_requires=['requests','spotinst-sdk'],
      scripts=['spotinst.py']
          
      )
