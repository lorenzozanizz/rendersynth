# Tutorials: Onboarding

Welcome to the **Rendersynth** tutorials. This section guides you through building synthetic datasets from setup to advanced generation workflows.

##  Tutorial Structure

This tutorial series is organized into a logical progression:

1. **[Classes & Entities](01_classes_entities.md)** – Define your dataset schema with custom classes and multi-object grouping
2. **[Create Pipeline](02_create_pipeline.md)** – Build your first randomization pipeline with distributions and operations
3. **[Labeling](03_labeling.md)** – Set up annotation formats and label generation strategies
4. **[Distributions](04_distributions.md)** – Master probability distributions for scene parameters
5. **[Create Labeling Formats](05_new_label_format.md)** – Define custom label export formats
6. **[Shader Randomization](06_shader_randomize.md)** – Randomize material properties and textures
7. **[Common Pitfalls](07_common_pitfalls.md)** – Avoid gotchas and optimize your pipelines
8. **[Matching Labeling and Formats](08_matching_labeling_generation.md)** – Align your pipeline output with label structure
9. **[Batch Generation](09_batch_generation.md)** – Configure and run large-scale dataset renders
10. **[Preview](10_preview.md)** – Inspect outputs, bounding boxes, and statistics in real-time
11. **[Importing and Exporting](11_import_export.md)** – Load configurations and export datasets
12. **[Labeling Rigs and Keys](12_labeling_rigs.md)** – Advanced labeling techniques and rig management

---

##  Recommended Learning Paths

### For Beginners
Start simple and build understanding:
1. [Classes & Entities](01_classes_entities.md) – Understand the data model
2. [Create Pipeline](02_create_pipeline.md) – Build your first pipeline
3. [Labeling](03_labeling.md) – Add output labels
4. [Batch Generation](09_batch_generation.md) – Render your first dataset

### For Intermediate Users
Dive into the core features:
1. [Distributions](04_distributions.md) – Advanced randomization
2. [Shader Randomization](06_shader_randomize.md) – Material variation
3. [Matching Labeling and Formats](08_matching_labeling_generation.md) – Alignment
4. [Preview](10_preview.md) – Quality control

### For Advanced Users
Optimize and extend:
1. [Common Pitfalls](07_common_pitfalls.md) – Best practices
2. [Create Labeling Formats](05_new_label_format.md) – Custom export formats
3. [Labeling Rigs and Keys](12_labeling_rigs.md) – Advanced setups
4. [Importing and Exporting](11_import_export.md) – Version control and sharing

---

## 🔗 Quick Links

| Topic | Page |
|-------|------|
| **Schema Definition** | [Classes & Entities](01_classes_entities.md) |
| **Pipeline Building** | [Create Pipeline](02_create_pipeline.md) |
| **Randomization** | [Distributions](04_distributions.md), [Shader Randomization](06_shader_randomize.md) |
| **Output & Labels** | [Labeling](03_labeling.md), [Create Labeling Formats](05_new_label_format.md) |
| **Quality & Debugging** | [Preview](10_preview.md), [Common Pitfalls](07_common_pitfalls.md) |
| **Workflows** | [Batch Generation](09_batch_generation.md), [Importing and Exporting](11_import_export.md) |

---

## Architecture Deep Dive

For a deeper understanding of how Rendersynth works internally, see the **Architecture** section:

- [Architecture Overview](../architecture/architecture_overview.md)
- [Distributions System](../architecture/distributions.md)
- [Label Generation](../architecture/label_gen.md)
- [Pipeline Serialization](../architecture/pipeline_serialization.md)
- [Pipeline Execution](../architecture/pipeline_execution.md)
- [Preview System](../architecture/preview.md)
- [User Interface Design](../architecture/ui.md)

---

##  Examples & Templates

Ready-to-use projects demonstrating complete workflows:

- **[Product Classification](../examples/01_prod_classification.md)** – Retail product detection dataset
- **[Image Segmentation](../examples/02_image_segmentation.md)** – Semantic segmentation with custom masks
- **[Pose Estimation](../examples/03_pose_estimation.md)** – Multi-object pose with keypoints

---

## Need Help?

- **Getting Started?** [Setup Guide](../setup.md)
- **Want Architecture Details?**  [Architecture Overview](../architecture/architecture_overview.md)
- **Looking for Examples?**  [Examples Section](../examples/00_landing.md)
- **Have Questions?** [Email Support](mailto:zanilorenzopm@gmail.com)

---

**Pro Tip**: Each tutorial page includes code examples, UI screenshots, and practical exercises. Work through them sequentially for best results.

Happy generation! 🎬✨