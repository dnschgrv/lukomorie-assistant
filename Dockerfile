FROM python:3.12-slim
WORKDIR /srv/lukomorie-assistant
COPY . .
RUN useradd --system --uid 10001 assistant && mkdir -p /srv/lukomorie-assistant/data && chown -R assistant:assistant /srv/lukomorie-assistant
USER assistant
EXPOSE 8080
CMD ["python", "-m", "app.server"]
