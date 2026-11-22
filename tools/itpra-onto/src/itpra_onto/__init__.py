"""itpra-onto: the ITPRA ontology-as-code pipeline.

Projects the vocabulary (``schema.yaml``, ``entities.yaml``, ``relationships.yaml``,
``terms/*.yaml`` under ``[paths] ontology_dir``) and, when a consumer configures one,
its requirement registries (``[overlay] requirements_glob``) into RDF named graphs
(ADR 0041); validates the result against the SHACL shapes under ``shapes/`` and
checks their parity with the consumer's linter (ADR 0042); and writes canonical,
digest-addressed artefacts under ``dist/`` (ADR 0043). ``itpra-onto --help`` lists
the commands; ``release`` is not implemented yet.
"""

__version__ = "0.1.0"
