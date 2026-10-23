# LEAF Guardian: Project Proposal

**An autonomous, low-cost plant health monitoring system for small environmental restoration nonprofits**

**Author:** Aarush Sundararajan
**Partner organization:** CA LEAF (California native-plant restoration)
**Competition targets:** Regeneron Science Talent Search · ISEF (Spring 2027)
**Status:** Version 1 in development (October 2026)

---

## 1. Summary

Small environmental nonprofits restore native habitat by planting thousands of native plants. However, they can only check on those plants a few times a year, by walking each site and judging plant health by eye. Plants that start to struggle between visits often die before anyone notices.

**LEAF Guardian** is a low-cost drone system that surveys a planting site on its own. It photographs the site on a grid, stitches the photos into one map, scores the health of every zone, and produces an easy-to-read report showing where intervention is needed. The goal is to give a coordinator with no special training a complete, repeatable site health assessment for a one-time hardware cost of roughly **$400–$660**. Professional surveys and commercial multispectral drones cost thousands to tens of thousands of dollars.

### Mission statement

> LEAF Guardian's mission is to make plant health monitoring affordable and accessible for small environmental organizations, providing a simple, autonomous survey tool that helps volunteers find struggling plants early and spend more of their time restoring habitat.

### Elevator pitch

> Existing ways to monitor restoration sites either take a lot of volunteer time (manual surveys) or cost far more than a small nonprofit can afford (professional drone services and commercial equipment). As a result, stressed plants are often found too late. LEAF Guardian lets any volunteer, with no botanical or technical training, run a complete site health assessment in a fraction of the time, using autonomous drone flight and automated health analysis.

### In plain language

A small flying camera travels back and forth over a planting area and takes pictures at regular spots, including pictures in light the human eye can't see. The pictures are then combined into one complete map of the area. The computer checks each section of the map for signs that plants are healthy, stressed, or dying, and produces a simple color-coded map and a short list of which areas need care first.

---

## 2. Problem statement

> LEAF Guardian helps small environmental restoration nonprofits monitor the health of their native plant sites by autonomously surveying planting areas with a low-cost drone and producing an easy-to-read, zone-by-zone health map with targeted recommendations. This lets coordinators identify which plants need intervention before they die, without expensive equipment, professional operators, or a large investment of volunteer time.

### 2.1 Who has this problem

The primary user is a **restoration site coordinator** at a small environmental nonprofit such as CA LEAF. Organizations like LEAF restore native plant communities to sustain keystone species for pollinators and birds. A typical coordinator:

- manages roughly 5–20 active planting sites across a region
- works with a small annual budget (roughly $30,000–$150,000), most of which goes to plants and volunteer events
- relies on a handful of trained volunteers plus occasional untrained participants
- monitors sites by walking them and assessing each plant by eye
- can realistically visit each site only 1–3 times per year
- has no sensors, no satellite subscription, and no budget for either

Secondary users include community gardens, city and state parks departments, and university research groups that manage small planted areas.

### 2.2 Why it matters: cause and effect

Limited funding means fewer people, less training, and less frequent evaluation. Every hour spent searching for problems is an hour not spent fixing them. Meanwhile, plant decline follows a predictable path:

| Time after stress begins | Plant condition | Can it be saved? |
|---|---|---|
| ~Month 2 | Early water stress, detectable in near-infrared light but not visible to the eye | Yes, easily |
| ~Month 3 | Slight yellowing | Yes, a short irrigation fix |
| ~Month 4 | Browning, root damage | Unlikely |
| ~Month 6 | Coordinator's next visit; the plant is dead | No |

With visits months apart, **the entire window where intervention would work can pass unnoticed.** The organization loses plants, the volunteer labor that went into planting them, and grant-funded progress toward its habitat goals. If nothing changes, small restoration groups keep losing plantings to problems that were fixable when they began.

### 2.3 Why this hasn't been solved

The tools that exist today were built for agriculture, government, or large enterprises, not for small volunteer-run groups. Each falls short in a specific way (see Section 3). The closest real competitor is **not a technology at all. It is a volunteer walking the site.**

---

## 3. Existing solutions (competitive analysis)

| Solution | Cost | Training required | Resolution | Update frequency | Why it doesn't solve the problem |
|---|---|---|---|---|---|
| **Manual field inspection** (current method) | Volunteer time | Moderate botanical knowledge to recognize stress | Plant-level, but subjective | 1–3 visits/year per site | Slow, doesn't scale past a few sites, leaves no consistent or spatial record, and can't detect stress before it is visible |
| **Volunteer surveys** | Low | Varies widely | Plant-level, inconsistent | Irregular | Even less consistent than trained inspections |
| **Satellite imagery** (Sentinel-2 free; Planet Labs ~$180+/mo) | Free to ~$1,500/mo | GIS and remote-sensing expertise | 3–10 m per pixel | Daily to every 5 days, often blocked by clouds and coastal fog | One pixel (9–100 m²) is larger than a seedling cluster, so it can't identify *which* plants are failing |
| **Commercial agricultural drone** (e.g. DJI Agras T40) | ~$20,000–$26,500 | FAA Part 107 certification and complex mission planning | Centimeter-level | On demand | Costs more than many small nonprofits' annual budget. Heavy aircraft with serious crash risk. Built for large commercial farms |
| **Professional survey service** (e.g. Zeitview) | ~$300–$5,000 per survey | None (operators run everything) | High | Requires 1–3 weeks of scheduling | Costs can exceed $10,000 per year for regular monitoring, and the lead time makes frequent check-ins impractical |
| **LEAF Guardian** | **~$400–$660 one-time** | Minimal: set the drone down and run one script | Plant-level (drone photos) | On demand, any day | Designed specifically for small, low-budget volunteer organizations |

