![GitHub last commit](https://img.shields.io/github/last-commit/odhiambokevin/xchange-rates)

# Exchange Rates Pipeline

## Introduction
This is an implementation of an ELT pipline workflow that compares Foreign Exchange Rates among financial institutions.

> **NOTE:** The code is for educational and demo purposes ONLY and should not be used for any extralegal activities. Focus is on the pipeline architecture.

## How it works
A stream of different forex exchange rates are pulled from credible sources and produced in a kafka topic. Flink reads from this Kafka topic and using a tumbling windows schedule compares who offers the best rates. A tumbling window is used so data is always the latest available version.

Flink then sinks the best rates directly to postgres. Since the throughput is low, there is no streaning spike that can crash postgres.

Airflow is used to orchestrate the Kafka schedule since it is not a streaming event.

dbt is introduced to show how it can be used in the integration at scale if downstream analytics and users will need data at various granularity.

Everything runs in a containerized environment.