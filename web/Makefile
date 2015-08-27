SOURCE_DIR ?= ctf_gameserver/web

.PHONY: lint

lint:
	# Run Pylint and pep8 to check the code for potential errors and style guideline violations, but ignore
	# their exit codes
	-pylint $(SOURCE_DIR)
	-pep8 --max-line-length=109 $(SOURCE_DIR)
