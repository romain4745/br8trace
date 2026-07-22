
import os
import base64
import hashlib
import json
import requests
from datetime import datetime
from dotenv import load_dotenv
import rasterio
from rasterio.windows import Window
import numpy as np
from shapely.geometry import Point, Polygon, mapping
import geopandas as gpd

load_dotenv()

class SatelliteIntel:
    """Satellite imagery intelligence module using Planet Labs API and local processing."""
    
    def __init__(self):
        self.planet_api_key = os.getenv('PLANET_API_KEY', '')
        self.planet_base_url = 'https://api.planet.com/data/v1'
        self.upload_dir = 'satellite_imagery'
        os.makedirs(self.upload_dir, exist_ok=True)
        
        # Planet Labs item types
        self.item_types = {
            'PSScene': 'PlanetScope 3m imagery',
            'SkySatScene': 'SkySat 0.5m imagery',
            'REOrthoTile': 'RapidEye 5m imagery'
        }
        
        # Supported search filters
        self.filters = {
            'cloud_cover': 0.1,  # Max cloud cover 10%
            'geometry': None,
            'date_range': None
        }
    
    def search_satellite_imagery(self, lat, lon, date_from=None, date_to=None, max_cloud=0.1):
        """
        Search for satellite imagery using Planet Labs API.
        
        Args:
            lat: Latitude coordinate
            lon: Longitude coordinate
            date_from: Start date (YYYY-MM-DD)
            date_to: End date (YYYY-MM-DD)
            max_cloud: Maximum cloud cover percentage (0-1)
        
        Returns:
            list: Available satellite imagery items
        """
        if not self.planet_api_key:
            print("[satellite] No Planet API key found. Using simulated data.")
            return self._simulate_satellite_search(lat, lon)
        
        try:
            # Build search geometry
            geometry = {
                "type": "Point",
                "coordinates": [lon, lat]
            }
            
            # Build search query
            query = {
                "filter": {
                    "type": "AndFilter",
                    "config": [
                        {
                            "type": "GeometryFilter",
                            "field_name": "geometry",
                            "config": {
                                "type": "Point",
                                "coordinates": [lon, lat]
                            }
                        },
                        {
                            "type": "RangeFilter",
                            "field_name": "cloud_cover",
                            "config": {
                                "lte": max_cloud
                            }
                        }
                    ]
                }
            }
            
            if date_from and date_to:
                query["filter"]["config"].append({
                    "type": "DateRangeFilter",
                    "field_name": "acquired",
                    "config": {
                        "gte": date_from,
                        "lte": date_to
                    }
                })
            
            # Make API request
            headers = {
                'Authorization': f'api-key {self.planet_api_key}',
                'Content-Type': 'application/json'
            }
            
            response = requests.post(
                f'{self.planet_base_url}/searches',
                headers=headers,
                json=query,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                items = data.get('features', [])
                print(f"[satellite] Found {len(items)} satellite imagery items")
                return self._parse_satellite_results(items)
            else:
                print(f"[satellite] API error: {response.status_code}")
                return self._simulate_satellite_search(lat, lon)
                
        except Exception as e:
            print(f"[satellite] Error searching satellite imagery: {e}")
            return self._simulate_satellite_search(lat, lon)
    
    def _parse_satellite_results(self, items):
        """Parse Planet API results into structured data."""
        results = []
        for item in items:
            properties = item.get('properties', {})
            geometry = item.get('geometry', {})
            
            result = {
                'type': 'satellite_imagery',
                'item_type': item.get('type', 'unknown'),
                'item_id': item.get('id', ''),
                'acquired': properties.get('acquired', ''),
                'cloud_cover': properties.get('cloud_cover', 0),
                'geometry': geometry,
                'coordinates': geometry.get('coordinates', [])
            }
            
            # Add additional metadata if available
            if 'asset' in item:
                result['asset_type'] = item['asset'].get('type', '')
                result['asset_url'] = item['asset'].get('url', '')
            
            results.append(result)
        
        return results
    
    def _simulate_satellite_search(self, lat, lon):
        """Simulate satellite search results for demo purposes."""
        return [
            {
                'type': 'satellite_imagery',
                'item_type': 'PSScene',
                'item_id': 'simulated_001',
                'acquired': datetime.utcnow().isoformat() + 'Z',
                'cloud_cover': 0.05,
                'coordinates': [lon, lat],
                'resolution_meters': 3,
                'bands': ['Red', 'Green', 'Blue', 'NIR'],
                'status': 'simulated'
            },
            {
                'type': 'satellite_imagery',
                'item_type': 'SkySatScene',
                'item_id': 'simulated_002',
                'acquired': (datetime.utcnow().isoformat() + 'Z'),
                'cloud_cover': 0.12,
                'coordinates': [lon, lat],
                'resolution_meters': 0.5,
                'bands': ['Red', 'Green', 'Blue', 'Panchromatic'],
                'status': 'simulated'
            }
        ]
    
    def process_geotiff(self, tiff_path, output_path, tile_size=(256, 256)):
        """
        Process GeoTIFF files for analysis.
        
        Args:
            tiff_path: Path to GeoTIFF file
            output_path: Output directory for processed tiles
            tile_size: Size of tiles to split into
        """
        try:
            from rasterio.windows import Window
            from tqdm import tqdm
            
            os.makedirs(output_path, exist_ok=True)
            
            with rasterio.open(tiff_path) as src:
                width, height = src.width, src.height
                tile_width, tile_height = tile_size
                
                # Calculate windows
                windows = []
                for y in range(0, height, tile_height):
                    for x in range(0, width, tile_width):
                        win = Window(x, y, min(tile_width, width - x), 
                                   min(tile_height, height - y))
                        windows.append(win)
                
                print(f"[satellite] Processing {len(windows)} tiles from {tiff_path}")
                
                # Process each tile
                for i, window in enumerate(tqdm(windows, desc="Processing tiles")):
                    out_path = os.path.join(output_path, f"tile_{i:04}.tif")
                    transform = src.window_transform(window)
                    
                    with rasterio.open(
                        out_path,
                        'w',
                        driver='GTiff',
                        height=window.height,
                        width=window.width,
                        count=src.count,
                        dtype=src.dtypes[0],
                        crs=src.crs,
                        transform=transform,
                    ) as dst:
                        dst.write(src.read(window=window))
                
                return {
                    'status': 'success',
                    'tiles_created': len(windows),
                    'output_directory': output_path
                }
                
        except Exception as e:
            print(f"[satellite] Error processing GeoTIFF: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def extract_vegetation_indices(self, tiff_path, index_type='NDVI'):
        """
        Extract vegetation indices from satellite imagery.
        
        Args:
            tiff_path: Path to multi-band GeoTIFF
            index_type: Type of index (NDVI, NDWI, etc.)
        
        Returns:
            dict: Extracted indices data
        """
        try:
            with rasterio.open(tiff_path) as src:
                # Assuming bands: [Red, Green, Blue, NIR]
                # This is typical for PlanetScope imagery
                bands = src.read()
                
                if bands.shape[0] >= 4:
                    red = bands[0].astype(np.float32)
                    green = bands[1].astype(np.float32)
                    blue = bands[2].astype(np.float32)
                    nir = bands[3].astype(np.float32)
                    
                    if index_type == 'NDVI':
                        # Normalized Difference Vegetation Index
                        ndvi = (nir - red) / (nir + red + 1e-10)
                        
                        return {
                            'index': 'NDVI',
                            'values': ndvi.tolist(),
                            'min': float(np.nanmin(ndvi)),
                            'max': float(np.nanmax(ndvi)),
                            'mean': float(np.nanmean(ndvi)),
                            'interpretation': self._interpret_ndvi(ndvi)
                        }
                    elif index_type == 'NDWI':
                        # Normalized Difference Water Index
                        ndwi = (green - nir) / (green + nir + 1e-10)
                        
                        return {
                            'index': 'NDWI',
                            'values': ndwi.tolist(),
                            'min': float(np.nanmin(ndwi)),
                            'max': float(np.nanmax(ndwi)),
                            'mean': float(np.nanmean(ndwi))
                        }
                
                return {
                    'status': 'error',
                    'message': 'Insufficient bands for index calculation'
                }
                
        except Exception as e:
            print(f"[satellite] Error extracting indices: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def _interpret_ndvi(self, ndvi):
        """Interpret NDVI values."""
        if np.nanmean(ndvi) > 0.6:
            return 'Dense vegetation/forest'
        elif np.nanmean(ndvi) > 0.3:
            return 'Moderate vegetation/green areas'
        elif np.nanmean(ndvi) > 0.1:
            return 'Sparse vegetation/urban areas'
        else:
            return 'Water/barren land'
    
    def collect(self, coordinates):
        """
        Main collection method for satellite intelligence.
        
        Args:
            coordinates: Can be (lat, lon) tuple or 'lat,lon' string
        
        Returns:
            list: Satellite intelligence results
        """
        results = []
        
        # Parse coordinates
        if isinstance(coordinates, str):
            try:
                lat, lon = map(float, coordinates.split(','))
            except:
                lat, lon = 0, 0
        elif isinstance(coordinates, (tuple, list)):
            lat, lon = coordinates[0], coordinates[1]
        else:
            print("[satellite] Invalid coordinates format")
            return results
        
        print(f"[satellite] Starting satellite intelligence for coordinates: {lat}, {lon}")
        
        # 1. Search for available imagery
        imagery = self.search_satellite_imagery(lat, lon)
        results.extend(imagery)
        
        # 2. Add location analysis
        results.append({
            'type': 'location_analysis',
            'coordinates': {'latitude': lat, 'longitude': lon},
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'available_imagery': len(imagery),
            'nearby_landmarks': self._get_nearby_landmarks(lat, lon)
        })
        
        print(f"[satellite] Satellite intelligence complete. Found {len(results)} items")
        return results
    
    def _get_nearby_landmarks(self, lat, lon):
        """Get nearby landmarks using OpenStreetMap (simulated)."""
        # This is a placeholder for actual geocoding API calls
        return [
            {'type': 'water_body', 'distance_km': 2.3},
            {'type': 'urban_area', 'distance_km': 1.5}
        ]