#!/bin/bash
if [[ $TRAVIS_OS_NAME == 'osx' ]]; then
    brew update --force
    brew upgrade pyenv
    eval "$(pyenv init -)"
    pyenv install 3.5.4 --skip-existing
    pyenv global 3.5.4
    pip install pip --upgrade
fi

java -version
pip install -e ".[TEST]"

curl https://search.maven.org/remotecontent?filepath=junit/junit/4.12/junit-4.12.jar -o junit-4.12.jar
curl https://search.maven.org/remotecontent?filepath=org/hamcrest/hamcrest-core/1.3/hamcrest-core-1.3.jar -o hamcrest-core-1.3.jar
