{#- Macro for generating audit columns -#}
{% macro audit_columns() %}
  created_at: '{{ run_started_at }}',
  updated_at: '{{ run_started_at }}',
  dbt_run_id: '{{ run_id }}'
{% endmacro %}
