#!/bin/bash

function run_flake8() {
    pip install flake8
    flake8 .
}

if [[ $TRAVIS_OS_NAME == 'osx' ]]; then
    eval "$(pyenv init -)"
    pyenv global 3.6.10
fi

run_flake8
pytest tests --cov=repobee_junit4 --cov-branch
