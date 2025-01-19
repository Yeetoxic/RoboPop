FROM python:latest

LABEL Maintainer="Dani"

WORKDIR /usr/app/src

COPY Main.py ./
COPY requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt

CMD [ "python","-u", "./Main.py"]