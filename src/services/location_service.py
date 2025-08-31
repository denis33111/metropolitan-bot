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
        self.office_latitude = float(os.getenv('OFFICE_LATITUDE', '37.924917'))
        self.office_longitude = float(os.getenv('OFFICE_LONGITUDE', '23.931444'))
        self.office_radius_meters = int(os.getenv('OFFICE_RADIUS_METERS', '500'))
        
        logger.info(f"📍 Office zone set: {self.office_latitude}, {self.office_longitude} (radius: {self.office_radius_meters}m)")
    
    def calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points using Haversine formula (in meters)"""
        # Convert to radians
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)
        
        # Haversine formula
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        # Earth's radius in meters
        earth_radius = 6371000
        
        return earth_radius * c
    
    def is_within_office_zone(self, latitude: float, longitude: float) -> Dict[str, any]:
        """Check if location is within office zone"""
        try:
            # Calculate distance to office
            distance = self.calculate_distance(
                self.office_latitude, 
                self.office_longitude, 
                latitude, 
                longitude
            )
            
            # Check if within radius
            is_within = distance <= self.office_radius_meters
            
            result = {
                'is_within': is_within,
                'distance_meters': round(distance, 2),
                'office_lat': self.office_latitude,
                'office_lon': self.office_longitude,
                'user_lat': latitude,
                'user_lon': longitude,
                'radius_meters': self.office_radius_meters
            }
            
            if is_within:
                logger.info(f"✅ Location verified: {distance:.2f}m from office")
            else:
                logger.warning(f"❌ Location outside zone: {distance:.2f}m from office (limit: {self.office_radius_meters}m)")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error calculating location: {e}")
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
            return f"❌ **Τοποθεσία εκτός ζώνης!**\n\n📍 Είστε {distance}m από το γραφείο\n❌ Πρέπει να είστε μέσα σε {self.office_radius_meters}m για check-in/out"
