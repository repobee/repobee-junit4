#!/bin/bash
if [[ $TRAVIS_OS_NAME == 'osx' ]]; then
    brew update --force
    brew upgrade pyenv
    eval "$(pyenv init -)"
    pyenv install 3.5.4 --skip-existing
    pyenv global 3.5.4
    pip install pip --upgrade
fi

pip install -e ".[TEST]"

wget http://central.maven.org/maven2/junit/junit/4.12/junit-4.12.jar
wget http://central.maven.org/maven2/org/hamcrest/hamcrest-core/1.3/hamcrest-core-1.3.jar
