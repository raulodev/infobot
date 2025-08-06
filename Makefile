help:
	@echo "Usage: make <target>"
	@echo "  deploy               Build and deploy app"
	@echo "  logs                 See logs app"

deploy:
	docker compose build app
	docker compose up -d app

logs:
	docker compose logs

