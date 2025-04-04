FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt
COPY . /app/
# RUN python manage.py migrate
EXPOSE 8000
CMD ["sh", "-c", "python manage.py migrate && gunicorn LecapProject.wsgi:application --bind 0.0.0.0:8000"]