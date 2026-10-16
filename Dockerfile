FROM python:3.12-slim
# Non-root user (required by Hugging Face Spaces; good practice elsewhere)
RUN useradd -m -u 1000 jaga
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY --chown=jaga:jaga . .
RUN mkdir -p /app/data && chown -R jaga:jaga /app/data
USER jaga
ENV JAGA_DB=/app/data/jaga.sqlite3 PORT=7860 PYTHONUNBUFFERED=1
EXPOSE 7860
CMD ["sh", "scripts/start.sh"]
