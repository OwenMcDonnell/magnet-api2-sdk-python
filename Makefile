sdist:
	rm -f dist/*
	python setup.py sdist

cheesecake: sdist
	cheesecake_index --path dist/`ls -1 dist/`

pypi:
	python setup.py clean
	python setup.py sdist upload -r pypi

pypitest:
	python setup.py clean
	python setup.py sdist upload -r pypitest
