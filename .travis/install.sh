#!/bin/bash
if [[ $TRAVIS_OS_NAME == 'osx' ]]; then
    brew update --force
    brew upgrade pyenv
    eval "$(pyenv init -)"
    pyenv install 3.6.10 --skip-existing
    pyenv global 3.6.10
    pip install pip --upgrade
fi

pip install -e ".[TEST]"

curl -L https://search.maven.org/remotecontent?filepath=junit/junit/4.13.1/junit-4.13.1.jar -o junit-4.13.1.jar
curl -L https://search.maven.org/remotecontent?filepath=org/hamcrest/hamcrest-core/1.3/hamcrest-core-1.3.jar -o hamcrest-core-1.3.jar
