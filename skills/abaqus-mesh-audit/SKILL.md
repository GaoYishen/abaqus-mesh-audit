---
name: abaqus-mesh-audit
description: Audit flat Abaqus INP linear triangle and quadrilateral meshes for orientation, degenerate elements, sampled Q4 Jacobians, small angles, edge-length ratio, coincident nodes and nonmanifold edges. Use for read-only 2D mesh checks, not automatic repair or 3D/UEL validation.
---

# Abaqus 2D mesh audit

Resolve the repository root two levels above this skill folder. Keep the complete repository. Run `python mesh_audit.py INPUT.inp --output audit.json` from the root or invoke the absolute script path.

Check the supported input first: explicit Cartesian XY nodes (z=0), CPE3/CPS3 or CPE4/CPE4R/CPS4/CPS4R, with unique node and element labels in one scope. Flatten includes, Parts and Instances outside this tool before auditing. It rejects unsupported element types and coordinate generation instead of silently projecting a 3D mesh or guessing connectivity. Material names do not alter the checks.

Explain the selected thresholds: minimum angle defaults to 20°, maximum longest/shortest edge ratio to 10. These are configurable screening values, not universal finite-element accuracy criteria. Area and Jacobian degeneracy tolerances scale with element edge length squared. Q4 checks sample four Gauss points, corners and center.

Report issue kinds and node/element IDs. Boundary edges include exterior boundaries and holes; never label all of them broken material interfaces. Coincident-node detection is exact, not a near-contact search. The tool does not check all geometric overlaps, provide full interface ownership proof, assess UEL constitutive state, or certify solution accuracy.

Exit 0 means the declared geometric screening checks pass, 1 means mesh issues were found, and 2 means unsupported/invalid input or output failure. JSON is strict and output refuses overwrite. Do not repair input files, edit a solver, run Abaqus, or broaden the supported input claim implicitly.
