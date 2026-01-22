#!/usr/bin/env python3
"""
Professional OSINT Username Checker
Async username enumeration across multiple platforms
"""

import asyncio
import httpx
import json
import argparse
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.panel import Panel
import random

console = Console()

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
]

class UsernameChecker:
    def __init__(self, sites_file: str = "sites.json", timeout: int = 10, rate_limit: float = 0.5):
        self.sites_file = Path(sites_file)
        self.timeout = timeout
        self.rate_limit = rate_limit
        self.sites: List[Dict] = []
        self.results: Dict[str, List[Dict]] = {"found": [], "not_found": [], "errors": []}
        
    def load_sites(self) -> bool:
        """Load site configurations from JSON file"""
        try:
            if not self.sites_file.exists():
                console.print(f"[red]Error: {self.sites_file} not found![/red]")
                return False
            
            with open(self.sites_file, 'r') as f:
                data = json.load(f)
                self.sites = data.get('sites', [])
            
            console.print(f"[green]✓[/green] Loaded {len(self.sites)} sites from {self.sites_file}")
            return True
        except json.JSONDecodeError as e:
            console.print(f"[red]Error parsing JSON: {e}[/red]")
            return False
        except Exception as e:
            console.print(f"[red]Error loading sites: {e}[/red]")
            return False

    async def check_username(self, site: Dict, username: str, client: httpx.AsyncClient) -> Dict:
        """Check if username exists on a specific site"""
        site_name = site['name']
        url = site['url_template'].format(username=username)
        detection_type = site['detection_type']
        
        result = {
            'site': site_name,
            'url': url,
            'status': 'unknown',
            'error': None
        }
        
        try:
            # Random User-Agent rotation
            headers = {'User-Agent': random.choice(USER_AGENTS)}
            
            # Make async request
            response = await client.get(url, headers=headers, timeout=self.timeout, follow_redirects=True)
            
            # Detection logic
            if detection_type == "status_code":
                # Simple status code check (200 = exists, 404 = not found)
                if response.status_code == 200:
                    result['status'] = 'found'
                elif response.status_code == 404:
                    result['status'] = 'not_found'
                else:
                    result['status'] = 'unknown'
                    result['error'] = f"Unexpected status: {response.status_code}"
            
            elif detection_type == "message_body":
                # Advanced: Check for error message in body (handles "soft 404s")
                error_message = site.get('error_message', '')
                
                if response.status_code == 200:
                    # Check if error message is in the response body
                    if error_message and error_message.lower() in response.text.lower():
                        result['status'] = 'not_found'
                    else:
                        result['status'] = 'found'
                elif response.status_code == 404:
                    result['status'] = 'not_found'
                else:
                    result['status'] = 'unknown'
                    result['error'] = f"Status: {response.status_code}"
            
            # Rate limiting
            await asyncio.sleep(self.rate_limit)
            
        except httpx.TimeoutException:
            result['status'] = 'error'
            result['error'] = 'Timeout'
        except httpx.ConnectError:
            result['status'] = 'error'
            result['error'] = 'Connection failed'
        except httpx.UnsupportedProtocol:
            result['status'] = 'error'
            result['error'] = 'SSL/TLS error'
        except Exception as e:
            result['status'] = 'error'
            result['error'] = str(e)
        
        return result

    async def scan_username(self, username: str) -> Dict[str, List[Dict]]:
        """Scan username across all loaded sites"""
        console.print(Panel.fit(
            f"[bold cyan]Scanning username:[/bold cyan] [yellow]{username}[/yellow]",
            border_style="cyan"
        ))
        
        # Create async HTTP client with custom settings
        async with httpx.AsyncClient(
            verify=True,
            http2=True,
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=100)
        ) as client:
            
            # Create progress bar
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                console=console
            ) as progress:
                
                task = progress.add_task("[cyan]Checking sites...", total=len(self.sites))
                
                # Create tasks for all sites
                tasks = [self.check_username(site, username, client) for site in self.sites]
                
                # Execute concurrently with progress updates
                for coro in asyncio.as_completed(tasks):
                    result = await coro
                    
                    # Categorize results
                    if result['status'] == 'found':
                        self.results['found'].append(result)
                    elif result['status'] == 'not_found':
                        self.results['not_found'].append(result)
                    else:
                        self.results['errors'].append(result)
                    
                    progress.update(task, advance=1)
        
        return self.results

    def display_results(self, username: str):
        """Display results in a beautiful table format"""
        console.print("\n")
        
        # Found accounts
        if self.results['found']:
            table = Table(title=f"[bold green]✓ Found ({len(self.results['found'])} platforms)[/bold green]", 
                         show_header=True, header_style="bold green")
            table.add_column("Platform", style="cyan", width=20)
            table.add_column("URL", style="blue")
            
            for result in self.results['found']:
                table.add_row(result['site'], result['url'])
            
            console.print(table)
        else:
            console.print("[yellow]No accounts found.[/yellow]")
        
        # Errors (optional display)
        if self.results['errors']:
            console.print(f"\n[dim]⚠ {len(self.results['errors'])} errors/timeouts occurred[/dim]")

    def export_results(self, username: str, format: str = "txt"):
        """Export found results to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if format == "txt":
            filename = f"{username}_{timestamp}.txt"
            with open(filename, 'w') as f:
                f.write(f"Username Check Results: {username}\n")
                f.write(f"Scan Date: {datetime.now()}\n")
                f.write(f"{'='*60}\n\n")
                
                if self.results['found']:
                    f.write(f"FOUND ON {len(self.results['found'])} PLATFORMS:\n\n")
                    for result in self.results['found']:
                        f.write(f"  • {result['site']}\n")
                        f.write(f"    {result['url']}\n\n")
                else:
                    f.write("No accounts found.\n")
            
            console.print(f"[green]✓[/green] Results exported to [cyan]{filename}[/cyan]")
        
        elif format == "json":
            filename = f"{username}_{timestamp}.json"
            export_data = {
                "username": username,
                "scan_date": datetime.now().isoformat(),
                "summary": {
                    "found": len(self.results['found']),
                    "not_found": len(self.results['not_found']),
                    "errors": len(self.results['errors'])
                },
                "results": self.results['found']
            }
            
            with open(filename, 'w') as f:
                json.dump(export_data, f, indent=2)
            
            console.print(f"[green]✓[/green] Results exported to [cyan]{filename}[/cyan]")

async def main():
    parser = argparse.ArgumentParser(
        description="Professional OSINT Username Checker",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python username_checker.py johndoe
  python username_checker.py johndoe --export json
  python username_checker.py johndoe --timeout 15 --rate-limit 1.0
        """
    )
    
    parser.add_argument('username', help='Username to search for')
    parser.add_argument('--sites', default='sites.json', help='Path to sites JSON file (default: sites.json)')
    parser.add_argument('--timeout', type=int, default=10, help='Request timeout in seconds (default: 10)')
    parser.add_argument('--rate-limit', type=float, default=0.5, help='Delay between requests in seconds (default: 0.5)')
    parser.add_argument('--export', choices=['txt', 'json'], help='Export results to file')
    parser.add_argument('--no-color', action='store_true', help='Disable colored output')
    
    args = parser.parse_args()
    
    # ASCII Banner
    console.print("""
[cyan]╔═══════════════════════════════════════════════╗
║   [bold]OSINT Username Checker v1.0[/bold]             ║
║   Professional Username Enumeration Tool      ║
╚═══════════════════════════════════════════════╝[/cyan]
    """)
    
    # Initialize checker
    checker = UsernameChecker(
        sites_file=args.sites,
        timeout=args.timeout,
        rate_limit=args.rate_limit
    )
    
    # Load sites
    if not checker.load_sites():
        return
    
    # Scan username
    await checker.scan_username(args.username)
    
    # Display results
    checker.display_results(args.username)
    
    # Export if requested
    if args.export:
        checker.export_results(args.username, args.export)
    
    # Summary
    console.print(f"\n[bold]Scan Complete![/bold]")
    console.print(f"  Found: [green]{len(checker.results['found'])}[/green]")
    console.print(f"  Not Found: [dim]{len(checker.results['not_found'])}[/dim]")
    console.print(f"  Errors: [yellow]{len(checker.results['errors'])}[/yellow]\n")

if __name__ == "__main__":
    asyncio.run(main())