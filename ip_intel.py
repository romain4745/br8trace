"""IP intelligence: WHOIS, geolocation, ASN, ISP, VPN/proxy checks with MongoDB storage."""
import os
import re
import socket
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from pathlib import Path
import requests
import whois
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import PyMongoError
import dns.resolver
import ssl
import OpenSSL
from urllib.parse import urlparse
import ipaddress

load_dotenv()

# Configuration from .env
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017')
MONGO_DB = os.getenv('MONGO_DB', 'inteltrace')
TOR_PROXY = os.getenv('TOR_PROXY')
INVESTIGATOR_NAME = os.getenv('INVESTIGATOR_NAME', 'Analyst')
REPORTS_DIR = Path(os.getenv('REPORTS_DIR', './reports'))

# Optional API keys
IPINFO_TOKEN = os.getenv('IPINFO_TOKEN', '')
ABUSEIPDB_KEY = os.getenv('ABUSEIPDB_KEY', '')
SHODAN_API_KEY = os.getenv('SHODAN_API_KEY', '')
VIRUSTOTAL_API_KEY = os.getenv('VIRUSTOTAL_API_KEY', '')


class MongoDBManager:
    """Manages MongoDB connections and operations."""
    
    def __init__(self, uri: str, db_name: str):
        self.client = MongoClient(uri)
        self.db = self.client[db_name]
        self._ensure_indexes()
    
    def _ensure_indexes(self):
        """Create necessary indexes for efficient querying."""
        # Investigations collection
        self.db.investigations.create_index([("investigation_id", 1)], unique=True)
        self.db.investigations.create_index([("timestamp", -1)])
        self.db.investigations.create_index([("ip", 1)])
        
        # IP intelligence cache
        self.db.ip_intel_cache.create_index([("ip", 1)], unique=True)
        self.db.ip_intel_cache.create_index([("timestamp", -1)])
        
        # Reports collection
        self.db.reports.create_index([("report_id", 1)], unique=True)
        self.db.reports.create_index([("timestamp", -1)])
        self.db.reports.create_index([("investigation_id", 1)])
        
        # TTL index on cache (auto-expire after 7 days)
        self.db.ip_intel_cache.create_index(
            [("timestamp", 1)], 
            expireAfterSeconds=604800  # 7 days
        )
    
    def save_investigation(self, investigation_data: Dict) -> str:
        """Save investigation data and return investigation ID."""
        investigation_id = hashlib.sha256(
            f"{investigation_data['ip']}{datetime.utcnow().isoformat()}".encode()
        ).hexdigest()[:16]
        
        document = {
            "investigation_id": investigation_id,
            "timestamp": datetime.utcnow(),
            "investigator": investigation_data.get('investigator', INVESTIGATOR_NAME),
            "ip": investigation_data['ip'],
            "data": investigation_data['data'],
            "summary": investigation_data.get('summary', {}),
            "tags": investigation_data.get('tags', []),
            "notes": investigation_data.get('notes', '')
        }
        
        try:
            self.db.investigations.insert_one(document)
            return investigation_id
        except PyMongoError as e:
            print(f"MongoDB error saving investigation: {e}")
            return None
    
    def get_investigation(self, investigation_id: str) -> Optional[Dict]:
        """Retrieve investigation by ID."""
        return self.db.investigations.find_one({"investigation_id": investigation_id})
    
    def get_ip_history(self, ip: str, limit: int = 10) -> List[Dict]:
        """Get investigation history for an IP."""
        return list(self.db.investigations.find(
            {"ip": ip}
        ).sort("timestamp", -1).limit(limit))
    
    def cache_ip_intel(self, ip: str, data: Dict) -> None:
        """Cache IP intelligence data."""
        try:
            self.db.ip_intel_cache.update_one(
                {"ip": ip},
                {"$set": {
                    "data": data,
                    "timestamp": datetime.utcnow()
                }},
                upsert=True
            )
        except PyMongoError as e:
            print(f"MongoDB error caching IP intel: {e}")
    
    def get_cached_intel(self, ip: str, max_age_hours: int = 24) -> Optional[Dict]:
        """Get cached IP intelligence if not expired."""
        cache = self.db.ip_intel_cache.find_one({"ip": ip})
        if cache:
            age = datetime.utcnow() - cache['timestamp']
            if age < timedelta(hours=max_age_hours):
                return cache['data']
        return None
    
    def save_report(self, report_data: Dict) -> str:
        """Save a generated report."""
        report_id = hashlib.sha256(
            f"{report_data.get('title', '')}{datetime.utcnow().isoformat()}".encode()
        ).hexdigest()[:12]
        
        document = {
            "report_id": report_id,
            "timestamp": datetime.utcnow(),
            "investigator": report_data.get('investigator', INVESTIGATOR_NAME),
            "title": report_data.get('title', 'Untitled Report'),
            "investigation_ids": report_data.get('investigation_ids', []),
            "summary": report_data.get('summary', ''),
            "findings": report_data.get('findings', []),
            "severity": report_data.get('severity', 'low'),
            "file_path": report_data.get('file_path', '')
        }
        
        try:
            self.db.reports.insert_one(document)
            return report_id
        except PyMongoError as e:
            print(f"MongoDB error saving report: {e}")
            return None
    
    def search_investigations(self, query: Dict, limit: int = 50) -> List[Dict]:
        """Search investigations with filters."""
        return list(self.db.investigations.find(query).sort("timestamp", -1).limit(limit))
    
    def get_statistics(self) -> Dict:
        """Get database statistics."""
        return {
            "total_investigations": self.db.investigations.count_documents({}),
            "total_reports": self.db.reports.count_documents({}),
            "unique_ips": len(self.db.investigations.distinct("ip")),
            "investigations_today": self.db.investigations.count_documents({
                "timestamp": {
                    "$gte": datetime.utcnow().replace(hour=0, minute=0, second=0)
                }
            }),
            "cache_size": self.db.ip_intel_cache.count_documents({})
        }


