"""Generates JSON and PDF reports using collected intelligence."""
import os
import json
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from dotenv import load_dotenv

load_dotenv()
REPORTS_DIR = os.getenv('REPORTS_DIR', './reports')
os.makedirs(REPORTS_DIR, exist_ok=True)


class ReportGenerator:
    def __init__(self):
        self.styles = getSampleStyleSheet()
    
    def _get_target_info(self, payload):
        """Extract target information for display purposes."""
        target_type = payload.get('target_type', 'Unknown')
        target = payload.get('target', 'Unknown')
        
        if target_type == 'phone':
            results = payload.get('results', {})
            basic_info = results.get('basic_info', {})
            carrier_info = results.get('carrier_information', {})
            
            return {
                'display_name': f"Phone: {basic_info.get('number', target)}",
                'details': {
                    'Country': basic_info.get('country', 'Unknown'),
                    'Region': basic_info.get('region', 'Unknown'),
                    'Carrier': carrier_info.get('display_name', 'Unknown'),
                    'Valid': 'Yes' if basic_info.get('valid') else 'No'
                }
            }
        elif target_type == 'email':
            return {
                'display_name': f"Email: {target}",
                'details': {'Address': target}
            }
        elif target_type == 'domain':
            return {
                'display_name': f"Domain: {target}",
                'details': {'Domain': target}
            }
        else:
            return {
                'display_name': f"{target_type}: {target}",
                'details': {'Target': target}
            }
    
    def _generate_filename(self, payload):
        """Generate a human-readable filename based on target details."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        target_info = self._get_target_info(payload)
        target_type = payload.get('target_type', 'unknown')
        target = payload.get('target', 'unknown')
        
        # Clean target for filename (remove special characters)
        clean_target = target.replace('+', '').replace('@', '_at_').replace('.', '_').replace(' ', '_')
        
        if target_type == 'phone':
            # Use country and carrier for phone numbers
            results = payload.get('results', {})
            basic_info = results.get('basic_info', {})
            carrier_info = results.get('carrier_information', {})
            country = basic_info.get('country', 'Unknown')
            carrier = carrier_info.get('display_name', 'Unknown').split('(')[0].strip()
            clean_carrier = carrier.replace(' ', '_')
            filename = f"{country}_{clean_carrier}_{clean_target}_{timestamp}"
        else:
            filename = f"{target_type}_{clean_target}_{timestamp}"
        
        return filename
    
    def _format_intelligence_data(self, payload):
        """Format intelligence data for better readability in reports."""
        results = payload.get('results', {})
        formatted = {}
        
        if payload.get('target_type') == 'phone':
            basic_info = results.get('basic_info', {})
            carrier_info = results.get('carrier_information', {})
            location_info = results.get('location_information', {})
            number_analysis = results.get('number_analysis', {})
            
            formatted = {
                'PHONE NUMBER DETAILS': {
                    'Number': basic_info.get('number', 'N/A'),
                    'National Format': basic_info.get('national_format', 'N/A'),
                    'Country': basic_info.get('country', 'N/A'),
                    'Region': basic_info.get('region', 'N/A'),
                    'Valid': '✓ Yes' if basic_info.get('valid') else '✗ No'
                },
                'CARRIER INFORMATION': {
                    'Standard Carrier': carrier_info.get('standard_carrier', 'N/A'),
                    'Detailed Carrier': carrier_info.get('display_name', 'N/A'),
                    'Carrier Details': str(carrier_info.get('detailed_carrier', {}))
                },
                'LOCATION INFORMATION': {
                    'Timezone': str(location_info.get('timezone', ['Unknown'])[0]) if location_info.get('timezone') else 'Unknown',
                    'Approximate Location': location_info.get('approximate_location', 'Unknown'),
                    'Specific Location': location_info.get('specific_location', {}).get('city', 'N/A') if location_info.get('specific_location') else 'N/A',
                    'Coordinates': f"{location_info.get('specific_location', {}).get('coordinates', {}).get('latitude', 'N/A')}, {location_info.get('specific_location', {}).get('coordinates', {}).get('longitude', 'N/A')}" if location_info.get('specific_location') and location_info.get('specific_location').get('coordinates') else 'N/A'
                },
                'NUMBER ANALYSIS': {
                    'Risk Level': number_analysis.get('risk_level', 'low').upper(),
                    'Pattern': number_analysis.get('pattern', 'Normal'),
                    'Number Type': number_analysis.get('number_type', 'Unknown'),
                    'Total Digits': number_analysis.get('total_digits', 'N/A')
                },
                'ADDITIONAL INTELLIGENCE': {
                    'External Verification': str(results.get('external_verification', 'N/A')),
                    'SIM Owner Status': results.get('sim_owner_status', {}).get('status', 'N/A')
                }
            }
        
        return formatted
    
    def generate_json(self, payload):
        """Generate JSON report with target details."""
        target_info = self._get_target_info(payload)
        filename = self._generate_filename(payload)
        fname = os.path.join(REPORTS_DIR, f"{filename}.json")
        
        # Create enhanced payload with display information
        report_data = {
            'report_metadata': {
                'generated_at': datetime.now().isoformat(),
                'report_id': payload.get('case_id', 'N/A'),
                'investigator': payload.get('investigator', 'Unknown'),
                'target_display_name': target_info['display_name'],
                'target_details': target_info['details']
            },
            'original_data': payload
        }
        
        with open(fname, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, default=str)
        return fname
    
    def generate_pdf(self, payload):
        """Generate professional PDF report with target details."""
        filename = self._generate_filename(payload)
        fname = os.path.join(REPORTS_DIR, f"{filename}.pdf")
        
        # Create PDF document
        doc = SimpleDocTemplate(fname, pagesize=letter)
        story = []
        
        # Title
        title_style = self.styles['Title']
        title = Paragraph(f"INTELLIGENCE REPORT: {payload.get('target_type', 'Unknown').upper()}", title_style)
        story.append(title)
        story.append(Spacer(1, 20))
        
        # Target Information Header
        target_info = self._get_target_info(payload)
        header_style = self.styles['Heading2']
        story.append(Paragraph("TARGET INFORMATION", header_style))
        story.append(Spacer(1, 10))
        
        # Target details table
        target_data = [
            ['Field', 'Value'],
            ['Target', target_info['display_name']]
        ]
        for key, value in target_info['details'].items():
            target_data.append([key, str(value)])
        
        target_table = Table(target_data, colWidths=[150, 350])
        target_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(target_table)
        story.append(Spacer(1, 20))
        
        # Case Details
        story.append(Paragraph("CASE DETAILS", header_style))
        story.append(Spacer(1, 10))
        
        case_data = [
            ['Case ID', payload.get('case_id', 'N/A')],
            ['Investigator', payload.get('investigator', 'Unknown')],
            ['Generated', datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
            ['Reputation Score', str(payload.get('reputation', 'N/A'))]
        ]
        
        case_table = Table(case_data, colWidths=[150, 350])
        case_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('PADDING', (0, 0), (-1, -1), 6)
        ]))
        story.append(case_table)
        story.append(Spacer(1, 20))
        
        # Intelligence Data
        if payload.get('target_type') == 'phone':
            formatted_data = self._format_intelligence_data(payload)
            
            for section_title, section_data in formatted_data.items():
                story.append(Paragraph(section_title, header_style))
                story.append(Spacer(1, 10))
                
                section_table_data = [['Field', 'Value']]
                for key, value in section_data.items():
                    section_table_data.append([key, str(value)])
                
                section_table = Table(section_table_data, colWidths=[150, 350])
                section_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('FONTNAME', (0, 1), (0, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 1), (-1, -1), 9),
                ]))
                story.append(section_table)
                story.append(Spacer(1, 15))
        else:
            # Generic intelligence display for non-phone targets
            normal_style = self.styles['Normal']
            story.append(Paragraph("INTELLIGENCE SUMMARY", header_style))
            story.append(Spacer(1, 10))
            
            results = str(payload.get('results', 'No data available'))
            story.append(Paragraph(results[:2000].replace('\n', '<br/>'), normal_style))
        
        # Footer
        story.append(Spacer(1, 30))
        footer_style = self.styles['Italic']
        story.append(Paragraph("This report is generated for intelligence purposes only.", footer_style))
        story.append(Paragraph(f"Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", footer_style))
        
        # Build PDF
        doc.build(story)
        return fname
    
    def generate(self, payload):
        """Generate both JSON and PDF reports."""
        j = self.generate_json(payload)
        p = self.generate_pdf(payload)
        
        return {
            'json': j,
            'pdf': p,
            'target': self._get_target_info(payload)['display_name']
        }


# Example usage
if __name__ == "__main__":
    # Test with phone intelligence data
    test_payload = {
        'case_id': 'CASE-2024-001',
        'investigator': 'John Doe',
        'target_type': 'phone',
        'target': '+250781234567',
        'reputation': 85,
        'results': {
            'basic_info': {
                'number': '+250 781 234 567',
                'national_format': '0781 234 567',
                'country': 'Rwanda',
                'region': 'RW',
                'valid': True
            },
            'carrier_information': {
                'standard_carrier': 'MTN Rwanda',
                'display_name': 'MTN (MTN Rwandacell PLC)',
                'detailed_carrier': {
                    'carrier_name': 'MTN Rwanda',
                    'brand': 'MTN',
                    'full_name': 'MTN Rwandacell PLC',
                    'type': 'mobile',
                    'prefix': '078'
                }
            },
            'location_information': {
                'timezone': ['Africa/Kigali'],
                'approximate_location': 'Kigali, Rwanda',
                'specific_location': {
                    'city': 'Kigali',
                    'coordinates': {
                        'latitude': -1.9706,
                        'longitude': 30.1044
                    }
                }
            },
            'number_analysis': {
                'risk_level': 'low',
                'pattern': 'Normal',
                'number_type': 'mobile',
                'total_digits': 9
            },
            'external_verification': 'MTN Rwanda - Mobile',
            'sim_owner_status': {
                'status': 'restricted',
                'message': 'SIM registration data requires legal authorization'
            }
        }
    }
    
    generator = ReportGenerator()
    reports = generator.generate(test_payload)
    print(f"Reports generated: {json.dumps(reports, indent=2)}")