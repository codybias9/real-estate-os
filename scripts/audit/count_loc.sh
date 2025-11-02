#!/bin/bash
# Count lines of code by directory

echo "Directory,Python_LOC,SQL_LOC,YAML_LOC,MD_LOC,Total_Files"

for dir in api ml dags database_schema document_processing graph_analytics offer_generation evidence docs; do
  if [ -d "$dir" ]; then
    py_loc=$(find "$dir" -name "*.py" -exec wc -l {} + 2>/dev/null | tail -1 | awk '{print $1}' || echo 0)
    sql_loc=$(find "$dir" -name "*.sql" -exec wc -l {} + 2>/dev/null | tail -1 | awk '{print $1}' || echo 0)
    yaml_loc=$(find "$dir" -name "*.yaml" -o -name "*.yml" -exec wc -l {} + 2>/dev/null | tail -1 | awk '{print $1}' || echo 0)
    md_loc=$(find "$dir" -name "*.md" -exec wc -l {} + 2>/dev/null | tail -1 | awk '{print $1}' || echo 0)
    total_files=$(find "$dir" -type f | wc -l)
    echo "$dir,$py_loc,$sql_loc,$yaml_loc,$md_loc,$total_files"
  fi
done
