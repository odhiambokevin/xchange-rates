FROM flink:2.2-java17

ARG CONNECTOR_VERSION=5.0.0-2.2

USER root

#python and pip if you haven't already for pyflink
RUN apt-get update -y && \
    apt-get install -y --no-install-recommends python3 python3-pip python3-dev python3.12-venv wget && \
    rm -rf /var/lib/apt/lists/*

#pyflink requires python to point to python3
RUN ln -s /usr/bin/python3 /usr/bin/python

#create virtual environment to avoid error from PEP668 that prevents install into system python
RUN python3 -m venv /opt/venv

#make use of the virtual environment by default
ENV PATH="/opt/venv/bin:${PATH}"

#install pyflink library version matching flink version exactly
RUN pip3 install --no-cache-dir apache-flink==2.2.0

#downloading the exact connector jar into flink dedicated library directory renamed using -o flag
RUN wget https://repo1.maven.org/maven2/org/apache/flink/flink-sql-connector-kafka/${CONNECTOR_VERSION}/flink-sql-connector-kafka-${CONNECTOR_VERSION}.jar -O /opt/flink/lib/flink-sql-connector-kafka.jar

# Create your project directory inside the container
WORKDIR /app

COPY flink_job.py wait-for-it.sh ./

RUN chmod +x wait-for-it.sh

#default to flink's user that is created by image
USER flink

CMD ["sh", "-c", "./wait-for-it.sh -s -t 30 $KAFKA_SERVER -- flink run -py flink_job.py"]