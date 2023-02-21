FROM python:3.11-alpine

WORKDIR /pycat

COPY . .

RUN pip install pipenv && pipenv install

ENV PYCAT_BIND=0.0.0.0
EXPOSE 7777

CMD ["pipenv", "run", "cli"]
