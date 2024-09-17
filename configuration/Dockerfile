FROM ubuntu:noble
ARG DEBIAN_FRONTEND=noninteractive

# Run all upgrades and installation of necessary tools to run the job
RUN apt-get update
RUN apt-get upgrade -y
RUN apt-get install -y software-properties-common
RUN apt-get install -y python3-pip
RUN apt install -y python3.12-venv
RUN apt-get install -y openjdk-8-jdk

COPY ./data-pipeline /home/ubuntu/data-pipeline

WORKDIR /home/ubuntu/data-pipeline

RUN python3 -m venv .venv

ENV VIRTUAL_ENV="/home/ubuntu/data-pipeline/.venv"
ENV PATH="${VIRTUAL_ENV}/bin:$PATH"

RUN pip install -e .[test]
CMD ["breweries", "--run-all"]