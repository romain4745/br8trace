"""Phone intelligence: carrier lookup, country code detection, location, and owner info."""
import phonenumbers
from phonenumbers import geocoder, carrier, timezone
from phonenumbers.phonenumberutil import region_code_for_country_code
import requests
import json
from datetime import datetime


class PhoneIntel:
    def __init__(self, numverify_api_key=None, twilio_api_key=None):
        """
        Initialize PhoneIntel with optional API keys for enhanced lookup.
        
        Args:
            numverify_api_key: API key for numverify.com (free tier available)
            twilio_api_key: API key for Twilio lookup services
        """
        self.numverify_api_key = numverify_api_key or "a2361cb6ea90615589e385ba3c40b778"
        self.twilio_api_key = twilio_api_key
        
        # Rwanda carrier database
        self.rwanda_carriers = {
            'MTN Rwanda': {
                'prefixes': ['078', '079'],
                'full_name': 'MTN Rwandacell PLC',
                'brand': 'MTN',
                'type': 'mobile'
            },
            'Airtel Rwanda': {
                'prefixes': ['072', '073'],
                'full_name': 'Airtel Rwanda Ltd',
                'brand': 'Airtel-Tigo',
                'type': 'mobile'
            }
        }
        
        # Global carrier databases (sample - expand as needed)
        self.global_carriers = {
            'US': {
                'Verizon': {'prefixes': ['201', '202'], 'type': 'mobile'},
                'AT&T': {'prefixes': ['205', '206'], 'type': 'mobile'},
                'T-Mobile': {'prefixes': ['210', '212'], 'type': 'mobile'}
            },
            'UK': {
                'EE': {'prefixes': ['71', '72', '73', '74', '75', '76'], 'type': 'mobile'},
                'Vodafone': {'prefixes': ['77', '78', '79'], 'type': 'mobile'},
                'O2': {'prefixes': ['70'], 'type': 'mobile'},
                'Three': {'prefixes': ['71'], 'type': 'mobile'}
            },
            'NG': {
                'MTN Nigeria': {'prefixes': ['0803', '0806', '0813', '0816'], 'type': 'mobile'},
                'Airtel Nigeria': {'prefixes': ['0802', '0808', '0812'], 'type': 'mobile'},
                'Glo': {'prefixes': ['0805', '0807', '0811'], 'type': 'mobile'},
                '9mobile': {'prefixes': ['0809', '0817', '0818'], 'type': 'mobile'}
            },
            'KE': {
                'Safaricom': {'prefixes': ['070', '071', '072'], 'type': 'mobile'},
                'Airtel Kenya': {'prefixes': ['073', '075'], 'type': 'mobile'}
            },
            'TZ': {
                'Vodacom': {'prefixes': ['074', '075', '076'], 'type': 'mobile'},
                'Airtel Tanzania': {'prefixes': ['068', '069', '078'], 'type': 'mobile'},
                'Tigo': {'prefixes': ['065', '067', '071'], 'type': 'mobile'}
            },
            'UG': {
                'MTN Uganda': {'prefixes': ['077', '078'], 'type': 'mobile'},
                'Airtel Uganda': {'prefixes': ['075', '070'], 'type': 'mobile'}
            }
        }
        
        # Location database (major cities)
        self.location_db = {
            'RW': {  # Rwanda
                'Kigali': {'code': '01', 'lat': -1.9706, 'lon': 30.1044},
                'Butare': {'code': '02', 'lat': -2.5967, 'lon': 29.7394},
                'Muhanga': {'code': '03', 'lat': -2.0744, 'lon': 29.7567},
                'Musanze': {'code': '04', 'lat': -1.5042, 'lon': 29.6358},
                'Rubavu': {'code': '05', 'lat': -1.7028, 'lon': 29.2564},
                'Nyagatare': {'code': '06', 'lat': -1.2979, 'lon': 30.3081},
                'Rwamagana': {'code': '07', 'lat': -1.9487, 'lon': 30.4347},
                'Karongi': {'code': '08', 'lat': -2.0603, 'lon': 29.3481},
                'Ngoma': {'code': '09', 'lat': -2.1597, 'lon': 30.5427},
                'Rusizi': {'code': '10', 'lat': -2.4847, 'lon': 28.9071}
            }
        }

    def parse_number(self, number, region=None):
        """Parse and validate a phone number."""
        try:
            pn = phonenumbers.parse(number, region)
            if phonenumbers.is_valid_number(pn):
                return pn
            return None
        except Exception as e:
            return None

    def detect_rwanda_carrier(self, national_number):
        """Detect specific carrier in Rwanda based on prefix."""
        str_number = str(national_number)
        for carrier_name, details in self.rwanda_carriers.items():
            for prefix in details['prefixes']:
                if str_number.startswith(prefix):
                    return {
                        'carrier_name': carrier_name,
                        'brand': details['brand'],
                        'full_name': details['full_name'],
                        'type': details['type'],
                        'prefix': prefix
                    }
        return None

    def detect_global_carrier(self, country_code, national_number):
        """Detect carrier for various countries based on prefix."""
        str_number = str(national_number)
        
        # Check Rwanda first
        if country_code == 'RW':
            return self.detect_rwanda_carrier(str_number)
        
        # Check other countries in database
        if country_code in self.global_carriers:
            for carrier_name, details in self.global_carriers[country_code].items():
                for prefix in details['prefixes']:
                    if str_number.startswith(prefix):
                        return {
                            'carrier_name': carrier_name,
                            'full_name': carrier_name,
                            'type': details.get('type', 'unknown'),
                            'prefix': prefix
                        }
        
        return None

    def get_timezone_location(self, pn):
        """Get timezone and approximate location information."""
        try:
            timezones = timezone.time_zones_for_number(pn)
            location = geocoder.description_for_number(pn, 'en')
            
            return {
                'timezones': timezones,
                'approximate_location': location,
                'country_code': region_code_for_country_code(pn.country_code)
            }
        except Exception:
            return {}

    def get_location_details(self, country_code, national_number):
        """Get detailed location information based on number prefix."""
        if country_code in self.location_db:
            str_number = str(national_number)
            # Check first 2 digits for city code
            city_code = str_number[:2] if len(str_number) >= 2 else str_number
            for city, details in self.location_db[country_code].items():
                if city_code == details['code']:
                    return {
                        'city': city,
                        'coordinates': {
                            'latitude': details['lat'],
                            'longitude': details['lon']
                        }
                    }
        return None

    def lookup_numverify(self, number):
        """Enhanced lookup using NumVerify API."""
        if not self.numverify_api_key:
            return None
            
        try:
            url = "http://apilayer.net/api/validate"
            params = {
                'access_key': self.numverify_api_key,
                'number': number,
                'format': 1
            }
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            if data.get('valid'):
                return {
                    'carrier': data.get('carrier'),
                    'line_type': data.get('line_type'),
                    'location': data.get('location'),
                    'country_name': data.get('country_name'),
                    'country_code': data.get('country_code')
                }
        except Exception as e:
            print(f"NumVerify API error: {e}")
        return None

    def sim_owner_lookup(self, number, country):
        """
        Look up SIM registration information (where legally authorized).
        This is a framework for integration with authorized databases.
        """
        # For production use, integrate with:
        # - Local telecom regulatory authority APIs
        # - Licensed telecom databases
        # - Law enforcement systems (with proper warrants)
        
        return {
            'status': 'restricted',
            'message': 'SIM registration data requires legal authorization',
            'available_through': 'RURA (Rwanda Utilities Regulatory Authority) for Rwanda',
            'data_protection_laws': {
                'Rwanda': 'Law N° 058/2021 of 13/10/2021 relating to the protection of personal data and privacy',
                'International': 'GDPR (Europe), CCPA (California), LGPD (Brazil)'
            }
        }

    def analyze_number_pattern(self, pn):
        """Analyze number patterns for additional intelligence."""
        national = str(pn.national_number)
        
        analysis = {
            'total_digits': len(national),
            'number_type': 'mobile' if phonenumbers.number_type(pn) == 1 else 'unknown',
            'is_premium': any(national.startswith(p) for p in ['900', '800', '700']),
            'is_voip': False,
            'risk_level': 'low'
        }
        
        # Check for suspicious patterns
        if len(set(national)) <= 3:
            analysis['risk_level'] = 'high'
            analysis['pattern'] = 'repeated_digits'
        elif national == national[::-1]:
            analysis['risk_level'] = 'medium'
            analysis['pattern'] = 'palindrome'
        elif national.count(national[0]) > len(national) / 2:
            analysis['risk_level'] = 'medium'
            analysis['pattern'] = 'mostly_same_digit'
            
        return analysis

    def carrier_info(self, number, region=None):
        """Enhanced carrier information with detailed lookup."""
        pn = self.parse_number(number, region)
        if not pn:
            return {'error': 'Invalid phone number'}
        
        country_code = region_code_for_country_code(pn.country_code)
        national_number = pn.national_number
        
        # Basic information
        info = {
            'number': phonenumbers.format_number(pn, phonenumbers.PhoneNumberFormat.E164),
            'national_format': phonenumbers.format_number(pn, phonenumbers.PhoneNumberFormat.NATIONAL),
            'international_format': phonenumbers.format_number(pn, phonenumbers.PhoneNumberFormat.INTERNATIONAL),
            'country': geocoder.country_name_for_number(pn, 'en'),
            'country_code': pn.country_code,
            'national_number': national_number,
            'region': country_code,
            'is_valid': phonenumbers.is_valid_number(pn),
            'number_type': str(phonenumbers.number_type(pn)),
            'timestamp': datetime.now().isoformat()
        }
        
        # Standard carrier info
        standard_carrier = carrier.name_for_number(pn, 'en')
        info['standard_carrier'] = standard_carrier
        
        # Enhanced carrier detection
        enhanced_carrier = self.detect_global_carrier(country_code, str(national_number))
        if enhanced_carrier:
            info['carrier_details'] = enhanced_carrier
        
        # Special handling for Rwanda
        if country_code == 'RW':
            rwanda_carrier = self.detect_rwanda_carrier(str(national_number))
            if rwanda_carrier:
                info['rwanda_carrier'] = rwanda_carrier
                info['carrier_display_name'] = f"{rwanda_carrier['brand']} ({rwanda_carrier['full_name']})"
        
        # Timezone and location
        location_info = self.get_timezone_location(pn)
        info.update(location_info)
        
        # Specific location based on prefix
        specific_location = self.get_location_details(country_code, str(national_number))
        if specific_location:
            info['specific_location'] = specific_location
        
        # Number analysis
        info['number_analysis'] = self.analyze_number_pattern(pn)
        
        # NumVerify lookup
        numverify_info = self.lookup_numverify(number)
        if numverify_info:
            info['external_verification'] = numverify_info
        
        # SIM owner information
        info['sim_owner_info'] = self.sim_owner_lookup(number, country_code)
        
        # Additional intelligence
        info['intelligence'] = {
            'is_mobile': phonenumbers.number_type(pn) == 1,
            'is_fixed_line': phonenumbers.number_type(pn) == 0,
            'possible_location': geocoder.description_for_number(pn, 'en'),
            'geocoding_accuracy': 'city_level'
        }
        
        return info

    def collect(self, number, region=None):
        """Collect comprehensive information about a phone number."""
        info = self.carrier_info(number, region)
        
        if 'error' in info:
            return info
        
        # Format output for better readability
        formatted_info = {
            'basic_info': {
                'number': info.get('international_format'),
                'national_format': info.get('national_format'),
                'country': info.get('country'),
                'region': info.get('region'),
                'valid': info.get('is_valid')
            },
            'carrier_information': {
                'standard_carrier': info.get('standard_carrier'),
                'detailed_carrier': info.get('carrier_details') or info.get('rwanda_carrier'),
                'display_name': info.get('carrier_display_name', info.get('standard_carrier'))
            },
            'location_information': {
                'timezone': info.get('timezones'),
                'approximate_location': info.get('approximate_location'),
                'specific_location': info.get('specific_location'),
                'coordinates': info.get('specific_location', {}).get('coordinates') if info.get('specific_location') else None
            },
            'number_analysis': info.get('number_analysis'),
            'external_verification': info.get('external_verification'),
            'additional_intelligence': info.get('intelligence'),
            'sim_owner_status': info.get('sim_owner_info'),
            'lookup_timestamp': info.get('timestamp')
        }
        
        return formatted_info


# Example usage
if __name__ == "__main__":
    # Initialize with NumVerify API key
    phone_intel = PhoneIntel()
    
    # Test with MTN Rwanda number
    mtn_number = "+250781234567"
    print("=== MTN Rwanda Number Analysis ===")
    result = phone_intel.collect(mtn_number)
    print(json.dumps(result, indent=2))
    
    # Test with Airtel Rwanda number
    airtel_number = "+250721234567"
    print("\n=== Airtel Rwanda Number Analysis ===")
    result = phone_intel.collect(airtel_number)
    print(json.dumps(result, indent=2))
    
    # Test with international number
    us_number = "+12025551234"
    print("\n=== US Number Analysis ===")
    result = phone_intel.collect(us_number)
    print(json.dumps(result, indent=2))
    
    # Test with Nigerian number
    ng_number = "+2348031234567"
    print("\n=== Nigerian Number Analysis ===")
    result = phone_intel.collect(ng_number)
    print(json.dumps(result, indent=2))