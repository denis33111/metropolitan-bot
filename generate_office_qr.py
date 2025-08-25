#!/usr/bin/env python3
"""
Generate Office QR Code
Creates the main office QR code image for printing
"""

from src.services.qr_service import QRService

def main():
    # Initialize QR service
    qr_service = QRService(
        qr_codes_dir="qr_codes",
        office_qr_code="METROPOLITAN_OFFICE_001"
    )
    
    # Generate office QR code image
    image_path = qr_service.create_office_qr_image()
    
    print(f"✅ Office QR code generated: {image_path}")
    print(f"📋 QR Code content: METROPOLITAN_OFFICE_001")
    print(f"📁 Image saved to: qr_codes/office_qr_code.png")

if __name__ == "__main__":
    main() 