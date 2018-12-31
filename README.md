# Spotinst script managing actions for Elastigroups

Before cloning repo you should declare the account id and token for Launches and Magento.  
Create a .netrc file and populate it with these values, and  $chmod 600 .netrc 

example:
--------------------------------------------------------------------------

  
```bash

machine magento-token
login act-xxxxxx
password XXXXXXXXXXXXXXXX

```
---------------------------------------------------------------------------
  
Install spotinst:  
$ git clone git@bitbucket.org:endclothing/utilities.git && cd utilities/spotinst && python setup.py install
