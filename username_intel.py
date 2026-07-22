# username_intel.py
"""Username reconnaissance across major platforms including dark web."""
import requests
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Clearnet platforms to check - NO DUPLICATES
PLATFORMS = {
    'github': 'https://github.com/{}',
    'x': 'https://x.com/{}',
    'twitter': 'https://twitter.com/{}',
    'reddit': 'https://www.reddit.com/user/{}',
    'instagram': 'https://www.instagram.com/{}',
    'facebook': 'https://www.facebook.com/{}',
    'tiktok': 'https://www.tiktok.com/{}',
    'youtube': 'https://www.youtube.com/@{}',
    'linkedin': 'https://www.linkedin.com/in/{}',
    'pinterest': 'https://www.pinterest.com/{}',
    'tumblr': 'https://{}.tumblr.com',
    'snapchat': 'https://www.snapchat.com/add/{}',
    'telegram': 'https://t.me/{}',
    'discord': 'https://discord.com/users/{}',
    'twitch': 'https://www.twitch.tv/{}',
    'steam': 'https://steamcommunity.com/id/{}',
    'spotify': 'https://open.spotify.com/user/{}',
    'soundcloud': 'https://soundcloud.com/{}',
    'vimeo': 'https://vimeo.com/{}',
    'dribbble': 'https://dribbble.com/{}',
    'behance': 'https://www.behance.net/{}',
    'flickr': 'https://www.flickr.com/people/{}',
    'pastebin': 'https://pastebin.com/u/{}',
    'hackernews': 'https://news.ycombinator.com/user?id={}',
    'keybase': 'https://keybase.io/{}',
    'gravatar': 'https://en.gravatar.com/{}',
    'bitbucket': 'https://bitbucket.org/{}/',
    'gitlab': 'https://gitlab.com/{}',
    'sourceforge': 'https://sourceforge.net/u/{}',
    'replit': 'https://replit.com/@{}',
    'codepen': 'https://codepen.io/{}',
    'devto': 'https://dev.to/{}',
    'hashnode': 'https://hashnode.com/@{}',
    'producthunt': 'https://www.producthunt.com/@{}',
    'angelco': 'https://angel.co/u/{}',
    'wellfound': 'https://wellfound.com/u/{}',
    'indiehackers': 'https://www.indiehackers.com/{}',
    'weworkremotely': 'https://weworkremotely.com/people/{}',
    'nomadlist': 'https://nomadlist.com/{}',
    'meetup': 'https://www.meetup.com/members/{}',
    'eventbrite': 'https://www.eventbrite.com/people/{}',
    'slideshare': 'https://www.slideshare.net/{}',
    'issuu': 'https://issuu.com/{}',
    'scribd': 'https://www.scribd.com/{}',
    'goodreads': 'https://www.goodreads.com/{}',
    'letterboxd': 'https://letterboxd.com/{}',
    'lastfm': 'https://www.last.fm/user/{}',
    'bandcamp': 'https://bandcamp.com/{}',
    'mixcloud': 'https://www.mixcloud.com/{}',
    'patreon': 'https://www.patreon.com/{}',
    'buymeacoffee': 'https://www.buymeacoffee.com/{}',
    'ko-fi': 'https://ko-fi.com/{}',
    'substack': 'https://substack.com/@{}',
    'quora': 'https://www.quora.com/profile/{}',
    'stackoverflow': 'https://stackoverflow.com/users/{}',
    'jsfiddle': 'https://jsfiddle.net/user/{}',
    'codesandbox': 'https://codesandbox.io/u/{}',
    'glitch': 'https://glitch.com/@{}',
    'vercel': 'https://vercel.com/{}',
    'netlify': 'https://app.netlify.com/teams/{}/sites',
    'heroku': 'https://dashboard.heroku.com/apps/{}',
    'dockerhub': 'https://hub.docker.com/u/{}',
    'pypi': 'https://pypi.org/user/{}',
    'npmjs': 'https://www.npmjs.com/~{}',
    'rubygems': 'https://rubygems.org/profiles/{}',
    'cratesio': 'https://crates.io/users/{}',
    'packagist': 'https://packagist.org/packages/{}/',
    'composer': 'https://packagist.org/users/{}',
    'wordpress': 'https://profiles.wordpress.org/{}',
    'joomla': 'https://community.joomla.org/user/{}',
    'drupal': 'https://www.drupal.org/u/{}',
    'magento': 'https://marketplace.magento.com/{}',
    'shopify': 'https://{}.myshopify.com',
    'bigcommerce': 'https://{}.bigcommerce.com',
    'woocommerce': 'https://woocommerce.com/{}',
    'wix': 'https://{}.wixsite.com/mysite',
    'squarespace': 'https://{}.squarespace.com',
    'weebly': 'https://{}.weebly.com',
    'webflow': 'https://webflow.com/design/{}',
    'carrd': 'https://{}.carrd.co',
    'linktree': 'https://linktr.ee/{}',
    'bio': 'https://bio.site/{}',
    'aboutme': 'https://about.me/{}',
    'blogger': 'https://{}.blogspot.com',
    'ghost': 'https://{}.ghost.io',
    'medium': 'https://medium.com/@{}'
}


