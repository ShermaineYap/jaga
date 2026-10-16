.PHONY: install test demo dashboard bot eval eval-mock charts smoke models

install:
	pip install -r requirements.txt

test:
	JAGA_MOCK=1 JAGA_DB=/tmp/jaga-test.sqlite3 pytest -q

demo:            ## seed the demo household + three demo cases
	python scripts/seed_demo.py

dashboard:
	uvicorn jaga.dashboard.app:app --host 0.0.0.0 --port 8000 --reload

bot:
	python -m jaga.bot

models:          ## day-one: confirm Nemotron model IDs on Token Factory
	python scripts/list_models.py

smoke:           ## day-one: Malay/Manglish smoke test
	python scripts/malay_smoke.py

eval:            ## full ScamBench-MY sweep on Token Factory (~ $1-3)
	python eval/run_eval.py --configs rules,fast,plan,full,no_tavily,no_ledger

eval-mock:       ## offline sweep with heuristics (CI / no credits)
	python eval/run_eval.py --mock

charts:
	python eval/charts.py
