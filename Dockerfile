FROM python:3.10.8-slim

RUN apt-get update && apt-get upgrade -y
RUN apt-get install git -y
COPY requirements.txt /requirements.txt

RUN cd /
RUN pip3 install -U pip && pip3 install -U -r requirements.txt
RUN mkdir /FileToLink
WORKDIR /FileToLink
COPY . /FileToLink
CMD ["python", "bot.py"]

