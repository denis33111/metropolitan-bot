#!/usr/bin/env python3
"""
📍 LOCATION SERVICE
Handles location verification for check-in/out
"""

import logging
import math
import os
from typing import Dict, Tuple

logger = logging.getLogger(__name__)

class LocationService:
    """Service for location verification"""
    
    def __init__(self):
        # Office coordinates from environment variables
        self.office_latitude = float(os.getenv('OFFICE_LATITUDE', '37.909411'))
        self.office_longitude = float(os.getenv('OFFICE_LONGITUDE', '23.871109'))
        self.office_radius_meters = int(os.getenv('OFFICE_RADIUS_METERS', '300'))
        
        logger.info(f"🔍 DEBUG: LocationService initialized")
        logger.info(f"🔍 DEBUG: OFFICE_LATITUDE env var: '{os.getenv('OFFICE_LATITUDE', 'NOT_SET')}'")
        logger.info(f"🔍 DEBUG: OFFICE_LONGITUDE env var: '{os.getenv('OFFICE_LONGITUDE', 'NOT_SET')}'")
        logger.info(f"🔍 DEBUG: OFFICE_RADIUS_METERS env var: '{os.getenv('OFFICE_RADIUS_METERS', 'NOT_SET')}'")
        logger.info(f"🔍 DEBUG: All environment variables starting with OFFICE_:")
        for key, value in os.environ.items():
            if key.startswith('OFFICE_'):
                logger.info(f"🔍 DEBUG:   {key} = '{value}'")
        logger.info(f"📍 Office zone set: {self.office_latitude}, {self.office_longitude} (radius: {self.office_radius_meters}m)")
    
    def calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points using Haversine formula (in meters)"""
        logger.info(f"🔍 DEBUG: calculate_distance called with:")
        logger.info(f"🔍 DEBUG:   Point 1 (Office): lat={lat1}, lon={lon1}")
        logger.info(f"🔍 DEBUG:   Point 2 (User): lat={lat2}, lon={lon2}")
        
        # Convert to radians
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)
        
        logger.info(f"🔍 DEBUG: Converted to radians:")
        logger.info(f"🔍 DEBUG:   lat1_rad={lat1_rad}, lon1_rad={lon1_rad}")
        logger.info(f"🔍 DEBUG:   lat2_rad={lat2_rad}, lon2_rad={lon2_rad}")
        
        # Haversine formula
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        logger.info(f"🔍 DEBUG: Differences: dlat={dlat}, dlon={dlon}")
        
        a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        logger.info(f"🔍 DEBUG: Haversine calculation: a={a}, c={c}")
        
        # Earth's radius in meters
        earth_radius = 6371000
        
        distance = earth_radius * c
        logger.info(f"🔍 DEBUG: Final distance calculation: {earth_radius} * {c} = {distance} meters")
        
        return distance
    
    def is_within_office_zone(self, latitude: float, longitude: float) -> Dict[str, any]:
        """Check if location is within office zone"""
        logger.info(f"🔍 DEBUG: is_within_office_zone called with user coordinates: lat={latitude}, lon={longitude}")
        logger.info(f"🔍 DEBUG: Office coordinates: lat={self.office_latitude}, lon={self.office_longitude}")
        logger.info(f"🔍 DEBUG: Office radius: {self.office_radius_meters} meters")
        
        try:
            # Calculate distance to office
            logger.info(f"🔍 DEBUG: Calling calculate_distance...")
            distance = self.calculate_distance(
                self.office_latitude, 
                self.office_longitude, 
                latitude, 
                longitude
            )
            
            logger.info(f"🔍 DEBUG: Distance calculated: {distance} meters")
            
            # Check if within radius
            is_within = distance <= self.office_radius_meters
            logger.info(f"🔍 DEBUG: Within radius check: {distance} <= {self.office_radius_meters} = {is_within}")
            
            result = {
                'is_within': is_within,
                'distance_meters': round(distance, 2),
                'office_lat': self.office_latitude,
                'office_lon': self.office_longitude,
                'user_lat': latitude,
                'user_lon': longitude,
                'radius_meters': self.office_radius_meters
            }
            
            logger.info(f"🔍 DEBUG: Final result: {result}")
            
            if is_within:
                logger.info(f"✅ Location verified: {distance:.2f}m from office")
            else:
                logger.warning(f"❌ Location outside zone: {distance:.2f}m from office (limit: {self.office_radius_meters}m)")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error calculating location: {e}")
            logger.error(f"🔍 DEBUG: Exception details: {type(e).__name__}: {str(e)}")
            import traceback
            logger.error(f"🔍 DEBUG: Traceback: {traceback.format_exc()}")
            return {
                'is_within': False,
                'error': str(e),
                'distance_meters': -1
            }
    
    def get_office_info(self) -> Dict[str, any]:
        """Get office zone information"""
        return {
            'latitude': self.office_latitude,
            'longitude': self.office_longitude,
            'radius_meters': self.office_radius_meters,
            'description': 'Metropolitan Office Zone'
        }
    
    def format_location_message(self, location_result: Dict[str, any]) -> str:
        """Format location result into user-friendly message"""
        if location_result.get('error'):
            return "❌ Σφάλμα κατά την επαλήθευση της τοποθεσίας."
        
        distance = location_result['distance_meters']
        is_within = location_result['is_within']
        
        if is_within:
            return f"✅ **Τοποθεσία επαληθεύθηκε!**\n\n📍 Είστε {distance}m από το γραφείο\n✅ Μπορείτε να κάνετε check-in/out"
        else:
            return f"❌ Εκτός εργασιακής ζώνης\n\n📍 Απόσταση: {distance}m\n❌ Απαιτείται: {self.office_radius_meters}m"
