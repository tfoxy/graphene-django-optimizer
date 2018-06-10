# Contributing


## Environment

The system must have installed:

* python 3
* virtualenv

```sh
virtualenv -p python3 venv
. venv/bin/activate
pip install -r dev-requirements.txt
# run tests:
python setup.py test
```


## Publish

```sh
# update version in setup.py
# then:
rm -r dist
python setup.py sdist bdist_wheel
twine upload dist/*
```
