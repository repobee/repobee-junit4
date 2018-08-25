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

wget https://download.java.net/java/GA/jdk10/10/binaries/openjdk-10_linux-x64_bin.tar.gz
tar -xzf openjdk-10_linux-x64_bin.tar.gz

wget http://central.maven.org/maven2/junit/junit/4.12/junit-4.12.jar
wget http://central.maven.org/maven2/org/hamcrest/hamcrest-core/1.3/hamcrest-core-1.3.jar

export REPOMATE_JUNIT4_HAMCREST="$(pwd)/junit-4.12.jar"
export REPOMATE_JUNIT4_JUNIT="$(pwd)/hamcrest-core-1.3.jar"
export JAVA_HOME="$(pwd)/jdk-10"
export PATH="$PATH:$(pwd)/jdk-10/bin"

echo export REPOMATE_JUNIT4_HAMCREST="$(pwd)/junit-4.12.jar" >> ~/.bashrc
echo export REPOMATE_JUNIT4_JUNIT="$(pwd)/hamcrest-core-1.3.jar" >> ~/.bashrc
echo export JAVA_HOME="$(pwd)/jdk-10" >> ~/.bashrc
echo export PATH="$PATH:$(pwd)/jdk-10/bin" >> ~/.bashrc
