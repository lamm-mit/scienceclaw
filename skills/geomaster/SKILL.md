---
name: geomaster
description: Comprehensive geospatial science skill covering 70+ topics in remote sensing, GIS, spatial analysis, and machine learning for Earth observation. Processes satellite imagery (Sentinel, Landsat, MODIS), vector/raster data, point clouds. Supports 8 programming languages with 500+ code examples.
license: MIT
metadata:
    skill-author: K-Dense Inc.
---

# GeoMaster — Geospatial Science Skill

## Overview

GeoMaster is a comprehensive geospatial science skill covering over 70 topics spanning remote sensing, GIS, spatial analysis, and machine learning for Earth observation. It provides practical implementations across 8 programming languages: Python, R, Julia, JavaScript, C++, Java, Go, and Rust.

**Key resources:**
- Documentation: Complete reference for geospatial methods
- 500+ code examples across multiple languages
- Best practices for modern Earth observation workflows

## Core Capabilities

1. **Satellite imagery processing** - Handle data from Sentinel, Landsat, MODIS, SAR, and hyperspectral sensors
2. **Vector and raster operations** - Perform GIS operations on spatial data
3. **Spatial statistics** - Apply statistical methods to spatial datasets
4. **Point cloud processing** - Work with LiDAR and other 3D data
5. **Network analysis** - Analyze spatial networks and connectivity
6. **Cloud-native workflows** - Leverage STAC catalogs and Cloud-Optimized GeoTIFFs (COGs)
7. **Machine learning for Earth observation** - Train models on satellite data

## Key Workflows

- Remote sensing data processing and classification
- Spatial machine learning for predictive mapping
- Terrain analysis and hydrological modeling
- Marine spatial analysis
- Atmospheric science applications
- Urban and agricultural monitoring
- Change detection analysis

## Best Practices

The documentation emphasizes:

- Always check coordinate reference system (CRS) before spatial operations
- Use projected CRS for area and distance calculations
- Implement spatial indexing for performance (10-100x faster queries)
- Use Dask for large raster datasets
- Leverage COGs and STAC for cloud-native access
- Validate results with ground truth data
- Consider computational resources for large-scale processing

## Performance Optimization

Key techniques for achieving significant speed improvements:

- Spatial indexing on vector data
- Chunking and lazy loading of large rasters
- Parallel processing with Dask
- Cloud-optimized formats (COGs, Parquet)
- Appropriate CRS selection for efficient computation
