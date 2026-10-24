# Validation record — v1.0.0

Tested on 2026-10-24 with Blender **5.1.0**, Apple Silicon macOS. Other Blender releases have not been independently tested. Python helpers use the standard library; Pillow was available for PNG contact sheets.

## Executed checks

- Nine Python contract tests passed: dimensions, front row sums, duplicate/unsafe IDs, non-finite coordinates, handle fit, existing-scene mode and geometry identity independent of camera changes.
- Real-Blender integration passed: synthetic model generation, design dimensions, three wardrobe fronts, four drawer fronts, ten slats sharing one mesh, and a 45-degree panel edge.
- A camera bound to a timeline marker was deliberately introduced. Rendering selected cameras cleared that binding in the output copy, produced different views, preserved the source file and kept the base geometry fingerprint unchanged.
- Repeating the same preview returned a cache hit. A changed camera invalidated the cache. A changed cabinet dimension was refused until the model was rebuilt.
- Final rendering without explicit camera IDs was rejected. A selected final render produced only that camera's image.
- A separate private existing-model compatibility test produced three 640px previews with unchanged base geometry. That source, its images and all personal paths are excluded from this repository.
- The synthetic model contained 61 base mesh objects and 1,604 base triangles. Base topology checks found no errors. The installed asset checker reported zero per-mesh render-profile errors. Accepted warnings: 61 meshes had no UVs (uniform white-model materials), and 38 meshes did not individually sit at Z=0 (parts within an assembly). This was **not** a full scene intersection or CAD-fidelity audit.

## Observed local timings

| Operation | Elapsed |
|---|---:|
| Synthetic model build | about 0.5 s |
| Four 640px Workbench camera previews plus contact sheet | about 0.8 s |
| Three 640px previews of a separate existing scene | about 0.9 s |
| One 2400×1800 Cycles/Metal image, 128 adaptive samples maximum | about 15 s |

Single local runs; timings include Blender process execution and relevant output assembly. They exclude reading CAD, interpreting dimensions, authoring the project configuration and human review. These are execution observations, **not** an end-to-end speed comparison or a measured token reduction claim.

## Review limits

Visual checks covered synthetic proofs/final output and the private scene compatibility proofs. Precise CAD fidelity requires the actual source drawings and dimensional review. Framing checks use projected bounding boxes; they do not prove absence of occlusion or perspective stretching. Geometry comparison covers base mesh coordinates, faces and world transforms, not evaluated modifier output.

The local automation environment required permission to access graphics devices outside its shell sandbox. Rendering tests ran with that access. No lifecycle hooks, credentials, cloud rendering or automatic publishing are required by the skill.