**Where LEAF Guardian is strongest:** cost, ease of use, and on-demand availability.
**Where it still needs to improve:** proven accuracy against expert assessment, flight time and range on large sites, and near-infrared (early stress) detection, which is planned but not yet integrated into the drone.

---

## 4. Proposed solution

### 4.1 System workflow

```
 Plan grid ─► Autonomous flight ─► Capture photo ─► Stitch into ─► Score each ─► Report with
 over site    (lawnmower path)      at each point    one site map    zone 0–1     tiers + actions
```

1. **Flight planning.** The site is divided into a grid of waypoints.
2. **Autonomous flight.** The drone flies a lawnmower pattern (up one column, across, down the next) with no pilot input.
3. **Image capture.** A photo is taken at every waypoint and named by its grid position (`row.col.jpg`).
4. **Image stitching.** The photos are assembled into one composite map of the site.
5. **Health analysis.** Every zone gets a 0–1 health score from visible-light (RGB) indices, and later from near-infrared (NDVI).
6. **Report generation.** A color-coded map and a plain-text report classify each zone and recommend an action.

| Tier | Score | Recommended action |
|---|---|---|
| Healthy | ≥ 0.65 | No intervention required |
| Monitor | 0.40–0.65 | Visual inspection within 2 weeks |
| Action Needed | 0.20–0.40 | Prioritize irrigation; inspect for pests or disease within 1 week |
| Critical | < 0.20 | Immediate intervention |

### 4.2 Health analysis method

- **RGB analysis (implemented).** Each zone is scored with two independent indices that are then averaged:
  - an HSV pixel classification that counts green (healthy), yellow (early stress), and brown (dead or dry) pixels, while excluding sky, shadow, and desaturated surfaces such as water
  - **VARI** (Visible Atmospherically Resistant Index; Gitelson et al., 2002)
- **NDVI analysis (planned for the drone).** Near-infrared imaging can reveal stress before it is visible. The full NDVI pipeline has already been built and validated on Sentinel-2 satellite data. The next step is adding a NoIR camera to the drone itself.
- **Machine-learning classifier (future).** A transfer-learning model will replace hand-tuned color thresholds. It will be pretrained on field-condition plant-stress datasets and fine-tuned on imagery from CA LEAF sites.

### 4.3 Hardware plan

| Stage | Platform | Role |
|---|---|---|
| Completed | DJI Tello | Proved autonomous grid flight, photo capture, stitching, and reporting work end to end. Limited by a forward-only camera and poor color. |
| Completed | DJI Mini 4K | High-quality downward photos for testing the analysis pipeline. No autonomous capability, so it is flown manually. |
| Proposed | Custom F450 quadcopter (Pixhawk + GPS) with Raspberry Pi and NoIR camera | Combines laptop-controlled autonomy, GPS waypoints, and a downward RGB + near-infrared camera. Missions can be tested in simulation before flight. |

---

## 5. Objectives and Version 1 success criteria

Version 1 is a **proof of concept**. It succeeds if a reviewer can watch a demonstration and agree that *this project works*:

1. **Autonomous flight works.** The drone completes a pre-planned grid survey without manual control.
2. **Mapping works.** The photos from that survey are stitched into a single, correctly ordered site map.
3. **Plant health analysis works.** Each zone receives a health score and tier that match what a human sees in the image.
4. **The report is useful.** The output clearly identifies which zones need attention and what to do.

**Version 1 demonstration (5 minutes):** autonomous flight → photos captured → stitched map → health map displayed → report with recommendations.

### Later versions

| Version | Goal | Key features |
|---|---|---|
| V2: Autonomous data collection | Reduce manual effort | GPS outdoor flight, onboard NDVI camera, overlap-aware stitching, multiple sites |
| V3: Smarter analysis | Improve accuracy | ML stress classifier, RGB + NDVI cross-checking, confidence scores |
| V4: Real-world deployment | Something organizations can use day to day | Web dashboard, historical tracking, multiple locations, user accounts, grant-ready impact reports |

---

## 6. User journey

**Today (without LEAF Guardian)**

