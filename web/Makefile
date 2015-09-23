SOURCE_DIR ?= ctf_gameserver/web
EXT_DIR ?= $(SOURCE_DIR)/static/ext

.PHONY: lint
.INTERMEDIATE: bootstrap.zip

dependencies: $(EXT_DIR)/jquery.min.js $(EXT_DIR)/bootstrap

$(EXT_DIR)/jquery.min.js:
	mkdir -p $(EXT_DIR)
	curl https://code.jquery.com/jquery-1.11.3.min.js -o $@

bootstrap.zip:
	curl -L https://github.com/twbs/bootstrap/releases/download/v3.3.5/bootstrap-3.3.5-dist.zip -o $@

$(EXT_DIR)/bootstrap: bootstrap.zip
	mkdir -p $(EXT_DIR)
	unzip -n $< -d $(EXT_DIR)
	mv -v $(EXT_DIR)/bootstrap-3.3.5-dist $(EXT_DIR)/bootstrap


lint:
	# Run Pylint and pep8 to check the code for potential errors and style guideline violations, but ignore
	# their exit codes
	-pylint $(SOURCE_DIR)
	-pep8 --max-line-length=109 $(SOURCE_DIR)