class IPIntel:
    """Advanced IP intelligence gathering with MongoDB integration."""
    
    def __init__(self, use_tor=False, use_cache=True):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': f'Inteltrace/2.0 ({INVESTIGATOR_NAME})'
        })
        
        if use_tor and TOR_PROXY:
            self.session.proxies.update({
                'http': TOR_PROXY, 
                'https': TOR_PROXY
            })
        
        # Initialize MongoDB
        try:
            self.db = MongoDBManager(MONGO_URI, MONGO_DB)
            self.mongo_available = True
        except Exception as e:
            print(f"Warning: MongoDB not available - {e}")
            self.mongo_available = False
        
        self.use_cache = use_cache and self.mongo_available
        self._dns_cache = {}
        
        # Ensure reports directory exists
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    
    def resolve_domain(self, ip: str) -> List[str]:
        """Reverse DNS lookup to find domains hosted on IP."""
        try:
            if ip in self._dns_cache:
                return self._dns_cache[ip]
            
            hostnames = socket.gethostbyaddr(ip)
            domains = [hostnames[0]] if hostnames else []
            self._dns_cache[ip] = domains
            return domains
        except (socket.herror, socket.gaierror):
            return []
    
    def whois_lookup(self, ip: str) -> Dict[str, Any]:
        """Enhanced WHOIS lookup with parsed information."""
        try:
            w = whois.whois(ip)
            if not w or not w.domain_name:
                return {"error": "No WHOIS data found"}
            
            return {
                "domain_name": w.domain_name if isinstance(w.domain_name, str) 
                              else w.domain_name[0] if w.domain_name else None,
                "registrar": w.registrar,
                "creation_date": self._parse_date(w.creation_date),
                "expiration_date": self._parse_date(w.expiration_date),
                "updated_date": self._parse_date(w.updated_date),
                "name_servers": w.name_servers if isinstance(w.name_servers, list) 
                                else [w.name_servers] if w.name_servers else [],
                "organization": w.org,
                "country": w.country,
                "city": w.city,
                "state": w.state,
                "registrant": w.name,
                "email": self._extract_emails(w),
                "raw": str(w)[:1000]  # Limit raw data size
            }
        except Exception as e:
            return {"error": f"WHOIS lookup failed: {str(e)}"}
    
    def ipinfo_lookup(self, ip: str) -> Dict[str, Any]:
        """Comprehensive IPInfo lookup with organization details."""
        try:
            url = f'https://ipinfo.io/{ip}/json'
            if IPINFO_TOKEN:
                url += f'?token={IPINFO_TOKEN}'
            
            r = self.session.get(url, timeout=10)
            data = r.json()
            
            if 'error' in data:
                return {"error": data['error'].get('message', 'Unknown error')}
            
            return {
                "ip": data.get('ip'),
                "hostname": data.get('hostname'),
                "city": data.get('city'),
                "region": data.get('region'),
                "country": data.get('country'),
                "location": data.get('loc'),
                "organization": data.get('org'),
                "postal": data.get('postal'),
                "timezone": data.get('timezone'),
                "asn": self._extract_asn(data.get('org', '')),
                "company": data.get('company', {}).get('name') if isinstance(data.get('company'), dict) else None,
                "abuse_contact": data.get('abuse', {}).get('email') if isinstance(data.get('abuse'), dict) else None,
                "type": data.get('type', 'business')
            }
        except Exception as e:
            return {"error": f"IPInfo lookup failed: {str(e)}"}
    
    def ssl_certificate_info(self, ip: str, port: int = 443) -> Dict[str, Any]:
        """Extract SSL certificate information to identify websites."""
        try:
            cert = ssl.get_server_certificate((ip, port))
            x509 = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, cert)
            
            subject = dict(x509.get_subject().get_components())
            issuer = dict(x509.get_issuer().get_components())
            
            # Extract SANs
            sans = []
            for i in range(x509.get_extension_count()):
                ext = x509.get_extension(i)
                if ext.get_short_name() == b'subjectAltName':
                    sans = str(ext).split(', ')
                    sans = [san.strip().replace('DNS:', '') for san in sans]
            
            return {
                "subject": {
                    "CN": subject.get(b'CN', b'').decode(),
                    "O": subject.get(b'O', b'').decode(),
                    "OU": subject.get(b'OU', b'').decode(),
                    "C": subject.get(b'C', b'').decode(),
                    "ST": subject.get(b'ST', b'').decode(),
                    "L": subject.get(b'L', b'').decode()
                },
                "issuer": {
                    "CN": issuer.get(b'CN', b'').decode(),
                    "O": issuer.get(b'O', b'').decode()
                },
                "sans": sans,
                "valid_from": datetime.strptime(
                    x509.get_notBefore().decode(), '%Y%m%d%H%M%SZ'
                ).isoformat(),
                "valid_until": datetime.strptime(
                    x509.get_notAfter().decode(), '%Y%m%d%H%M%SZ'
                ).isoformat(),
                "serial_number": x509.get_serial_number(),
                "version": x509.get_version()
            }
        except Exception:
            return {}
    
    def shodan_lookup(self, ip: str) -> Dict[str, Any]:
        """Query Shodan for device/website information."""
        if not SHODAN_API_KEY:
            return {"error": "Shodan API key not configured"}
        
        try:
            r = self.session.get(
                f'https://api.shodan.io/shodan/host/{ip}',
                params={'key': SHODAN_API_KEY},
                timeout=10
            )
            data = r.json()
            
            if 'error' in data:
                return {"error": data['error']}
            
            devices = []
            websites = []
            for service in data.get('data', []):
                product = service.get('product', '')
                version = service.get('version', '')
                port = service.get('port')
                org = service.get('org', '')
                
                if service.get('http'):
                    host = service['http'].get('host', '')
                    title = service['http'].get('title', '')
                    if host or title:
                        websites.append({
                            "host": host,
                            "title": title,
                            "port": port,
                            "server": service['http'].get('server', ''),
                            "technologies": self._detect_technologies(service)
                        })
                
                if product:
                    devices.append({
                        "product": product,
                        "version": version,
                        "port": port,
                        "org": org,
                        "type": self._categorize_service(product, port)
                    })
            
            return {
                "organization": data.get('org'),
                "isp": data.get('isp'),
                "country": data.get('country_name'),
                "city": data.get('city'),
                "hostnames": data.get('hostnames', []),
                "domains": data.get('domains', []),
                "os": data.get('os'),
                "ports": data.get('ports', []),
                "devices": devices,
                "websites": websites,
                "tags": data.get('tags', []),
                "last_update": data.get('last_update')
            }
        except Exception as e:
            return {"error": f"Shodan lookup failed: {str(e)}"}
    
    def blacklist_check(self, ip: str) -> Dict[str, Any]:
        """Check IP against multiple blacklists."""
        results = {
            "blacklisted": False,
            "lists": [],
            "abuse_reports": 0
        }
        
        # Check AbuseIPDB
        if ABUSEIPDB_KEY:
            try:
                r = self.session.get(
                    'https://api.abuseipdb.com/api/v2/check',
                    params={'ipAddress': ip, 'maxAgeInDays': 90},
                    headers={'Key': ABUSEIPDB_KEY},
                    timeout=10
                )
                data = r.json().get('data', {})
                if data.get('abuseConfidenceScore', 0) > 50:
                    results['blacklisted'] = True
                results['abuse_reports'] = data.get('totalReports', 0)
                results['abuse_score'] = data.get('abuseConfidenceScore', 0)
                results['lists'].append({
                    "name": "AbuseIPDB",
                    "confidence": data.get('abuseConfidenceScore', 0),
                    "reports": data.get('totalReports', 0)
                })
            except Exception:
                pass
        
        # Check DNSBL providers
        dnsbl_providers = [
            "zen.spamhaus.org",
            "bl.spamcop.net",
            "dnsbl.sorbs.net",
            "b.barracudacentral.org"
        ]
        
        reversed_ip = '.'.join(reversed(ip.split('.')))
        for provider in dnsbl_providers:
            try:
                query = f"{reversed_ip}.{provider}"
                answers = dns.resolver.resolve(query, 'A')
                if answers:
                    results['blacklisted'] = True
                    results['lists'].append({
                        "name": provider,
                        "result": str(answers[0])
                    })
            except dns.resolver.NXDOMAIN:
                continue
            except Exception:
                continue
        
        return results
    
    def detect_vpn_proxy(self, ip: str) -> Dict[str, Any]:
        """Detect VPN, proxy, hosting, or residential IP."""
        result = {
            "vpn": False,
            "proxy": False,
            "tor": False,
            "hosting": False,
            "residential": True,
            "confidence": 0
        }
        
        try:
            ipinfo_data = self.ipinfo_lookup(ip)
            org = (ipinfo_data.get('organization') or '').lower()
            company = (ipinfo_data.get('company') or '').lower()
            
            hosting_keywords = [
                'hosting', 'cloud', 'server', 'vps', 'dedicated',
                'amazon', 'aws', 'google cloud', 'azure', 'digitalocean',
                'linode', 'vultr', 'ovh', 'hetzner', 'datacenter',
                'colocation', 'cdn', 'backbone'
            ]
            
            vpn_keywords = [
                'vpn', 'proxy', 'tunnel', 'private internet access',
                'nordvpn', 'expressvpn', 'surfshark', 'protonvpn',
                'mullvad', 'ivpn', 'windscribe', 'hide.me'
            ]
            
            # Tor exit node check
            try:
                tor_exit_list = self.session.get(
                    'https://check.torproject.org/exit-addresses', 
                    timeout=5
                ).text
                if ip in tor_exit_list:
                    result['tor'] = True
                    result['vpn'] = True
                    result['confidence'] += 40
            except Exception:
                pass
            
            if any(keyword in org for keyword in hosting_keywords):
                result['hosting'] = True
                result['residential'] = False
                result['confidence'] += 30
                
                if any(keyword in org for keyword in vpn_keywords):
                    result['vpn'] = True
                    result['confidence'] += 30
            
            if any(keyword in company for keyword in vpn_keywords):
                result['vpn'] = True
                result['confidence'] += 30
            
            asn = self._extract_asn(ipinfo_data.get('organization', ''))
            if asn:
                hosting_asns = ['AS16509', 'AS14618', 'AS14061', 'AS24940', 'AS16276']
                if asn in hosting_asns:
                    result['hosting'] = True
                    result['residential'] = False
                    result['confidence'] += 20
            
            if ipinfo_data.get('type') == 'hosting':
                result['hosting'] = True
                result['residential'] = False
                result['confidence'] += 50
                
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    def identify_website(self, ip: str) -> Dict[str, Any]:
        """Identify websites hosted on the IP."""
        websites = []
        
        # Reverse DNS
        domains = self.resolve_domain(ip)
        for domain in domains:
            websites.append({
                "domain": domain,
                "source": "reverse_dns",
                "verified": False
            })
        
        # HTTP/HTTPS scanning
        for port in [80, 443, 8080, 8443]:
            try:
                protocol = 'https' if port in [443, 8443] else 'http'
                url = f'{protocol}://{ip}:{port}'
                r = self.session.get(url, timeout=3, allow_redirects=True, verify=False)
                
                title_match = re.search(r'<title>(.*?)</title>', r.text, re.IGNORECASE)
                title = title_match.group(1) if title_match else ''
                
                server = r.headers.get('Server', '')
                final_url = r.url
                final_domain = urlparse(final_url).netloc.split(':')[0]
                
                websites.append({
                    "domain": final_domain,
                    "title": title,
                    "port": port,
                    "protocol": protocol,
                    "server": server,
                    "status_code": r.status_code,
                    "source": "http_scan",
                    "verified": True
                })
                
            except (requests.RequestException, ssl.SSLError):
                continue
        
        # SSL certificate
        ssl_info = self.ssl_certificate_info(ip)
        if ssl_info and 'subject' in ssl_info:
            cn = ssl_info['subject'].get('CN', '')
            if cn and cn != ip:
                websites.append({
                    "domain": cn,
                    "source": "ssl_certificate",
                    "verified": True,
                    "ssl_valid_until": ssl_info.get('valid_until')
                })
                
                for san in ssl_info.get('sans', []):
                    if san != cn and san != ip:
                        websites.append({
                            "domain": san,
                            "source": "ssl_san",
                            "verified": True,
                            "ssl_valid_until": ssl_info.get('valid_until')
                        })
        
        # Remove duplicates
        seen = set()
        unique_websites = []
        for site in websites:
            if site['domain'] not in seen:
                seen.add(site['domain'])
                unique_websites.append(site)
        
        return {
            "websites": unique_websites,
            "count": len(unique_websites),
            "primary_domain": unique_websites[0]['domain'] if unique_websites else None
        }
    
    def device_fingerprint(self, ip: str) -> Dict[str, Any]:
        """Fingerprint devices and services running on the IP."""
        common_ports = [21, 22, 23, 25, 53, 80, 110, 143, 443, 993, 995, 
                       3306, 3389, 5432, 5900, 6379, 8080, 8443, 9200]
        
        devices = []
        for port in common_ports:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex((ip, port))
                if result == 0:
                    service = self._identify_service(ip, port)
                    devices.append({
                        "port": port,
                        "service": service,
                        "category": self._categorize_service(service, port)
                    })
                sock.close()
            except Exception:
                continue
        
        return {
            "devices": devices,
            "open_ports": [d['port'] for d in devices],
            "device_count": len(devices)
        }
    
    def collect(self, ip: str, comprehensive: bool = False, 
                use_cache: bool = True, tags: List[str] = None, 
                notes: str = "") -> Dict[str, Any]:
        """Collect comprehensive IP intelligence and store in MongoDB."""
        # Validate IP
        try:
            ipaddress.ip_address(ip)
        except ValueError:
            return {"error": f"Invalid IP address: {ip}"}
        
        # Check cache first
        if self.use_cache and use_cache:
            cached = self.db.get_cached_intel(ip)
            if cached:
                print(f"Using cached data for {ip}")
                cached['cache_hit'] = True
                return cached
        
        data = {
            "ip": ip,
            "timestamp": datetime.utcnow().isoformat(),
            "investigator": INVESTIGATOR_NAME,
            "whois": self.whois_lookup(ip),
            "ipinfo": self.ipinfo_lookup(ip),
            "reverse_dns": self.resolve_domain(ip),
            "vpn_proxy": self.detect_vpn_proxy(ip),
            "blacklist": self.blacklist_check(ip),
            "websites": self.identify_website(ip),
            "devices": self.device_fingerprint(ip)
        }
        
        if comprehensive:
            data['shodan'] = self.shodan_lookup(ip)
            data['ssl_certificates'] = self.ssl_certificate_info(ip)
        
        data['summary'] = self._generate_summary(data)
        data['cache_hit'] = False
        
        # Cache the results
        if self.mongo_available:
            self.db.cache_ip_intel(ip, data)
            
            # Save as investigation
            investigation_doc = {
                "ip": ip,
                "data": data,
                "summary": data['summary'],
                "tags": tags or [],
                "notes": notes,
                "investigator": INVESTIGATOR_NAME
            }
            investigation_id = self.db.save_investigation(investigation_doc)
            data['investigation_id'] = investigation_id
        
        return data
    
    def get_ip_history(self, ip: str) -> List[Dict]:
        """Get investigation history for an IP."""
        if self.mongo_available:
            return self.db.get_ip_history(ip)
        return []
    
    def generate_report(self, ip: str, investigation_id: str = None) -> Dict[str, Any]:
        """Generate a detailed report for an IP investigation."""
        if investigation_id and self.mongo_available:
            investigation = self.db.get_investigation(investigation_id)
            if investigation:
                data = investigation['data']
            else:
                data = self.collect(ip)
        else:
            data = self.collect(ip)
        
        # Create report
        report = {
            "title": f"IP Intelligence Report - {ip}",
            "timestamp": datetime.utcnow().isoformat(),
            "investigator": INVESTIGATOR_NAME,
            "ip": ip,
            "summary": data.get('summary', {}),
            "findings": self._generate_findings(data),
            "risk_assessment": self._assess_risk(data),
            "recommendations": self._generate_recommendations(data),
            "raw_data": data
        }
        
        # Save report to file
        report_filename = f"report_{ip}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        report_path = REPORTS_DIR / report_filename
        
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        # Save to MongoDB
        if self.mongo_available:
            report_doc = {
                "title": report['title'],
                "investigator": INVESTIGATOR_NAME,
                "investigation_ids": [data.get('investigation_id')],
                "summary": json.dumps(report['summary'], default=str),
                "findings": report['findings'],
                "severity": report['risk_assessment']['level'],
                "file_path": str(report_path)
            }
            report_id = self.db.save_report(report_doc)
            report['report_id'] = report_id
        
        report['file_path'] = str(report_path)
        return report
    
    def search_investigations(self, **filters) -> List[Dict]:
        """Search through saved investigations."""
        if self.mongo_available:
            return self.db.search_investigations(filters)
        return []
    
    def get_statistics(self) -> Dict:
        """Get database and investigation statistics."""
        stats = {
            "investigator": INVESTIGATOR_NAME,
            "reports_dir": str(REPORTS_DIR),
            "tor_enabled": bool(TOR_PROXY),
            "apis_configured": {
                "ipinfo": bool(IPINFO_TOKEN),
                "abuseipdb": bool(ABUSEIPDB_KEY),
                "shodan": bool(SHODAN_API_KEY),
                "virustotal": bool(VIRUSTOTAL_API_KEY)
            }
        }
        
        if self.mongo_available:
            stats.update(self.db.get_statistics())
        
        return stats
    
    # Helper methods
    def _parse_date(self, date_obj) -> Optional[str]:
        """Parse various date formats to ISO string."""
        if not date_obj:
            return None
        if isinstance(date_obj, list):
            date_obj = date_obj[0]
        if isinstance(date_obj, datetime):
            return date_obj.isoformat()
        return str(date_obj)
    
    def _extract_emails(self, whois_data) -> List[str]:
        """Extract email addresses from WHOIS data."""
        emails = []
        text = str(whois_data)
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        found = re.findall(email_pattern, text)
        return list(set(found))
    
    def _extract_asn(self, org_string: str) -> Optional[str]:
        """Extract ASN from organization string."""
        match = re.search(r'AS(\d+)', org_string)
        return f"AS{match.group(1)}" if match else None
    
    def _detect_technologies(self, service: Dict) -> List[str]:
        """Detect technologies from service banners."""
        technologies = []
        http = service.get('http', {})
        
        if http.get('components'):
            technologies.extend(http['components'].keys())
        
        server = http.get('server', '')
        if server:
            technologies.append(server)
        
        if http.get('x_powered_by'):
            technologies.append(http['x_powered_by'])
        
        return technologies
    
    def _categorize_service(self, service: str, port: int) -> str:
        """Categorize service type."""
        categories = {
            21: "FTP",
            22: "SSH",
            23: "Telnet",
            25: "SMTP",
            53: "DNS",
            80: "HTTP",
            110: "POP3",
            143: "IMAP",
            443: "HTTPS",
            993: "IMAPS",
            995: "POP3S",
            3306: "MySQL",
            3389: "RDP",
            5432: "PostgreSQL",
            5900: "VNC",
            6379: "Redis",
            8080: "HTTP-Alt",
            8443: "HTTPS-Alt",
            9200: "Elasticsearch"
        }
        return categories.get(port, "Unknown")
    
    def _identify_service(self, ip: str, port: int) -> str:
        """Try to identify service by banner grabbing."""
        try:
            if port == 80 or port == 8080:
                return "HTTP"
            elif port == 443 or port == 8443:
                return "HTTPS"
            elif port == 22:
                return "SSH"
            elif port == 21:
                return "FTP"
            return socket.getservbyport(port)
        except Exception:
            return "Unknown"
    
    def _generate_summary(self, data: Dict) -> Dict[str, Any]:
        """Generate a human-readable summary."""
        summary = {
            "is_legitimate": True,
            "risks": [],
            "notes": []
        }
        
        # VPN/Proxy risks
        if data['vpn_proxy'].get('vpn'):
            summary['is_legitimate'] = False
            summary['risks'].append("VPN/Proxy detected")
        
        if data['vpn_proxy'].get('tor'):
            summary['is_legitimate'] = False
            summary['risks'].append("Tor exit node detected")
        
        if data['vpn_proxy'].get('hosting'):
            summary['notes'].append("IP belongs to hosting provider (not residential)")
        
        # Blacklist risks
        if data['blacklist'].get('blacklisted'):
            summary['is_legitimate'] = False
            summary['risks'].append(f"Listed on {len(data['blacklist']['lists'])} blacklists")
        
        # Website info
        if data['websites']['count'] > 0:
            summary['notes'].append(f"Hosts {data['websites']['count']} website(s)")
            if data['websites']['primary_domain']:
                summary['primary_domain'] = data['websites']['primary_domain']
        
        # Device info
        if data['devices']['device_count'] > 0:
            summary['notes'].append(f"Has {data['devices']['device_count']} open ports/services")
        
        return summary
    
    def _generate_findings(self, data: Dict) -> List[Dict]:
        """Generate detailed findings from the collected data."""
        findings = []
        
        # Location findings
        if data.get('ipinfo', {}).get('city'):
            findings.append({
                "type": "location",
                "severity": "info",
                "description": f"IP located in {data['ipinfo']['city']}, {data['ipinfo']['country']}"
            })
        
        # Organization findings
        if data.get('ipinfo', {}).get('organization'):
            findings.append({
                "type": "organization",
                "severity": "info",
                "description": f"Organization: {data['ipinfo']['organization']}"
            })
        
        # VPN/Proxy findings
        vpn_data = data.get('vpn_proxy', {})
        if vpn_data.get('vpn'):
            findings.append({
                "type": "anonymity",
                "severity": "high",
                "description": "VPN/Proxy detected - possible anonymity service"
            })
        if vpn_data.get('tor'):
            findings.append({
                "type": "anonymity",
                "severity": "critical",
                "description": "Tor exit node detected"
            })
        
        # Blacklist findings
        blacklist = data.get('blacklist', {})
        if blacklist.get('blacklisted'):
            findings.append({
                "type": "threat",
                "severity": "high",
                "description": f"IP listed on {len(blacklist['lists'])} blacklists"
            })
        
        # Website findings
        websites = data.get('websites', {})
        if websites.get('count', 0) > 0:
            findings.append({
                "type": "hosting",
                "severity": "info",
                "description": f"Hosting {websites['count']} website(s) including: " +
                             ", ".join([w['domain'] for w in websites['websites'][:3]])
            })
        
        return findings
    
    def _assess_risk(self, data: Dict) -> Dict[str, Any]:
        """Assess the risk level of the IP."""
        risk_score = 0
        
        if data.get('vpn_proxy', {}).get('tor'):
            risk_score += 50
        if data.get('vpn_proxy', {}).get('vpn'):
            risk_score += 30
        if data.get('blacklist', {}).get('blacklisted'):
            risk_score += 40
        
        if risk_score >= 70:
            level = "critical"
        elif risk_score >= 50:
            level = "high"
        elif risk_score >= 30:
            level = "medium"
        elif risk_score > 0:
            level = "low"
        else:
            level = "none"
        
        return {
            "score": min(risk_score, 100),
            "level": level
        }
    
    def _generate_recommendations(self, data: Dict) -> List[str]:
        """Generate security recommendations based on findings."""
        recommendations = []
        
        if data.get('vpn_proxy', {}).get('tor'):
            recommendations.append("Block Tor exit node - high risk of malicious activity")
        
        if data.get('blacklist', {}).get('blacklisted'):
            recommendations.append("IP is blacklisted - investigate recent abuse reports")
        
        if data.get('devices', {}).get('device_count', 0) > 5:
            recommendations.append("Multiple services exposed - consider security audit")
        
        if not recommendations:
            recommendations.append("No immediate threats detected - continue monitoring")
        
        return recommendations
    
    def batch_collect(self, ips: List[str], comprehensive: bool = False) -> Dict[str, Any]:
        """Collect intelligence for multiple IPs."""
        results = {}
        for ip in ips:
            results[ip] = self.collect(ip, comprehensive)
        return results
    
    def close(self):
        """Close database connection."""
        if self.mongo_available:
            self.db.client.close()