class UsernameIntel:
    """Username intelligence collection across clearnet and dark web."""
    
    def __init__(self, timeout=10, use_tor=True):
        """
        Initialize username intelligence collector.
        
        Args:
            timeout: Request timeout in seconds
            use_tor: Whether to use Tor for dark web checks
        """
        self.s = requests.Session()
        self.s.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.timeout = timeout
        self.use_tor = use_tor
        
        # Initialize dark web scanner
        try:
            from darkweb_enhanced import DarkWebIntelEnhanced
            self.darkweb = DarkWebIntelEnhanced(use_tor=use_tor)
        except ImportError:
            print("[username] Warning: darkweb_enhanced.py not found. Dark web features disabled.")
            self.darkweb = None
        
        print(f"[username] Initialized with {len(PLATFORMS)} platforms to check")

    def check_profile(self, platform, username):
        """
        Check if a username exists on a specific platform.
        
        Args:
            platform: Platform name
            username: Username to check
            
        Returns:
            dict: Platform check results
        """
        try:
            url = PLATFORMS.get(platform)
            if not url:
                return {'platform': platform, 'exists': False, 'url': None, 'status_code': None, 'error': 'No URL defined'}
            
            url = url.format(username)
            
            # Use HEAD request for efficiency
            r = self.s.head(url, allow_redirects=True, timeout=self.timeout)
            
            # Check if profile exists (200 OK or redirect)
            exists = r.status_code in (200, 301, 302, 307, 308)
            
            # Special handling for some platforms
            if platform == 'github' and r.status_code == 404:
                exists = False
            elif platform == 'twitter' and r.status_code == 404:
                exists = False
            elif platform == 'instagram' and r.status_code == 404:
                exists = False
            
            return {
                'platform': platform,
                'exists': exists,
                'url': r.url,
                'status_code': r.status_code,
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            }
            
        except requests.exceptions.Timeout:
            return {
                'platform': platform,
                'exists': False,
                'url': url,
                'status_code': None,
                'error': 'Timeout',
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            }
        except requests.exceptions.ConnectionError:
            return {
                'platform': platform,
                'exists': False,
                'url': url,
                'status_code': None,
                'error': 'Connection Error',
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            }
        except Exception as e:
            return {
                'platform': platform,
                'exists': False,
                'url': url,
                'status_code': None,
                'error': str(e)[:100],
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            }

    def check_profiles_batch(self, username, platforms=None):
        """
        Check multiple platforms in parallel.
        
        Args:
            username: Username to check
            platforms: List of platforms to check (None for all)
            
        Returns:
            list: Results from all platform checks
        """
        if platforms is None:
            platforms = list(PLATFORMS.keys())
        
        results = []
        
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = {
                executor.submit(self.check_profile, platform, username): platform 
                for platform in platforms
            }
            
            for future in as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    platform = futures[future]
                    results.append({
                        'platform': platform,
                        'exists': False,
                        'error': str(e)[:100],
                        'timestamp': datetime.utcnow().isoformat() + 'Z'
                    })
        
        return results

    def collect(self, username):
        """
        Main collection method for username intelligence.
        
        Args:
            username: Username to investigate
            
        Returns:
            list: Complete intelligence results including dark web
        """
        print(f"[username] Starting intelligence collection for: {username}")
        results = []
        
        # Track start time
        start_time = datetime.utcnow().isoformat() + 'Z'
        
        # 1. Check clearnet platforms
        print(f"[username] Checking {len(PLATFORMS)} clearnet platforms...")
        clearnet_results = self.check_profiles_batch(username)
        results.extend(clearnet_results)
        
        # Count found profiles
        found_count = sum(1 for r in clearnet_results if r.get('exists', False))
        print(f"[username] Found {found_count} profiles on clearnet")
        
        # 2. Check dark web presence
        if self.darkweb:
            print("[username] Checking dark web presence...")
            try:
                darkweb_results = self.darkweb.collect(username)
                results.extend(darkweb_results)
                print(f"[username] Dark web check complete")
            except Exception as e:
                print(f"[username] Dark web check error: {e}")
                results.append({
                    'type': 'darkweb_error',
                    'error': str(e),
                    'timestamp': datetime.utcnow().isoformat() + 'Z'
                })
        else:
            print("[username] Dark web features disabled")
            results.append({
                'type': 'darkweb_status',
                'status': 'disabled',
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            })
        
        # 3. Add summary
        results.append({
            'type': 'username_summary',
            'username': username,
            'clearnet_platforms_checked': len(PLATFORMS),
            'clearnet_profiles_found': found_count,
            'darkweb_checked': self.darkweb is not None,
            'start_time': start_time,
            'end_time': datetime.utcnow().isoformat() + 'Z',
            'total_results': len(results)
        })
        
        print(f"[username] Collection complete. Total results: {len(results)}")
        return results

    def get_found_profiles(self, username):
        """
        Get only the found profiles for a username.
        
        Args:
            username: Username to check
            
        Returns:
            list: Only profiles that exist
        """
        results = self.collect(username)
        return [r for r in results if r.get('exists', False)]

    def get_summary(self, username):
        """
        Get a summary of username presence.
        
        Args:
            username: Username to check
            
        Returns:
            dict: Summary of findings
        """
        results = self.collect(username)
        found = [r for r in results if r.get('exists', False)]
        
        return {
            'username': username,
            'total_platforms_checked': len(PLATFORMS),
            'profiles_found': len(found),
            'found_platforms': [r['platform'] for r in found if 'platform' in r],
            'found_urls': [r['url'] for r in found if 'url' in r],
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }


# Quick test function
if __name__ == '__main__':
    import sys
    
    # Test with a sample username
    test_username = sys.argv[1] if len(sys.argv) > 1 else 'github'
    
    print(f"\nTesting username intelligence for: {test_username}")
    print("=" * 60)
    
    intel = UsernameIntel()
    results = intel.collect(test_username)
    
    # Print found profiles
    print("\n[+] Found Profiles:")
    found = [r for r in results if r.get('exists', False)]
    for r in found:
        if 'platform' in r:
            print(f"  ✓ {r['platform']}: {r['url']}")
    
    print(f"\n[+] Total found: {len(found)}/{len(PLATFORMS)}")