1. A volunteer arrives at the site.
2. They walk the area on foot and check plants one by one (about an hour or more per site, by the author's estimate; to be confirmed with CA LEAF).
3. They try to spot stress signs, which requires botanical knowledge many volunteers don't have.
4. They record findings by hand or with phone photos, then report back to a coordinator.
5. The coordinator assembles a plan. Stressed areas that were missed or forgotten get no care, and stress that isn't yet visible is never detected.

**With LEAF Guardian**

1. A volunteer sets the drone on the ground, connects a laptop, and runs the survey (about 5 minutes of setup).
2. The drone flies the site autonomously, photographing every waypoint (estimated 20–25 minutes; to be confirmed by testing).
3. The software stitches the images and produces a color-coded health map and a report.
4. The coordinator sees immediately which zones need attention and sends volunteers there.
5. Every survey is standardized and saved, so health can be tracked over time.

**Value:** less volunteer time spent searching, less botanical training required to find problem areas, consistent records, and (with NDVI) earlier detection. In Version 1 the system shows *where* attention is needed. Later versions aim to also suggest *why*.

---

## 7. Evaluation plan and success metrics

Claims such as "lower cost," "less training," and "earlier detection" will be backed by measurement, not assumed.

| Metric | How it will be measured |
|---|---|
| **Survey completion time** | Time a full LEAF Guardian survey (setup + flight + analysis) against a manual walk-through of the same site |
| **Volunteer effort** | Person-hours per site survey, before and after |
| **Training required** | Time for a first-time volunteer to run a survey successfully, compared with time to learn manual stress identification |
| **Accuracy** | Agreement between LEAF Guardian zone tiers and an expert's assessment of the same zones (percent agreement / confusion matrix) |
| **Early-detection lead time** | Controlled test: let a sample plant patch go without water, survey it regularly, and record how many days earlier the system flags stress than a visual inspection does |
| **Cost** | Total hardware and software cost compared with the alternatives in Section 3 |

### Customer validation

Feedback will be gathered from **at least 3–5 organizations**, with the goal of learning, not selling. Candidates include CA LEAF, a local ecology center, parks departments, community gardens, and university drone or ecology research groups. Questions:

- How do you currently monitor plant health?
- What tools do you use?
- What is the hardest part, and how much time does it take?
- Would a system like this actually be useful to you?
- What concerns would you have about using it?

---

## 8. Timeline

| Period | Focus |
|---|---|
| Summer 2026 (done) | Satellite NDVI/RGB pipeline, photo stitcher, RGB health scoring and reports, Tello autonomous grid flights, Mini 4K image testing |
| Fall 2026 | Software-only work: confidence scoring, labeling tool for training data, higher-resolution aerial (NAIP) baseline, customer outreach |
| Winter break 2026–27 | Build and calibrate the custom F450 drone, testing missions in simulation first |
| Spring 2027 | Outdoor GPS surveys at CA LEAF sites, NDVI integration, controlled early-detection experiment, evaluation against expert assessment |
| Following year | ML classifier trained on collected field data, research paper, public dataset release |

---

## 9. Budget

| Item | Est. cost | Status |
|---|---|---|
| DJI Tello Boost Combo | ~$150 | Owned |
| DJI Mini 4K + microSD | ~$299 | Owned |
| F450 drone kit (frame, motors, ESCs, Pixhawk flight controller, GPS, battery, RC transmitter) | ~$396 | Proposed |
| Raspberry Pi 4, NoIR camera, NIR filter, microSD, telemetry radio, camera mount, LiPo bag | ~$182 | Proposed |
| Spare battery, RGB Pi camera, spare props, multimeter | ~$80 | Recommended |
| **Custom build total** | **~$660** | |

For comparison: commercial multispectral drone systems start around $18,000, and professional surveys cost $300–$5,000 *each*.

---

## 10. Risks and mitigation

| Risk | Mitigation |
|---|---|
| Custom drone build takes longer than planned | Keep build work in winter break; continue software-only work in fall; Mini 4K or a waypoint-capable consumer drone as a fallback |
| Color-based scoring is unreliable under different lighting and species | Combine two indices (HSV + VARI), add confidence flags, add NDVI, and later replace thresholds with a trained model |
| Not enough labeled training data for ML | Build a labeling tool so every flight produces labeled data; use transfer learning from existing field datasets |
| Outdoor wind, GPS drift, or battery limits on larger sites | GPS-based flight controller, simulator testing, battery checks before each mission, smaller survey blocks |
| Safety and regulations | FAA registration, RC failsafe required to arm, LiPo safety procedures, flights only where permitted |

---

## 11. Expected outcomes

- A working, documented, open-source system that a small nonprofit can operate for a one-time cost of a few hundred dollars.
- Measured evidence of time saved, training reduced, and stress detection accuracy at real CA LEAF restoration sites.
- **A labeled California native-plant health image dataset.** No public dataset currently pairs California restoration species with plant health labels. Releasing one would be a contribution beyond the device itself.
- A research paper documenting the method, the comparison against satellite and manual monitoring, and the results.

---

*Technical details, design iterations, and code: see the main [README](../README.md).*