# CLI Interface
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Inteltrace - IP Intelligence & Investigation Tool"
    )
    parser.add_argument("ip", nargs="+", help="IP address(es) to analyze")
    parser.add_argument("--tor", action="store_true", help="Use Tor proxy")
    parser.add_argument("--comprehensive", action="store_true", 
                       help="Perform comprehensive analysis (slower)")
    parser.add_argument("--report", action="store_true", 
                       help="Generate detailed report")
    parser.add_argument("--history", action="store_true",
                       help="Show investigation history")
    parser.add_argument("--tags", nargs="+", help="Tags for the investigation")
    parser.add_argument("--notes", help="Notes for the investigation")
    parser.add_argument("--output", help="Save results to JSON file")
    parser.add_argument("--stats", action="store_true",
                       help="Show database statistics")
    parser.add_argument("--search", help="Search investigations (JSON query)")
    
    args = parser.parse_args()
    
    # Disable SSL warnings for scanning
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    intel = IPIntel(use_tor=args.tor)
    
    try:
        if args.stats:
            print(json.dumps(intel.get_statistics(), indent=2, default=str))
        elif args.search:
            try:
                query = json.loads(args.search)
                results = intel.search_investigations(**query)
                print(json.dumps(results, indent=2, default=str))
            except json.JSONDecodeError:
                print("Error: Invalid JSON query")
        elif args.history and len(args.ip) == 1:
            history = intel.get_ip_history(args.ip[0])
            print(f"Investigation history for {args.ip[0]}:")
            for inv in history:
                print(f"  - {inv['timestamp']}: {inv['summary'].get('notes', [])}")
        else:
            for ip in args.ip:
                print(f"\nAnalyzing {ip}...")
                
                if args.report:
                    result = intel.generate_report(ip)
                    print(f"Report generated: {result.get('file_path', 'N/A')}")
                else:
                    result = intel.collect(
                        ip, 
                        comprehensive=args.comprehensive,
                        tags=args.tags,
                        notes=args.notes
                    )
                
                if args.output:
                    with open(args.output, 'w') as f:
                        json.dump(result, f, indent=2, default=str)
                    print(f"Results saved to {args.output}")
                else:
                    # Print summary
                    summary = result.get('summary', {})
                    print(f"\nSummary for {ip}:")
                    print(f"  Legitimate: {summary.get('is_legitimate', 'Unknown')}")
                    if summary.get('risks'):
                        print(f"  Risks: {', '.join(summary['risks'])}")
                    if summary.get('notes'):
                        print(f"  Notes: {', '.join(summary['notes'])}")
                    if result.get('investigation_id'):
                        print(f"  Investigation ID: {result['investigation_id']}")
    finally:
        intel.close()