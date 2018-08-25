
#!/bin/bash

if [[ $TRAVIS_OS_NAME == 'osx' ]]; then
    eval "$(pyenv init -)"
    pyenv global "$PYTHON"
    python --version
    python -m pytest tests --cov=repomate_junit4
else
    pytest tests --cov=repomate_junit4
fi
