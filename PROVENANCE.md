# Provenance

This public package was newly written to make a local two-dimensional mesh-checking workflow portable. It uses standard polygon geometry, vector angles, edge ownership and bilinear Q4 mapping derivatives. It is not a copy of a private solver, UEL implementation or commercial program.

All INP examples and tests are synthetic. They contain only small explicit node and element lists. No research microstructure, FOR source, material parameter contract, solver output or user credential is included.

The scope is deliberately narrower than a complete Abaqus input reader. Unknown element types and supported-scope violations are rejected; the report is a screening result, not an Abaqus or mesh-accuracy certification. Abaqus is a third-party product name; this project is independent and unaffiliated.

Code, documentation, synthetic examples and skill instructions in this repository are released under the included MIT License.
