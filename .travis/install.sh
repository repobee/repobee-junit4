#!/bin/bash

if [[ $TRAVIS_OS_NAME == 'osx' ]]; then

    brew upgrade pyenv
    eval "$(pyenv init -)"
    pyenv install "$PYTHON"
    pyenv global "$PYTHON"
    python -m pip install -e ".[TEST]"
else
    pip install -e ".[TEST]"
fi

wget http://central.maven.org/maven2/junit/junit/4.12/junit-4.12.jar
wget http://central.maven.org/maven2/org/hamcrest/hamcrest-core/1.3/hamcrest-core-1.3.jar
