#!/bin/bash
# Classify DAGs as real or stub based on operator usage

echo "DAG_File,Has_EmptyOperator,Has_PythonOperator,Has_BashOperator,LOC,Classification"

for dag in dags/*.py; do
  filename=$(basename "$dag")

  # Count operators
  empty_ops=$(grep -c "EmptyOperator\|DummyOperator" "$dag" || echo 0)
  python_ops=$(grep -c "PythonOperator" "$dag" || echo 0)
  bash_ops=$(grep -c "BashOperator" "$dag" || echo 0)
  loc=$(wc -l < "$dag")

  # Classify
  if [ "$empty_ops" -gt 0 ] && [ "$python_ops" -eq 0 ] && [ "$bash_ops" -eq 0 ]; then
    classification="STUB"
  elif [ "$loc" -lt 100 ]; then
    classification="MINIMAL"
  else
    classification="REAL"
  fi

  echo "$filename,$empty_ops,$python_ops,$bash_ops,$loc,$classification"
done
