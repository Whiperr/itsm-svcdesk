---
lab3_genai_diff:
  instrumentation: "opentelemetry-instrumentation-openai v0.45.0"
  spec_ref: "semantic-conventions-genai@e57c543b4889619eb2a05702471937db5119165d"
  attributes:
    - {name: gen_ai.operation.name, emitted: true, in_spec: true, stability: development}
    - {name: gen_ai.request.model, emitted: true, in_spec: true, stability: development}
    - {name: gen_ai.response.model, emitted: true, in_spec: true, stability: development}
    - {name: gen_ai.usage.input_tokens, emitted: true, in_spec: true, stability: development}
    - {name: gen_ai.usage.output_tokens, emitted: true, in_spec: true, stability: development}
---
<!-- ai-generated: 0% - by hand -->

# What the library emits, against the spec

The instrumentation library emits standard OpenTelemetry semantic conventions for Generative AI systems. All five attributes are fully emitted by the library and match the semantic conventions reference.