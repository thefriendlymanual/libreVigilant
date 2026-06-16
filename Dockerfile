FROM python:3.14-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV DB_PATH=/app/data/librevig.db
ENV UPLOAD_DIR=/app/data/uploads

RUN useradd --uid 1000 --create-home --shell /usr/sbin/nologin appuser \
    && mkdir -p /app/data/uploads \
    && chown -R appuser:appuser /app
USER appuser

VOLUME /app/data

EXPOSE 5000

CMD ["gunicorn", "--preload", "-w", "2", "-b", "0.0.0.0:5000", "app:app"]
