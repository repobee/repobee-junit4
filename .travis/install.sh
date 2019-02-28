#!/bin/bash

if [[ $TRAVIS_OS_NAME == 'osx' ]]; then

    brew upgrade pyenv
    eval "$(pyenv init -)"
    pyenv install 3.5.4
    pyenv install 3.6.5
    pyenv install 3.7.0
    pyenv global 3.7.0
    pip install pip --upgrade
    pip install tox tox-pyenv
else
    pip install pip --upgrade
    pip install tox tox-travis
    pip install -e ".[TEST]"
fi

wget http://central.maven.org/maven2/junit/junit/4.12/junit-4.12.jar
wget http://central.maven.org/maven2/org/hamcrest/hamcrest-core/1.3/hamcrest-core-1.3.jar
