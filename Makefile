PACKAGE      = src/metrics_python
BASE  	     = $(shell dirname $(realpath $(lastword $(MAKEFILE_LIST))))

POETRY      = poetry

V = 0
Q = $(if $(filter 1,$V),,@)
M = $(shell printf "\033[34;1m▶\033[0m")

.PHONY: all
all: lint test ; @ ## Lint and test project
	$Q

$(POETRY): ; $(info $(M) checking POETRY…)
	$Q

$(BASE): | $(POETRY) ; $(info $(M) checking PROJECT…)
	$Q

.PHONY: fix
fix: fix-ruff fix-black | $(BASE) ; @ ## Run all fixers
	$Q

.PHONY: lint-backend
lint-backend: lint-ruff lint-black lint-dmypy | $(BASE) ; @ ## Run all backend linters
	$Q

.PHONY: lint
lint: lint-backend | $(BASE) ; @ ## Lint project
	$Q


.PHONY: test-backend
test-backend: test-pytest | $(BASE) ; @ ## Run pytest
	$Q


.PHONY: test
test: test-backend | $(BASE) ; @ ## Run tests
	$Q

# Tests
.PHONY: test-pytest
test-pytest: .venv | $(BASE) ; $(info $(M) running backend tests…) @ ## Run pytest
	$Q cd $(BASE) && PYTHONHASHSEED=0 $(POETRY) run pytest $(PACKAGE) --numprocesses 3

.PHONY: test-pytest-coverage
test-pytest-coverage: .venv | $(BASE) ; $(info $(M) running tests with coverage…) @ ## Run pytest with coverage
	$Q cd $(BASE) && PYTHONHASHSEED=0 $(POETRY) run pytest \
        --numprocesses 8 \
		--cov \
		--cov-report=html \
		--cov-report=xml:coverage/pytest-cobertura.xml \
		--cov-report=term

# Linters

.PHONY: lint-black
lint-black: .venv | $(BASE) ; $(info $(M) running black…) @ ## Run black linter
	$Q cd $(BASE) && $(POETRY) run black --check $(PACKAGE)

.PHONY: lint-ruff
lint-ruff: .venv | $(BASE) ; $(info $(M) running ruff…) @ ## Run ruff linter
	$Q cd $(BASE) && $(POETRY) run ruff $(PACKAGE)

.PHONY: lint-mypy
lint-mypy: .venv | $(BASE) ; $(info $(M) running mypy…) @ ## Run mypy linter
	$Q cd $(BASE) && $(POETRY) run mypy --show-error-codes --show-column-numbers $(PACKAGE)

.PHONY: lint-dmypy
lint-dmypy: .venv | $(BASE) ; $(info $(M) running mypy…) @ ## Run dmypy linter
	$Q cd $(BASE) && $(POETRY) run -- dmypy run $(PACKAGE) -- --show-error-codes

# Fixers

.PHONY: fix-black
fix-black: .venv | $(BASE) ; $(info $(M) running black…) @ ## Run black fixer
	$Q cd $(BASE) && $(POETRY) run black $(PACKAGE)

.PHONY: fix-ruff
fix-ruff: .venv | $(BASE) ; $(info $(M) running ruff…) @ ## Run ruff fixer
	$Q cd $(BASE) && $(POETRY) run ruff --fix $(PACKAGE)

# Dependency management

.venv: pyproject.toml poetry.lock | $(BASE) ; $(info $(M) retrieving dependencies…) @ ## Install python dependencies
	$Q cd $(BASE) && $(POETRY) run pip install -U pip
	$Q cd $(BASE) && $(POETRY) install
	@touch $@

# Misc

.PHONY: clean
clean: ; $(info $(M) cleaning…) @ ## Cleanup caches and virtual environment
	@rm -rf .eggs *.egg-info .venv test-reports
	@find . -type d -name '__pycache__' -exec rm -rf {} +
	@find . -type d -name '*pytest_cache*' -exec rm -rf {} +

.PHONY: help
help: ## This help message
	@grep -E '^[ a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}' | sort
