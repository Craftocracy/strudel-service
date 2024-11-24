FROM python:3.12.7-slim-bookworm

EXPOSE 8079

WORKDIR /code


COPY ./requirements.txt /code/requirements.txt


RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt


COPY ./src /code/app


CMD ["fastapi", "run", "app/main.py", "--port", "8079"]