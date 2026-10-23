# LEAF Guardian - Initial Research

**Low-cost drone monitoring of native plant health at restoration sites.**

LEAF Guardian is a drone-based system that surveys native-plant restoration sites and produces a zone-by-zone plant health map with plain-English recommendations. A drone flies a pre-planned grid over a planting area and photographs each waypoint. The software stitches those photos into one composite map, scores every grid cell for vegetation health, and writes a report that says which zones need attention and what to do about them.

Partner organization: **CA LEAF**, a California native-plant restoration nonprofit (50 volunteer hours, 200 native plants planted).

📄 **[Read the full project proposal →](docs/PROJECT_PROPOSAL.md)**

---

## Table of contents

1. [The problem](#1-the-problem)
2. [Existing solutions and why they fall short](#2-existing-solutions-and-why-they-fall-short)
3. [What LEAF Guardian does](#3-what-leaf-guardian-does)
4. [Design iterations: software](#4-design-iterations-software)
5. [Design iterations: hardware](#5-design-iterations-hardware)
6. [Next steps](#6-next-steps)
7. [Repository layout and setup](#7-repository-layout-and-setup)

---

## 1. The problem

Small environmental restoration nonprofits plant thousands of native plants every year, but they have almost no way to tell which ones are struggling until it's too late.

A typical **restoration site coordinator**:

- manages 5–20 active planting sites across a region
- has an annual budget of roughly $30,000–$150,000, most of which goes to plants and volunteer events
- works with 2–8 trained volunteers plus occasional untrained helpers
- monitors sites by walking them and judging each plant by eye
- can realistically visit each site only 1–3 times a year
- has no sensors, no satellite subscription, and no budget for either

That visit schedule doesn't match how plants die. A typical decline looks like this:

| Time | What's happening to the plant | Can it still be saved? |
|---|---|---|
| Month 2 | Early drought stress, visible in near-infrared but not to the eye | Yes, easily |
| Month 3 | Slight yellowing | Yes, a ~20-minute irrigation fix |
| Month 4 | Browning, root damage | Unlikely |
| Month 6 | Coordinator visits; the plant is dead | No |

**The whole 60–90 day window where intervention would work goes by unnoticed.** Restoration groups lose plants, volunteer effort, and grant money to problems that were fixable when they started.

> **Problem statement:** LEAF Guardian helps small environmental restoration nonprofits monitor the health of their native plant sites by autonomously surveying planting areas with a low-cost drone and producing an easy-to-read, zone-by-zone health map with actionable recommendations. Coordinators can then see which plants need intervention before they die, without expensive equipment, professional operators, or excessive volunteer time.

---

## 2. Existing solutions and why they fall short

| Alternative | Cost | Why it doesn't work for a small nonprofit |
|---|---|---|
| **Manual field survey** (today's default) | Volunteer time | Needs botanical expertise most volunteers lack. Doesn't scale past a few sites. Leaves no spatial or repeatable record, and misses early stress entirely. |
| **Professional aerial survey** (e.g. Zeitview, DroneBase) | $300–$5,000 per survey | Adds up to $10K–$90K a year for a multi-site organization. 1–3 week scheduling lead time and no ongoing monitoring. |
| **Satellite imagery** (Sentinel-2 free; Planet Labs ~$180+/mo) | Free to ~$1,500/mo | Sentinel-2 is **10 m per pixel**, so one pixel covers 100 m², larger than a whole seedling cluster. It can't show *which* plant is dying. Coastal fog blocks imagery for weeks at a time, and processing it takes GIS expertise. |
| **Commercial multispectral drone** (DJI Agras T40, Matrice + MicaSense) | $18,000–$26,500+ | The hardware costs more than many of these nonprofits spend in a year. It also needs an FAA Part 107 pilot, and software like Pix4D runs about $350/mo. |
| **LEAF Guardian** | **~$400–$660 one-time** | Designed for this user |

The real competitor isn't another technology. It's **a volunteer walking the site**. LEAF Guardian aims to be cheaper and easier than every technical option, and more consistent, more scalable, and earlier-warning than the manual one.

---

## 3. What LEAF Guardian does

```
  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
  │ 1. Plan      │──►│ 2. Fly &     │──►│ 3. Stitch    │──►│ 4. Score     │──►│ 5. Report    │
  │ lawnmower    │   │ capture photo│   │ row.col.jpg  │   │ every grid   │   │ color map +  │
  │ grid         │   │ at each      │   │ tiles into   │   │ cell 0–1,    │   │ text report  │
  │              │   │ waypoint     │   │ one site map │   │ assign tier  │   │ w/ actions   │
  └──────────────┘   └──────────────┘   └──────────────┘   └──────────────┘   └──────────────┘
```

Each grid cell gets a health score from 0 to 1 and one of four tiers:

| Tier | Score | Recommendation |
|---|---|---|
| 🟢 **Healthy** | ≥ 0.65 | No intervention required |
| 🟡 **Monitor** | 0.40–0.65 | Schedule a visual inspection within 2 weeks |
| 🟠 **Action Needed** | 0.20–0.40 | Prioritize irrigation; inspect for pests or disease within 1 week |
| 🔴 **Critical** | < 0.20 | Immediate intervention required |

### Version roadmap

| Version | Goal |
|---|---|
| **V1 (current)** | Prove the full loop works: grid flight → photos → stitched composite → RGB health scoring → report |
| **V2** | GPS outdoor flight, onboard NDVI (near-infrared) camera, overlap-aware stitching, multiple sites |
| **V3** | Machine-learning health classifier trained on field data, RGB + NDVI cross-referencing, confidence scores |
| **V4** | Web dashboard, historical tracking per site, user accounts, grant-ready impact reports |

---

## 4. Design iterations: software

### Iteration 1: satellite data (Sentinel-2) as a test bed

Before any drone was in hand, the whole analysis pipeline was built and debugged on **real, georeferenced satellite data**. The Sentinel-2 L2A scene covers **Coyote Hills Regional Park, Fremont CA** (tile T10SEG, 12 Aug 2022). The analysis uses a 2 km × 2 km crop centered on 37.5527°N, 122.0926°W, divided into a 9×9 grid.

Two independent health scores were computed from the same scene:

- **NDVI** (`sentinel_ndvi.py`) uses the red (B04) and near-infrared (B08) bands:
  `NDVI = (NIR − Red) / (NIR + Red)`. Each cell is scored as `clip(mean NDVI, 0, 0.8) / 0.8`. The ceiling is 0.8 because dense, healthy California vegetation plateaus around 0.6–0.8 in late summer.
- **Excess Green (ExG)** (`sentinel_rgb.py`) uses the visible bands: `ExG = 2G − R − B`, scored as `clip(mean ExG, 0, 0.12) / 0.12`. Satellite reflectance is a 0–1 float rather than an 8-bit photo, so simple band arithmetic works better here than color-space thresholds.

`combine_maps.py` then averages the two scores per cell and adds a **discrepancy layer** (`|RGB − NDVI|`) that shows where visible color and near-infrared disagree.

<p align="center">
  <img src="data/sentinel_data/color_images/sat_rgb_2022-Aug-CoyoteHills.png" width="45%" alt="Sentinel-2 true color, Coyote Hills">
  <img src="data/sentinel_data/color_images/ndvi_2022-Aug-CoyoteHills.png" width="45%" alt="Sentinel-2 NDVI, Coyote Hills">
  <br><em>Left: Sentinel-2 true-color crop of Coyote Hills. Right: NDVI of the same crop. Bay water on the left reads strongly negative.</em>
</p>

<p align="center">
  <img src="data/sentinel_data/combined_maps/combined_map_2022-Aug-CoyoteHills.png" width="80%" alt="Combined health map and discrepancy">
  <br><em>Combined RGB + NDVI health score per 222 m cell (left) and where the two sensors disagree (right).</em>
</p>

**Lessons from this phase:**

1. **The first download was the entire 100 km × 100 km tile.** Drawing a box in the Copernicus browser doesn't crop the download. The fix was `sentinel_utils.crop_band()`, a windowed read that both scripts share, so NDVI and RGB always cover exactly the same ground.
2. **The first crop landed on a residential neighborhood,** not the park. It had to be re-centered twice.
3. **Comparing unrelated images is meaningless.** An early test compared a houseplant photo to a satellite tile and showed near-total "discrepancy." Once both scores came from the same scene and crop, the comparison became meaningful.
4. **Water was being read as healthy vegetation.** Green-tinted bay water and algae have the same *hue* as leaves, so the color classifier scored them as healthy, while NDVI correctly showed them as non-vegetation. The fix was a **saturation filter (S > 80)**: water is washed out compared to real foliage. This removed the false positives without affecting real plants.

<p align="center">
  <img src="data/sentinel_data/combined_maps/discrepancy_comparison.png" width="90%" alt="Saturation filter before and after">
  <br><em>The water-channel misclassification before (left) and after (right) adding the saturation filter. The dark-red block of false "healthy" water cells disappears.</em>
</p>

The discrepancy layer also became interpretable:

| Pattern | Likely meaning |
|---|---|
| High NDVI, low RGB | Dry annual grass. The near-infrared signal persists after visible green fades (very common in CA by August). |
| High RGB, low NDVI | Misclassification, or narrow shrubs that don't fill a 10 m cell |
| Both high | Reliably green woody vegetation |
| Both low | Bare soil, pavement, or open water |

**The key limitation:** at 10 m per pixel, Sentinel-2 **cannot see individual plants**. One pixel is 100 m², and a seedling is under 1 m². Satellite data shows zone-level trends, not which plant needs water. That's why the project moved from satellite to drone imagery. The satellite pipeline now serves as a **baseline to compare against** and as the place where the grid scoring, fusion, and reporting code was validated.

### Iteration 2: stitching real-world RGB photos

Next, the pipeline moved to ground-level photos. Real plant photos were taken in a grid pattern from above (1.1 = top-left, 2.2 = bottom-right) to imitate what a drone would capture. `stitch_grid.py` assembles and analyzes them:

1. **Scan.** It finds every `<row>.<col>.jpg` in a folder and auto-detects the grid size (2×2, 3×3, 4×5…), warning about missing tiles.
2. **Stitch.** It assembles the tiles into one composite. Mixed aspect ratios are **letterboxed** (scaled and padded) instead of cropped, so no real pixel data is thrown away.
3. **Analyze.** It scores the composite at a finer resolution, with (rows × 3) × (cols × 3) cells, and overlays color-coded results.

<p align="center">
  <img src="docs/images/real_grid_composite_2x2.jpg" width="40%" alt="Stitched 2x2 real photo composite">
  <img src="docs/images/real_grid_analyzed_2x2.jpg" width="40%" alt="Analyzed 2x2 real photo composite">
  <br><em>A 2×2 grid of real overhead photos stitched together (left) and scored cell by cell (right). Dense leaves score 0.7–0.9, yellowing leaves score lower, and concrete and shadow score ~0.</em>
</p>

#### How the current RGB health analysis works

`rgb_health.py` scores each grid cell with **two independent visible-light indices** and averages them.

**① HSV pixel classification.** The photo is converted from RGB to HSV (hue, saturation, value). Each pixel is then sorted:

| Class | Rule (OpenCV HSV, hue 0–179) | Why |
|---|---|---|
| Excluded: shadow | V ≤ 30 | Too dark to tell the color |
| Excluded: sky | H 90–130 and S > 50 | Blue sky isn't plant or ground |
| **Green** (healthy) | H 35–85 **and S > 80** | The saturation check rejects water and algae (see Iteration 1) |
| **Yellow** (early stress) | H 20–35, S > 100, V > 100 | Bright yellow is an early warning sign |
| **Brown** (dead/dry) | H 10–35, not yellow | Dry or dead material |

`HSV score = green / (green + 0.5·yellow + brown + 1)`. Yellow counts half as much as brown because yellowing is an earlier, still-recoverable stage.

**② VARI** (Visible Atmospherically Resistant Index, Gitelson et al. 2002) is a published vegetation index that uses only red, green, and blue:
`VARI = (G − R) / (G + R − B)`. It is clipped to [−0.2, 0.6] and rescaled to 0–1. It's less sensitive to lighting than raw color thresholds.

**Final score** = average of ① and ②. The score is mapped to one of the four tiers above, and a `health_report_<label>.txt` file lists a summary, the overall site score, and every *Action Needed* or *Critical* zone with its recommendation.

Health scores are always computed on the **original full-resolution image**. Resizing and letterboxing only happen for the display composite.

### Iteration 3: autonomous mission code and a mock drone

`waypoint_mission.py` flies a **lawnmower pattern**: up one column, shift right, down the next. It captures `<row>.<col>.jpg` at each waypoint, runs the stitcher automatically after landing, and writes a timestamped JSON flight log (battery used, duration, photo list, stitch results).

Because the code was written before the drone arrived, it includes a **`MockTello`** class that imitates connecting, taking off, moving, battery drain, and landing, and writes placeholder photos. That let the full fly → stitch → analyze pipeline be tested end to end with no hardware. Switching to the real drone is a single `--real` flag.

### Other code changes worth noting

- **Shared crop geometry** (`sentinel_utils.py`). Duplicate cropping code was pulled into one function after NDVI and RGB were found to be cropping slightly different areas.
- **Zero-score cells shown in black** on grid maps, so "no vegetation at all" is visually distinct from "unhealthy vegetation."
- **Fixed coordinate convention.** Row 1 is the top and column 1 is the left, 1-indexed everywhere. The mission writer and the stitcher use the same convention, so no flipping logic is needed.
- **Tello capture fixes** (`test_capture.py`). The video stream returns black or corrupted frames for its first few seconds, so the script waits about 4 s after `streamon()`, throws away early frames, and only saves frames that pass a brightness check. Three white-balance correction methods (channel scaling, histogram stretch, LAB + CLAHE) were added to fight the Tello's blue color cast.

---

## 5. Design iterations: hardware

### Drone 1: DJI Tello (~$150)

The Tello was chosen because it can be **programmed directly from a laptop in Python** (`djitellopy`), which makes true autonomous flight possible.

**What worked:**
- Stable hover and clean landing (`test_hover.py`)
- Single-axis moves (`test_move.py`)
- A 4-point, 60 cm square flown autonomously that **completes reliably** and uses about 1% battery (`test_square.py`)
- Capturing still frames from the video stream mid-flight
- A full 3×3 autonomous **vertical-grid** mission with photos at every waypoint (`vertical_grid_mission.py`)

**What limited it:**

| Problem | Cause | Status |
|---|---|---|
| **Can't look down** | The downward camera is reserved for the Tello's positioning system. The undocumented `downvision` command does nothing on the standard Tello (only the EDU model). | Hardware limit. Worked around by flying a *vertical* grid with the forward camera. |
| **Poor color** | Strong blue cast in captured frames, plus low-resolution (960×720) video frames | Partly corrected in software; not fully solved |
| Flips fail | Tello disables flips below ~40–50% battery, and needs altitude clearance | Battery check plus climb before maneuvers |
| `Motor stop` / `Not joystick` errors | Drone stuck out of SDK mode from a previous session | Power-cycle between sessions, wait 2 s after `connect()` |
| No GPS | Optical-flow positioning only, so it drifts in any outdoor wind | Hardware limit |

<p align="center">
  <img src="docs/images/tello_vertical_grid_composite_3x3.jpg" width="45%" alt="Tello vertical grid composite">
  <img src="docs/images/tello_vertical_grid_analyzed_3x3.jpg" width="45%" alt="Tello vertical grid analyzed">
  <br><em>First real autonomous Tello grid mission: 9 photos captured on a 3×3 vertical grid, stitched (left) and scored (right). The indoor test scene has no vegetation, so every cell correctly scores Critical. The test proves the drone-to-report pipeline works end to end.</em>
</p>

**Takeaway:** the Tello proved that **autonomous grid flight → photo capture → stitching → health report** works as a complete loop. Its camera, though, can't produce the overhead, color-accurate images plant monitoring needs.

### Drone 2: DJI Mini 4K (~$299)

The Mini 4K was bought as the outdoor field platform because of its much better camera.

**Strengths:**
- **3-axis gimbal that tilts to −90°** (straight down), which is exactly the view plant monitoring needs
- Much higher image quality and more accurate color than the Tello
- GPS-stabilized outdoor flight

**Limitations:**
- **No autonomous capability.** The Mini 4K doesn't support waypoint missions, either in DJI Fly or in third-party apps like Litchi, and DJI consumer drones can't be controlled from a laptop.
- Flights are manual, from the phone app.

**How it was used:** to test the **drone imagery → analysis pipeline** with real aerial photos. The drone was flown manually over a grid and photos were captured at each position. They were moved to the computer **on the drone's microSD card**, renamed to the `row.col.jpg` convention, and run through `stitch_grid.py` and the health scoring.

<!-- TODO: add Mini 4K aerial photos here, e.g.
<p align="center">
  <img src="docs/images/mini4k_composite.jpg" width="45%">
  <img src="docs/images/mini4k_analyzed.jpg" width="45%">
</p>
-->

**Takeaway:** the Mini 4K has the right camera but no autonomy, and the Tello has autonomy but the wrong camera. Neither does everything the project needs, which points to the next step.

### Drones evaluated and rejected

| Drone | Why not |
|---|---|
| Parrot ANAFI 4K | Open Python SDK and a good gimbal, but **discontinued**. No parts or support. |
| DJI Mini 4 Pro (~$759) | Has waypoints, but is still phone-controlled rather than laptop/Python. Kept as a fallback. |
| Prebuilt F450 kits from unverified sellers | Suspicious pricing and specs, and the included cameras don't support NDVI |
| Holybro X500 / S500 | Good quality, but more expensive than building an F450 |

---

## 6. Next steps

### Software

- **Neural-network health classifier.** Replace the hand-tuned HSV thresholds, which break under different lighting, shadow, white balance, and species, with a model that *learns* what deteriorating plant health looks like.
  - **Transfer learning:** start from a pretrained network (e.g. ResNet18 or MobileNetV2) and fine-tune it on plant-stress datasets at the right scale (close-range, field conditions). Candidates include **PlantSeg** (disease segmentation masks), **OLID I** (biotic *and* abiotic stress such as drought and nutrient deficiency), **AMG_HS** (healthy vs. stressed), **PlantDoc**, and **PlantDiseaseNet**. PlantVillage will be avoided because its lab-background images transfer poorly to the field.
  - **Labeling tool:** a simple tool to tag image tiles as Healthy / Stressed / Dead, so every future flight adds labeled training data.
  - **Fine-tune on CA LEAF imagery.** No public dataset pairs California native restoration species with health labels. Building one is a contribution in itself.
- **Confidence scores.** Flag cells that have too few classified pixels or an almost even green/brown split, instead of reporting false precision.
- **Higher-resolution aerial baseline.** Test USDA **NAIP** imagery (60 cm/pixel, includes near-infrared) as a middle ground between Sentinel-2 and drone photos.

### Hardware

- **A custom, non-prebuilt drone** that combines the Tello's autonomy with the Mini 4K's camera quality. The leading candidate is an **F450 quadcopter kit (Pixhawk flight controller + GPS)** with:
  - **laptop Python control** through DroneKit / MAVLink, with real **GPS waypoint** missions uploaded from the computer
  - a **Raspberry Pi** onboard with a **downward-facing camera**, including a **NoIR camera + filter for NDVI**, so near-infrared health data comes from the drone itself
  - photos saved on the Pi and pulled after landing over Wi-Fi, which removes the microSD shuffle. Later, analysis could run **onboard** so the report is ready when the drone lands.
  - **SITL simulation**, so missions can be tested in a physics simulator before real flights (replacing `MockTello`)
  - estimated total of **~$660**, still a small fraction of a commercial multispectral drone
- Most of the existing pipeline carries over unchanged (`stitch_grid.py`, `rgb_health.py`, `combine_maps.py`, reporting). Only the flight-control and photo-capture layers need rewriting.

### Field work

- Collect real survey imagery at CA LEAF planting sites.
- Get input from CA LEAF coordinators on which plant stress signs matter most in the field.

---

## 7. Repository layout and setup

```
leaf-guardian/
├── data/
│   ├── sentinel_data/        # Sentinel-2 bands (gitignored) + NDVI, RGB, grid, combined outputs
│   ├── drone_imagery/        # test photos, grid_test (real), survey (mock), vertical_grid (Tello)
│   └── flight_logs/          # JSON logs written by each mission
├── docs/                     # flight plan, README images
└── software/
    ├── ndvi_pipeline/        # satellite NDVI/RGB, rgb_health, stitch_grid, combine_maps
    └── tello_control/        # waypoint + vertical grid missions, hardware test scripts
```

| Script | What it does |
|---|---|
| `ndvi_pipeline/run_combined.py` | Runs the full satellite pipeline (RGB → NDVI → combine) |
| `ndvi_pipeline/sentinel_ndvi.py` | NDVI map and scored grid from Sentinel-2 B04/B08 |
| `ndvi_pipeline/sentinel_rgb.py` | True-color image and ExG health grid from B02/B03/B04 |
| `ndvi_pipeline/combine_maps.py` | Averages RGB and NDVI scores; discrepancy layer |
| `ndvi_pipeline/rgb_health.py` | HSV + VARI health scoring, tiers, text report |
| `ndvi_pipeline/stitch_grid.py` | Stitches `row.col.jpg` tiles and analyzes the composite |
| `tello_control/waypoint_mission.py` | Lawnmower survey (mock by default, `--real` for Tello) |
| `tello_control/vertical_grid_mission.py` | Vertical-grid survey using the Tello's forward camera |
| `tello_control/test_*.py` | Individual hardware tests (hover, move, square, capture, …) |

### Setup

```bash
git clone https://github.com/Aarush-Sundararajan/leaf-guardian.git
cd leaf-guardian
py -m pip install numpy matplotlib rasterio opencv-python djitellopy

# Satellite pipeline (needs Sentinel-2 B02/B03/B04/B08 .jp2 files in data/sentinel_data/2022_aug/)
py software/ndvi_pipeline/run_combined.py

# Mock drone survey (no hardware needed)
py software/tello_control/waypoint_mission.py

# Stitch and analyze any folder of row.col.jpg photos
py software/ndvi_pipeline/stitch_grid.py data/drone_imagery/grid_test

# Live Tello mission (connect to the Tello's Wi-Fi first)
py software/tello_control/waypoint_mission.py --real
```

All scripts must be run from the **repo root**, because data paths are relative.

---

*Development history: see [DEVLOG.md](DEVLOG.md).*
