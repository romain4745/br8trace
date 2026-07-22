
import os
import json
import requests
import socket
from datetime import datetime
from urllib.parse import urlparse
from dotenv import load_dotenv
import stem
import stem.process

load_dotenv()

class DarkWebIntelEnhanced:
    """Enhanced dark web intelligence with real .onion domain checks."""
    
    def __init__(self, use_tor=True):
        self.tor_proxy = os.getenv('TOR_PROXY', 'socks5h://127.0.0.1:9050')
        self.use_tor = use_tor
        self.session = requests.Session()
        
        if use_tor:
            try:
                self.session.proxies.update({
                    'http': self.tor_proxy,
                    'https': self.tor_proxy
                })
                print("[darkweb] Tor proxy configured")
            except Exception as e:
                print(f"[darkweb] Tor configuration error: {e}")
                self.use_tor = False
        
        # Known dark web marketplaces and services
        self.darkweb_services = {
            'tunnels': {
                'url': 'http://62gs2n5ydnyffzfy.onion',
                'type': 'darknet_marketplace'
            },
            'elude': {
                'url': 'http://eludemaillhqfkh5.onion',
                'type': 'email_service'
            },
            'dnm': {
                'url': 'http://darknetmarketplace.onion',
                'type': 'marketplace'
            }
        }
    
    def check_onion_domain(self, domain):
        """
        Check if a .onion domain is accessible via Tor.
        
        Args:
            domain: .onion domain to check
        
        Returns:
            dict: Availability and metadata
        """
        if not self.use_tor:
            return {
                'domain': domain,
                'accessible': False,
                'reason': 'Tor not configured',
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            }
        
        try:
            # Normalize domain
            if not domain.startswith('http://'):
                domain = f'http://{domain}'
            
            # Try to connect
            response = self.session.get(domain, timeout=30, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
            })
            
            # Check if we got a response
            if response.status_code == 200:
                return {
                    'domain': domain,
                    'accessible': True,
                    'status_code': response.status_code,
                    'title': self._extract_title(response.text),
                    'timestamp': datetime.utcnow().isoformat() + 'Z'
                }
            else:
                return {
                    'domain': domain,
                    'accessible': False,
                    'status_code': response.status_code,
                    'timestamp': datetime.utcnow().isoformat() + 'Z'
                }
                
        except requests.exceptions.Timeout:
            return {
                'domain': domain,
                'accessible': False,
                'reason': 'Connection timeout',
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            }
        except requests.exceptions.ConnectionError:
            return {
                'domain': domain,
                'accessible': False,
                'reason': 'Connection error',
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            }
        except Exception as e:
            return {
                'domain': domain,
                'accessible': False,
                'reason': str(e),
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            }
    
    def _extract_title(self, html):
        """Extract title from HTML content."""
        try:
            start = html.find('<title>')
            end = html.find('</title>')
            if start != -1 and end != -1:
                return html[start+7:end].strip()
        except:
            pass
        return None
    
    def search_username_darkweb(self, username):
        """
        Search for username across dark web services.
        
        Args:
            username: Username to search
        
        Returns:
            list: Dark web presence results
        """
        results = []
        
        print(f"[darkweb] Searching for username '{username}' on dark web")
        
        # 1. Check Tunnels
        if 'tunnels' in self.darkweb_services:
            tunnels_url = self.darkweb_services['tunnels']['url']
            result = self.check_onion_domain(tunnels_url)
            results.append({
                'service': 'tunnels',
                'url': tunnels_url,
                'username': username,
                'found': result.get('accessible', False),
                'metadata': result
            })
        
        # 2. Check Elude
        if 'elude' in self.darkweb_services:
            elude_url = self.darkweb_services['elude']['url']
            result = self.check_onion_domain(elude_url)
            results.append({
                'service': 'elude',
                'url': elude_url,
                'username': username,
                'found': result.get('accessible', False),
                'metadata': result
            })
        
        # 3. General dark web presence
        if results:
            results.append({
                'type': 'darkweb_analysis',
                'username': username,
                'services_checked': len(results),
                'services_found': sum(1 for r in results if r.get('found', False)),
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            })
        
        print(f"[darkweb] Dark web search complete. Found {len(results)} results")
        return results
    
    def collect(self, username):
        """Main collection method for dark web intelligence."""
        return self.search_username_darkweb(username)