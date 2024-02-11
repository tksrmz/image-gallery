create-tables:
	@echo "Creating tables..."
	python -m util.create_tables
	@echo "Tables created."

debug:
	flask run --host=0.0.0.0