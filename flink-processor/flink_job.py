import os
from pyflink.datastream import StreamExecutionEnvironment
from pyflink.table import StreamTableEnvironment, EnvironmentSettings
from pyflink.table.expressions import col,lit

def main():
    print("Starting flink job")
    #initialize streaming and table environments
    env = StreamExecutionEnvironment.get_execution_environment()
    settings = EnvironmentSettings.new_instance().in_streaming_mode().build()
    t_env = StreamTableEnvironment.create(env, settings)

    #connector location from dockerfile installation/ optional since flink automatically scans the flink/lib folder
    kafka_jar = "/opt/flink/lib/flink-sql-connector-kafka.jar"
    t_env.get_config().get_configuration().set_string("pipeline.jars", f"file://{kafka_jar}")
    
    #create table and map it to 'exchange_rates' kafka topic
    t_env.execute_sql("""
        CREATE TABLE fx_rates (
            firm STRING,
            currency STRING,
            buy DECIMAL(18, 8),
            sell DECIMAL(18, 8)
        ) WITH (
            'connector' = 'kafka',
            'topic' = 'fx_rates',
            'properties.bootstrap.servers' = 'kafka:9092',
            'properties.group.id' = 'flink-forex-analyzer',
            'scan.startup.mode' = 'earliest-offset',
            'format' = 'json'
        )
    """)

    #sink table
    t_env.execute_sql("""
        CREATE TABLE best_deals_sink (
            currency STRING,
            deal_type STRING,
            rate DECIMAL(18, 8),
            firm STRING
        ) WITH (
            'connector' = 'print'
        )
    """)

    fx_rates = t_env.from_path("fx_rates")

    #get extremes per currency extremes, aliased columns avoid name collisions on join
    best_sell = (
        fx_rates
        .where(col("sell") > 0)
        .group_by(col("currency"))
        .select(col("currency").alias("bs_currency"), col("sell").min.alias("best_sell"))
    )

    best_buy = (
    fx_rates
    .where(col("buy") > 0)
    .group_by(col("currency"))
    .select(col("currency").alias("bb_currency"), col("buy").max.alias("best_buy"))
)

    #join raw rows back to the extremes to recover firm(s); equality join keeps every tie
    lowest_sell_deals = (
        fx_rates
        .join(best_sell, col("currency") == col("bs_currency"))
        .where(col("sell") == col("best_sell"))
        .select(
            col("currency"),
            lit("LOWEST_SELL (best to buy from)").alias("deal_type"),
            col("sell").alias("rate"),
            col("firm"),
        )
    )

    highest_buy_deals = (
    fx_rates
    .join(best_buy, col("currency") == col("bb_currency"))
    .where(col("buy") == col("best_buy"))
    .select(
        col("currency"),
        lit("HIGHEST_BUY (best to sell to)").alias("deal_type"),
        col("buy").alias("rate"),
        col("firm"),
    )
)

    best_deals = lowest_sell_deals.union_all(highest_buy_deals)

    table_result = best_deals.execute_insert("best_deals_sink")
    table_result.wait()
 
if __name__ == '__main__':
    main()