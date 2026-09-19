# SIH26124 requirement coverage

This document keeps the prototype aligned with the problem statement while separating implemented behavior from demonstration data.

## Implemented architecture
- Public-bus multi-camera ingestion and edge processing.
- Road defect, traffic, pedestrian-risk, incident and ANPR pipelines.
- GPS/timestamp event records, fleet aggregation, GIS views, congestion heatmap, incident workflow and reports.
- Spatial-temporal duplicate fusion and offline event queue/retry.
- Road-condition scoring and route-delay API.
- Dedicated infrastructure-deficiency dashboard and origin–destination analytics UI.

## Explicit infrastructure categories
Pothole, damaged road, waterlogging, damaged/missing divider, damaged/missing zebra crossing, damaged/missing signboard and generic road hazard are first-class event categories.

## Prototype / simulated
The OD dashboard currently derives clearly labelled demonstration observations from configured routes. Route-delay demo values are simulated unless returned by backend telemetry. Demo confidence values are scenario data, not validated model accuracy.

## Validation still required
Real-video validation and calibrated metrics are required before claiming production accuracy for road defects, ANPR, pedestrian risk, rash driving or hit-and-run. Missing-infrastructure detection also requires suitable labelled datasets and trained weights.

## Recommended SIH demo
1. Bus camera detects a road defect at the edge.
2. GPS, timestamp and evidence metadata are attached.
3. A second bus observes the same location and the event is deduplicated/corroborated.
4. The event appears on GIS and Infrastructure views.
5. Traffic observations feed congestion and OD intelligence.
6. Route Delays shows the resulting corridor impact.
7. Authority workflow reviews and resolves the event.
