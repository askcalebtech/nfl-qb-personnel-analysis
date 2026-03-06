#!/bin/bash

export project_path="/Users/calebsherman/projects/other/nfl-qb-personnell-analysis"
export data_path="/Users/calebsherman/projects/other/nfl-qb-personnell-analysis/data/raw"

# Use whatever local python version you have, or comment out if using 3.9.10
export PYENV_VERSION="3.9.13"
python --version

# User whatever local spark version you have
export spark_version="3.5.0"

echo "Project Path: " ${project_path}
echo "Data Path: " ${data_path}

export job_folder="jobs"
export job_name="explore_data"

# Before launching pyspark
make clean-build
make build

spark-submit \
--master local \
--packages org.apache.spark:spark-avro_2.12:${spark_version} \
--conf spark.driver.memory=24g \
--conf spark.executor.memory=24g \
--conf spark.executor.instances=3 \
--conf spark.executor.cores=3 \
--conf "spark.driver.host=127.0.0.1" \
--conf "spark.driver.bindAddress=127.0.0.1" \
--conf "spark.driver.extraJavaOptions=-XX:ReservedCodeCacheSize=512m -XX:+UseCodeCacheFlushing -Dlog4j.configuration=file:${project_path}/log4j.properties" \
--conf "spark.executor.extraJavaOptions=-XX:ReservedCodeCacheSize=512m -XX:+UseCodeCacheFlushing -Dlog4j.configuration=file:${project_path}/log4j.properties" \
--conf spark.sql.shuffle.partitions=12 \
--conf spark.hadoop.fs.file.impl=org.apache.hadoop.fs.RawLocalFileSystem \
--conf spark.sql.files.ignoreCorruptFiles=true \
--conf spark.sql.sources.ignoreCorruptFiles=true \
--conf spark.serializer=org.apache.spark.serializer.KryoSerializer \
--conf spark.sql.adaptive.enabled=true \
--conf spark.sql.adaptive.coalescePartitions.enabled=true \
--py-files ${project_path}/dist/jobs.zip ${project_path}/dist/spark_session.py \
--job ${job_folder}.${job_name}  \
--add-py-files ${project_path}/dist/jobs.zip