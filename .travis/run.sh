
#!/bin/bash

if [[ $TRAVIS_OS_NAME == 'osx' ]]; then
    tox
else
    pytest tests --cov=repomate_junit4
fi
