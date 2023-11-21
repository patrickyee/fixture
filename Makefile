venv: requirements.txt
	python3 -m venv $@
	$@/bin/pip install -U pip
	$@/bin/pip install -r $<
	touch $@

.PHONY: format
format: venv
	venv/bin/isort .
	venv/bin/black .
	venv/bin/flake8 --exclude venv .

.PHONY: clean
clean:
	$(RM) -r venv
