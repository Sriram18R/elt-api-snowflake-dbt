{%- set json_parse_exception = config.get('json_parse_exception') or False -%}

{#- Macro to parse JSON strings -#}
{% macro parse_json(json_string) %}
  {% if json_string %}
    {% try %}
      {{ json_string }}
    {% except %}
      {%- if json_parse_exception -%}
        {{ exceptions.raise_compiler_error('Failed to parse JSON: ' ~ json_string) }}
      {%- else -%}
        null
      {%- endif -%}
    {% endtry %}
  {% else %}
    null
  {% endif %}
{% endmacro %}
