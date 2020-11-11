#!/bin/bash
pip install -e ".[TEST]"

curl -L https://search.maven.org/remotecontent?filepath=junit/junit/4.12/junit-4.12.jar -o junit-4.12.jar
curl -L https://search.maven.org/remotecontent?filepath=org/hamcrest/hamcrest-core/1.3/hamcrest-core-1.3.jar -o hamcrest-core-1.3.jar
