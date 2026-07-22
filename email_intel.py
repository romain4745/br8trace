

import os
import re
import json
import hashlib
import requests
from datetime import datetime
from urllib.parse import quote
from concurrent.futures import ThreadPoolExecutor, as_completed

CONFIG = {
    'EMAILREP_API_KEY': '',         
    'VIRUSTOTAL_API_KEY': '55d27f2088a1b8dbf28e0f3180249ea4599b99a4815264d85d6501ef0e5fe82f',
    'REPORTS_DIR': './reports',
}

os.makedirs(CONFIG['REPORTS_DIR'], exist_ok=True)


class EmailIntel:
    """Production-ready email intelligence with registration checking."""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        
        # Platform registration check endpoints (not just password reset)
        self.platform_registration_checks = {
            # Social Media
            'Facebook': {
                'url': 'https://www.facebook.com/ajax/login/help/identify.php?ctx=recover',
                'method': 'POST',
                'data': {'email': '{email}'},
                'registered_indicator': 'status_code_200',
                'type': 'social_media'
            },
            'Instagram': {
                'url': 'https://www.instagram.com/api/v1/web/accounts/web_create_ajax/attempt/',
                'method': 'POST',
                'data': {'email': '{email}'},
                'registered_indicator': 'json_response',
                'json_key': 'errors',
                'type': 'social_media'
            },
            'Twitter/X': {
                'url': 'https://api.twitter.com/i/users/email_available.json',
                'method': 'GET',
                'params': {'email': '{email}'},
                'registered_indicator': 'json_response',
                'json_key': 'taken',
                'type': 'social_media'
            },
            'LinkedIn': {
                'url': 'https://www.linkedin.com/uas/request-password-reset',
                'method': 'POST',
                'data': {'session_key': '{email}'},
                'registered_indicator': 'no_error_redirect',
                'type': 'social_media'
            },
            'GitHub': {
                'url': 'https://github.com/signup_check/email',
                'method': 'POST',
                'data': {'value': '{email}'},
                'registered_indicator': 'email_exists',
                'type': 'development'
            },
            'GitLab': {
                'url': 'https://gitlab.com/users/sign_up',
                'method': 'GET',
                'registered_indicator': 'status_code_200',
                'type': 'development'
            },
            'Reddit': {
                'url': 'https://www.reddit.com/api/v1/account/check_email',
                'method': 'POST',
                'data': {'email': '{email}'},
                'registered_indicator': 'taken',
                'type': 'social_media'
            },
            'Pinterest': {
                'url': 'https://www.pinterest.com/resource/EmailExistsResource/get/',
                'method': 'GET',
                'params': {'source_url': '/', 'data': '{{"options":{{"email":"{email}"}}}}'},
                'registered_indicator': 'json_response',
                'json_key': 'exists',
                'type': 'social_media'
            },
            'Spotify': {
                'url': 'https://www.spotify.com/api/signup/validate',
                'method': 'POST',
                'data': {'email': '{email}'},
                'registered_indicator': 'email_exists',
                'type': 'entertainment'
            },
            'Tumblr': {
                'url': 'https://www.tumblr.com/svc/account/register',
                'method': 'POST',
                'data': {'email': '{email}'},
                'registered_indicator': 'email_exists',
                'type': 'social_media'
            },
            'Discord': {
                'url': 'https://discord.com/api/v9/auth/register',
                'method': 'POST',
                'data': {'email': '{email}'},
                'registered_indicator': 'email_already_registered',
                'type': 'communication'
            },
            'Snapchat': {
                'url': 'https://accounts.snapchat.com/accounts/check_email',
                'method': 'POST',
                'data': {'email': '{email}'},
                'registered_indicator': 'has_account',
                'type': 'social_media'
            },
            'TikTok': {
                'url': 'https://www.tiktok.com/passport/email/check/',
                'method': 'POST',
                'data': {'email': '{email}'},
                'registered_indicator': 'email_exists',
                'type': 'social_media'
            },
            
            # E-commerce & Services
            'Amazon': {
                'url': 'https://www.amazon.com/ap/register',
                'method': 'POST',
                'data': {'email': '{email}'},
                'registered_indicator': 'email_exists',
                'type': 'ecommerce'
            },
            'eBay': {
                'url': 'https://signup.ebay.com/pa/crte',
                'method': 'POST',
                'data': {'email': '{email}'},
                'registered_indicator': 'email_exists',
                'type': 'ecommerce'
            },
            'PayPal': {
                'url': 'https://www.paypal.com/authflow/entry/',
                'method': 'POST',
                'data': {'email': '{email}'},
                'registered_indicator': 'exists',
                'type': 'payment'
            },
            'Shopify': {
                'url': 'https://www.shopify.com/api/check_email',
                'method': 'POST',
                'data': {'email': '{email}'},
                'registered_indicator': 'exists',
                'type': 'ecommerce'
            },
            'Etsy': {
                'url': 'https://www.etsy.com/api/v3/ajax/bespoke/member/validate-email',
                'method': 'POST',
                'data': {'email': '{email}'},
                'registered_indicator': 'email_exists',
                'type': 'ecommerce'
            },
            
            # Gaming
            'Steam': {
                'url': 'https://store.steampowered.com/join/checkemailavail',
                'method': 'POST',
                'data': {'email': '{email}'},
                'registered_indicator': 'email_exists',
                'type': 'gaming'
            },
            'Epic Games': {
                'url': 'https://www.epicgames.com/id/api/account/email/exists',
                'method': 'POST',
                'data': {'email': '{email}'},
                'registered_indicator': 'exists',
                'type': 'gaming'
            },
            'Roblox': {
                'url': 'https://auth.roblox.com/v1/validate/email',
                'method': 'POST',
                'data': {'email': '{email}'},
                'registered_indicator': 'is_valid',
                'type': 'gaming'
            },
            
            # Professional & Development
            'Stack Overflow': {
                'url': 'https://stackoverflow.com/users/signup',
                'method': 'POST',
                'data': {'email': '{email}'},
                'registered_indicator': 'email_exists',
                'type': 'professional'
            },
            'Medium': {
                'url': 'https://medium.com/m/signin',
                'method': 'POST',
                'data': {'email': '{email}'},
                'registered_indicator': 'exists',
                'type': 'professional'
            },
            'Quora': {
                'url': 'https://www.quora.com/api/check_email',
                'method': 'POST',
                'data': {'email': '{email}'},
                'registered_indicator': 'exists',
                'type': 'professional'
            },
            
            # Travel & Services
            'Airbnb': {
                'url': 'https://www.airbnb.com/api/v2/email_check',
                'method': 'POST',
                'data': {'email': '{email}'},
                'registered_indicator': 'email_exists',
                'type': 'travel'
            },
            'Uber': {
                'url': 'https://auth.uber.com/v2/email/exists',
                'method': 'POST',
                'data': {'email': '{email}'},
                'registered_indicator': 'exists',
                'type': 'transport'
            },
            'Booking.com': {
                'url': 'https://account.booking.com/register',
                'method': 'POST',
                'data': {'email': '{email}'},
                'registered_indicator': 'email_exists',
                'type': 'travel'
            },
            
            # Additional Services
            'Patreon': {
                'url': 'https://www.patreon.com/api/auth/check_email',
                'method': 'POST',
                'data': {'email': '{email}'},
                'registered_indicator': 'taken',
                'type': 'creator'
            },
            'OnlyFans': {
                'url': 'https://onlyfans.com/api2/v2/users/check',
                'method': 'POST',
                'data': {'email': '{email}'},
                'registered_indicator': 'exists',
                'type': 'creator'
            },
            'BitcoinTalk': {
                'url': 'https://bitcointalk.org/index.php?action=register',
                'method': 'POST',
                'data': {'email': '{email}'},
                'registered_indicator': 'email_exists',
                'type': 'crypto'
            }
        }
        
        # Dark web and deep web monitoring sources
        self.darkweb_sources = {
            'Have I Been Pwned (Dark Web)': {
                'url': 'https://haveibeenpwned.com/api/v3/breachedaccount/{email}',
                'method': 'GET',
                'type': 'dark_web_breaches'
            },
            'Firefox Monitor': {
                'url': 'https://monitor.firefox.com/api/v1/scan',
                'method': 'POST',
                'type': 'breach_monitoring'
            },
            'IntelX': {
                'url': 'https://2.intelx.io/phonebook/search?k={email}',
                'method': 'GET',
                'type': 'deep_web_search'
            },
            'DeHashed (Public)': {
                'url': 'https://dehashed.com/search?query={email}',
                'method': 'GET',
                'type': 'dark_web_exposure'
            },
            'SnusBase (Public)': {
                'url': 'https://snusbase.com/search?q={email}',
                'method': 'GET',
                'type': 'dark_web_exposure'
            }
        }
        
        # Common disposable email domains
        self.disposable_domains = [
            'mailinator.com', 'guerrillamail.com', 'tempmail.com', '10minutemail.com',
            'yopmail.com', 'throwaway.email', 'sharklasers.com', 'trashmail.com',
            'temp-mail.org', 'fakeinbox.com', 'emailondeck.com', 'spam4.me',
            'getnada.com', 'tempinbox.com', 'throwawaymail.com', 'tmpmail.org',
            'dispostable.com', 'maildrop.cc', 'harakirimail.com', 'spambog.com',
            'bccto.me', 'chacuo.net', 'discard.email', 'mailnesia.com',
            'mintemail.com', 'mytrashmail.com', 'nwytg.net', 'objectmail.com',
            'oneoffemail.com', 'owlymail.com', 'sibmail.com', 'trashmail.de',
            'trashmail.es', 'trashmail.fr', 'trashmail.nl', 'trashmail.ws',
            'wegwerfemail.de', 'wh4f.org', 'wuzup.net', 'xoxy.net'
        ]
    
    def validate_email(self, email):
        """Validate email format."""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    def check_platform_registration(self, platform_name, config, email):
        """Check if email is registered on a specific platform."""
        try:
            url = config['url']
            method = config.get('method', 'GET')
            
            # Prepare URL with email
            if '{email}' in url:
                url = url.replace('{email}', quote(email))
            
            # Prepare data/params
            data = None
            params = None
            
            if 'data' in config:
                data = {}
                for key, value in config['data'].items():
                    if isinstance(value, str) and '{email}' in value:
                        data[key] = value.replace('{email}', email)
                    else:
                        data[key] = value
            
            if 'params' in config:
                params = {}
                for key, value in config['params'].items():
                    if isinstance(value, str) and '{email}' in value:
                        params[key] = value.replace('{email}', email)
                    else:
                        params[key] = value
            
            # Make request
            if method == 'POST':
                response = self.session.post(url, data=data, params=params, timeout=10, allow_redirects=False)
            else:
                response = self.session.get(url, params=params, timeout=10, allow_redirects=False)
            
            # Check registration indicators
            indicator = config.get('registered_indicator', '')
            
            if indicator == 'status_code_200':
                registered = response.status_code == 200
            elif indicator == 'json_response':
                try:
                    json_data = response.json()
                    json_key = config.get('json_key', '')
                    if json_key in json_data:
                        registered = bool(json_data[json_key])
                    elif 'exists' in str(json_data).lower():
                        registered = True
                    else:
                        registered = False
                except:
                    registered = False
            elif indicator == 'no_error_redirect':
                registered = response.status_code == 200 and 'error' not in response.url.lower()
            elif indicator in ['email_exists', 'taken', 'exists', 'has_account', 'email_already_registered', 'is_valid']:
                try:
                    json_data = response.json()
                    registered = str(json_data).lower().find(indicator.replace('_', '')) != -1
                except:
                    registered = response.status_code == 200
            else:
                registered = response.status_code == 200
            
            return {
                'platform': platform_name,
                'type': config.get('type', 'unknown'),
                'registered': registered,
                'status_code': response.status_code,
                'check_method': 'email_registration_check'
            }
            
        except requests.exceptions.Timeout:
            return {
                'platform': platform_name,
                'type': config.get('type', 'unknown'),
                'registered': False,
                'error': 'timeout'
            }
        except Exception as e:
            return {
                'platform': platform_name,
                'type': config.get('type', 'unknown'),
                'registered': False,
                'error': str(e)[:100]
            }
    
    def check_all_platforms(self, email):
        """Check email registration on all platforms using threading."""
        results = {}
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {
                executor.submit(self.check_platform_registration, platform, config, email): platform
                for platform, config in self.platform_registration_checks.items()
            }
            
            for future in as_completed(futures):
                result = future.result()
                platform = result['platform']
                results[platform] = result
        
        return results
    
    def check_darkweb_exposure(self, email):
        """Check email exposure on dark web and deep web sources."""
        darkweb_results = {}
        
        for source_name, config in self.darkweb_sources.items():
            try:
                url = config['url'].replace('{email}', quote(email))
                method = config.get('method', 'GET')
                
                if method == 'POST':
                    if source_name == 'Firefox Monitor':
                        email_hash = hashlib.sha1(email.lower().encode()).hexdigest().upper()
                        response = self.session.post(
                            url, 
                            json={'emailHash': email_hash}, 
                            headers={'Content-Type': 'application/json'},
                            timeout=15
                        )
                    else:
                        response = self.session.post(url, timeout=15)
                else:
                    headers = {}
                    if source_name == 'Have I Been Pwned (Dark Web)':
                        headers['User-Agent'] = 'Br8Trace-DarkWeb'
                    
                    response = self.session.get(url, headers=headers, timeout=15)
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        darkweb_results[source_name] = {
                            'found': True,
                            'type': config.get('type', 'unknown'),
                            'source': source_name,
                            'data_summary': str(data)[:500]
                        }
                    except:
                        darkweb_results[source_name] = {
                            'found': response.status_code == 200,
                            'type': config.get('type', 'unknown'),
                            'source': source_name,
                            'response_size': len(response.text)
                        }
                elif response.status_code == 404:
                    darkweb_results[source_name] = {
                        'found': False,
                        'type': config.get('type', 'unknown'),
                        'source': source_name,
                        'status': 'not_found'
                    }
                else:
                    darkweb_results[source_name] = {
                        'found': False,
                        'type': config.get('type', 'unknown'),
                        'source': source_name,
                        'status_code': response.status_code
                    }
                    
            except Exception as e:
                darkweb_results[source_name] = {
                    'found': False,
                    'error': str(e)[:100],
                    'type': config.get('type', 'unknown'),
                    'source': source_name
                }
        
        return darkweb_results
    
    def breach_check_hibp(self, email):
        """Check email against Have I Been Pwned database."""
        try:
            # k-anonymity check
            email_hash = hashlib.sha1(email.lower().encode()).hexdigest().upper()
            prefix = email_hash[:5]
            suffix = email_hash[5:]
            
            url = f'https://api.pwnedpasswords.com/range/{prefix}'
            response = self.session.get(url, headers={'User-Agent': 'Br8Trace'}, timeout=10)
            
            k_anon_found = False
            k_anon_count = 0
            
            if response.status_code == 200:
                for line in response.text.splitlines():
                    if ':' in line:
                        h, count = line.split(':')
                        if h == suffix:
                            k_anon_found = True
                            k_anon_count = int(count)
                            break
            
            # Get detailed breach info
            url = f'https://haveibeenpwned.com/api/v3/breachedaccount/{email}'
            headers = {'User-Agent': 'Br8Trace'}
            params = {'truncateResponse': 'false', 'includeUnverified': 'true'}
            
            response = self.session.get(url, headers=headers, params=params, timeout=15)
            
            if response.status_code == 200:
                breaches = response.json()
                return {
                    'k_anonymity_found': k_anon_found,
                    'k_anonymity_count': k_anon_count,
                    'breaches_found': len(breaches),
                    'breaches': [{
                        'name': breach.get('Name'),
                        'domain': breach.get('Domain'),
                        'date': breach.get('BreachDate'),
                        'description': breach.get('Description', '')[:200],
                        'data_classes': breach.get('DataClasses', []),
                        'is_verified': breach.get('IsVerified', False),
                        'is_sensitive': breach.get('IsSensitive', False),
                        'pwn_count': breach.get('PwnCount', 0)
                    } for breach in breaches]
                }
            elif response.status_code == 404:
                return {
                    'k_anonymity_found': k_anon_found,
                    'k_anonymity_count': k_anon_count,
                    'breaches_found': 0,
                    'breaches': []
                }
            
            return {'error': f'HIBP API error: {response.status_code}'}
            
        except Exception as e:
            return {'error': str(e)}
    
    def emailrep_check(self, email):
        """Check email reputation using EmailRep.io API."""
        if not CONFIG['EMAILREP_API_KEY']:
            return {'status': 'api_key_not_configured'}
        
        try:
            url = f'https://emailrep.io/{email}'
            headers = {'Key': CONFIG['EMAILREP_API_KEY'], 'User-Agent': 'Br8Trace'}
            
            response = self.session.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                details = data.get('details', {})
                
                return {
                    'reputation': data.get('reputation'),
                    'suspicious': data.get('suspicious', False),
                    'blacklisted': details.get('blacklisted', False),
                    'malicious_activity': details.get('malicious_activity', False),
                    'credentials_leaked': details.get('credentials_leaked', False),
                    'social_profiles': details.get('profiles', []),
                    'references': details.get('references', 0),
                    'last_seen': details.get('last_seen')
                }
            
            return {'error': f'EmailRep error: {response.status_code}'}
        except Exception as e:
            return {'error': str(e)}
    
    def check_domain_virustotal(self, domain):
        """Check domain on VirusTotal."""
        if not CONFIG['VIRUSTOTAL_API_KEY']:
            return {'status': 'api_key_not_configured'}
        
        try:
            url = f'https://www.virustotal.com/api/v3/domains/{domain}'
            headers = {'x-apikey': CONFIG['VIRUSTOTAL_API_KEY']}
            
            response = self.session.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                stats = data.get('data', {}).get('attributes', {}).get('last_analysis_stats', {})
                
                return {
                    'malicious': stats.get('malicious', 0),
                    'suspicious': stats.get('suspicious', 0),
                    'clean': stats.get('harmless', 0),
                    'undetected': stats.get('undetected', 0)
                }
            
            return {'error': f'VirusTotal error: {response.status_code}'}
        except Exception as e:
            return {'error': str(e)}
    
    def check_gravatar(self, email):
        """Check Gravatar profile."""
        try:
            email_hash = hashlib.md5(email.lower().strip().encode()).hexdigest()
            url = f'https://www.gravatar.com/{email_hash}.json'
            
            response = self.session.get(url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                profile = data.get('entry', [{}])[0] if data.get('entry') else {}
                
                return {
                    'exists': True,
                    'display_name': profile.get('displayName'),
                    'profile_url': profile.get('profileUrl'),
                    'accounts': profile.get('accounts', [])
                }
            return {'exists': False}
        except:
            return {'exists': False}
    
    def check_disposable(self, email):
        """Check if email is disposable."""
        domain = email.split('@')[-1].lower()
        return {
            'is_disposable': domain in self.disposable_domains,
            'domain': domain
        }
    
    def collect(self, email):
        """Collect comprehensive email intelligence."""
        if not self.validate_email(email):
            return {'error': 'Invalid email format'}
        
        domain = email.split('@')[-1]
        
        print("[*] Checking platform registrations (30+ platforms)...")
        platform_results = self.check_all_platforms(email)
        
        print("[*] Checking dark web exposure...")
        darkweb_results = self.check_darkweb_exposure(email)
        
        print("[*] Checking breaches (HIBP)...")
        breach_results = self.breach_check_hibp(email)
        
        print("[*] Checking email reputation...")
        reputation_results = self.emailrep_check(email)
        
        print("[*] Checking domain security...")
        domain_results = self.check_domain_virustotal(domain)
        
        print("[*] Checking Gravatar...")
        gravatar_results = self.check_gravatar(email)
        
        print("[*] Checking disposable email...")
        disposable_results = self.check_disposable(email)
        
        # Organize platforms by type
        platforms_by_type = {}
        for platform, result in platform_results.items():
            platform_type = result.get('type', 'other')
            if platform_type not in platforms_by_type:
                platforms_by_type[platform_type] = []
            platforms_by_type[platform_type].append(result)
        
        # Count registered platforms
        registered_platforms = [p for p, r in platform_results.items() if r.get('registered')]
        
        data = {
            'email': email,
            'domain': domain,
            'timestamp': datetime.now().isoformat(),
            'registration_check': {
                'total_platforms_checked': len(platform_results),
                'platforms_registered': len(registered_platforms),
                'registered_on': registered_platforms,
                'platforms_by_type': platforms_by_type,
                'detailed_results': platform_results
            },
            'dark_web_intelligence': {
                'darkweb_sources_checked': len(darkweb_results),
                'exposure_found': any(r.get('found') for r in darkweb_results.values()),
                'detailed_results': darkweb_results
            },
            'breach_intelligence': breach_results,
            'email_reputation': reputation_results,
            'domain_security': domain_results,
            'gravatar_profile': gravatar_results,
            'disposable_check': disposable_results,
            'risk_summary': {}
        }
        
        print("[*] Generating risk summary...")
        data['risk_summary'] = self.generate_risk_summary(data)
        
        return data
    
    def generate_risk_summary(self, data):
        """Generate risk assessment."""
        risk = {
            'overall_risk': 'LOW',
            'risk_factors': [],
            'recommendations': []
        }
        
        # Check platform registrations
        reg_check = data.get('registration_check', {})
        registered_count = reg_check.get('platforms_registered', 0)
        if registered_count > 20:
            risk['risk_factors'].append(f'Email registered on {registered_count} platforms - large digital footprint')
        elif registered_count > 10:
            risk['risk_factors'].append(f'Email registered on {registered_count} platforms')
        
        # Check dark web exposure
        darkweb = data.get('dark_web_intelligence', {})
        if darkweb.get('exposure_found'):
            risk['overall_risk'] = 'CRITICAL'
            risk['risk_factors'].append('Email found on dark web/deep web sources')
        
        # Check breaches
        breaches = data.get('breach_intelligence', {})
        if isinstance(breaches, dict) and breaches.get('breaches_found', 0) > 0:
            breach_count = breaches['breaches_found']
            if breach_count > 5:
                risk['overall_risk'] = 'CRITICAL'
            elif breach_count > 2:
                risk['overall_risk'] = 'HIGH'
            else:
                risk['overall_risk'] = 'MEDIUM'
            risk['risk_factors'].append(f'Found in {breach_count} data breaches')
        
        # Check reputation
        reputation = data.get('email_reputation', {})
        if reputation.get('credentials_leaked'):
            risk['overall_risk'] = 'CRITICAL'
            risk['risk_factors'].append('Credentials have been leaked')
        if reputation.get('blacklisted'):
            risk['overall_risk'] = 'HIGH'
            risk['risk_factors'].append('Email is blacklisted')
        
        # Recommendations
        if risk['overall_risk'] in ['CRITICAL', 'HIGH']:
            risk['recommendations'].append('Change passwords immediately on all accounts')
            risk['recommendations'].append('Enable Two-Factor Authentication everywhere')
        risk['recommendations'].append('Use unique passwords for each service')
        risk['recommendations'].append('Monitor accounts for suspicious activity')
        
        return risk


def main():
    """Main execution."""
    print("=" * 80)
    print("Br8Trace - Email OSINT Intelligence Framework")
    print("Registration Check | Dark Web Monitoring | Breach Detection")
    print("=" * 80)
    
    email_intel = EmailIntel()
    email = input("\nEnter email address to investigate: ").strip()
    
    if not email_intel.validate_email(email):
        print("[ERROR] Invalid email format")
        return
    
    print(f"\n[*] Target: {email}")
    print("[*] Starting investigation...\n")
    
    results = email_intel.collect(email)
    
    if 'error' in results:
        print(f"[ERROR] {results['error']}")
        return
    
    # Display Platform Registrations
    print("\n" + "=" * 80)
    print("PLATFORM REGISTRATION CHECK")
    print("=" * 80)
    
    reg_check = results.get('registration_check', {})
    registered = reg_check.get('registered_on', [])
    
    if registered:
        print(f"\n[!] EMAIL REGISTERED ON {len(registered)} PLATFORMS:")
        print("-" * 50)
        
        platforms_by_type = reg_check.get('platforms_by_type', {})
        for platform_type, platforms in platforms_by_type.items():
            registered_in_type = [p for p in platforms if p.get('registered')]
            if registered_in_type:
                print(f"\n  [{platform_type.upper()}]")
                for p in registered_in_type:
                    print(f"    ✓ {p['platform']}")
    else:
        print("\n[-] No platform registrations detected")
    
    # Display Dark Web Results
    print("\n" + "=" * 80)
    print("DARK WEB & DEEP WEB INTELLIGENCE")
    print("=" * 80)
    
    darkweb = results.get('dark_web_intelligence', {})
    darkweb_results = darkweb.get('detailed_results', {})
    
    exposure_found = False
    for source, result in darkweb_results.items():
        if result.get('found'):
            exposure_found = True
            print(f"\n[!] EXPOSURE FOUND: {source}")
            print(f"    Type: {result.get('type', 'unknown')}")
        elif result.get('error'):
            print(f"\n[-] {source}: Error - {result['error'][:80]}")
        else:
            print(f"\n[+] {source}: No exposure found")
    
    if not exposure_found:
        print("\n[+] No dark web exposure detected")
    
    # Display Breach Results
    print("\n" + "=" * 80)
    print("DATA BREACH INTELLIGENCE")
    print("=" * 80)
    
    breaches = results.get('breach_intelligence', {})
    if isinstance(breaches, dict) and breaches.get('breaches_found', 0) > 0:
        print(f"\n[!] FOUND IN {breaches['breaches_found']} DATA BREACHES:")
        for breach in breaches.get('breaches', []):
            sensitive = " [SENSITIVE]" if breach.get('is_sensitive') else ""
            print(f"  • {breach.get('name')} ({breach.get('date')}){sensitive}")
    else:
        print("\n[+] No breaches found")
    
    # Display Risk Summary
    print("\n" + "=" * 80)
    print("RISK ASSESSMENT")
    print("=" * 80)
    
    risk = results.get('risk_summary', {})
    risk_level = risk.get('overall_risk', 'LOW')
    
    risk_display = {
        'CRITICAL': '[!!!] CRITICAL RISK',
        'HIGH': '[!!] HIGH RISK',
        'MEDIUM': '[!] MEDIUM RISK',
        'LOW': '[+] LOW RISK'
    }.get(risk_level, f'[{risk_level}]')
    
    print(f"\n{risk_display}")
    
    factors = risk.get('risk_factors', [])
    if factors:
        print("\nRisk Factors:")
        for factor in factors:
            print(f"  • {factor}")
    
    recommendations = risk.get('recommendations', [])
    if recommendations:
        print("\nRecommendations:")
        for rec in recommendations:
            print(f"  • {rec}")
    
    # Save results
    print("\n" + "=" * 80)
    save = input("\nSave results to JSON? (y/n): ").strip().lower()
    if save == 'y':
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_email = email.replace('@', '_at_').replace('.', '_')
        filename = f"email_intel_{safe_email}_{timestamp}.json"
        filepath = os.path.join(CONFIG['REPORTS_DIR'], filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"[+] Saved: {filepath}")
    
    print("\n[*] Investigation complete")


if __name__ == "__main__":
    main()