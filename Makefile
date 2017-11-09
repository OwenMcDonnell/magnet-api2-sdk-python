
sdist:
	rm -f dist/*
	python setup.py sdist

cheesecake: sdist
	cheesecake_index --path dist/`ls -1 dist/`
