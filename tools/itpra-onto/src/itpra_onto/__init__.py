"""itpra-onto: the ITPRA ontology-as-code pipeline.

Projects the vocabulary (``schema.yaml``, ``entities.yaml``, ``relationships.yaml``,
``terms/*.yaml`` under ``[paths] ontology_dir``) into RDF named graphs (ADR 0041);
validates the result against the SHACL shapes under ``shapes/`` and checks their
parity with the linter (ADR 0042); and writes canonical, digest-addressed artefacts
under ``dist/`` (ADR 0043). ``itpra-onto --help`` lists the commands.
"""

__version__ = "5.0.0"  # the release's version: equal to schema.yaml ontology_version (ADR 0044)
