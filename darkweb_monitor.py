#!/usr/bin/env python3

import argparse
import yaml
import logging
import sys
from datetime import datetime
import socks
import socket
from rich.console import Console
from rich.logging import RichHandler
from stem import Signal
from stem.control import Controller
import time
import requests
import os

class DarkWebMonitor:
    def __init__(self, config_path="config.yml"):
        """Initialize the DarkWeb Monitor with configuration"""
        self.console = Console()
        self.setup_logging()
        self.load_config(config_path)
        self.setup_tor()

    def setup_logging(self):
        """Configure rich logging"""
        logging.basicConfig(
            level=logging.INFO,
            format="%(message)s",
            handlers=[RichHandler(rich_tracebacks=True)]
        )
        self.logger = logging.getLogger("darkweb_monitor")

    def load_config(self, config_path):
        """Load configuration from YAML file"""
        try:
            with open(config_path, 'r') as file:
                self.config = yaml.safe_load(file)
            self.logger.info("[green]Configuration loaded successfully[/green]")
        except Exception as e:
            self.logger.error(f"[red]Error loading configuration: {e}[/red]")
            sys.exit(1)

    def setup_tor(self):
        """Setup Tor connection"""
        if self.config['tor']['enabled']:
            try:
                socks.set_default_proxy(
                    socks.SOCKS5, 
                    "127.0.0.1", 
                    self.config['tor']['port']
                )
                socket.socket = socks.socksocket
                self.session = requests.Session()
                self.session.headers['User-Agent'] = self.config['network']['user_agent']
                
                # Verify Tor connection
                response = self.session.get('https://check.torproject.org/api/ip')
                if response.json().get('IsTor', False):
                    self.logger.info("[bold green]Successfully connected to Tor network[/bold green]")
                else:
                    raise Exception("Not connected to Tor")
                    
            except Exception as e:
                self.logger.error(f"[bold red]Failed to connect to Tor: {e}[/bold red]")
                sys.exit(1)

    def renew_tor_ip(self):
        """Renew Tor IP address"""
        try:
            with Controller.from_port(port=self.config['tor']['control_port']) as controller:
                controller.authenticate()
                controller.signal(Signal.NEWNYM)
                time.sleep(self.config['safety']['request_delay'])
                self.logger.info("[yellow]Tor IP renewed[/yellow]")
        except Exception as e:
            self.logger.error(f"Failed to renew Tor IP: {e}")

    def safe_request(self, url, method='get', **kwargs):
        """Make a safe request with retries and error handling"""
        retries = self.config['network']['max_retries']
        while retries > 0:
            try:
                response = getattr(self.session, method)(
                    url, 
                    timeout=self.config['network']['timeout'],
                    **kwargs
                )
                response.raise_for_status()
                return response
            except Exception as e:
                retries -= 1
                if retries == 0:
                    self.logger.error(f"[red]Request failed: {e}[/red]")
                    return None
                self.logger.warning(f"Request failed, retrying... ({retries} attempts left)")
                self.renew_tor_ip()
                time.sleep(self.config['safety']['request_delay'])

    def generate_report(self, keyword, results):
        """Generate a formatted report of findings"""
        report = f"""
DarkWeb Monitor Report
=====================
Target Keyword: {keyword}
Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
=====================\n\n"""

        if not results:
            report += "No results found.\n"
        else:
            for source, items in results.items():
                if items:
                    report += f"\n{source}:\n"
                    for item in items:
                        report += f"- {item}\n"

        return report

    def scan(self, keyword):
        """Main scanning function"""
        self.logger.info(f"[bold blue]Starting scan for keyword: {keyword}[/bold blue]")
        
        results = {
            'Dark Web Forums': [],
            'Dark Web Markets': [],
            'Paste Sites': []
        }

        # Basic implementation - you would expand this with actual dark web sources
        test_url = "http://example.onion"  # Example onion URL
        response = self.safe_request(test_url)
        
        if response:
            # Process response here
            results['Dark Web Forums'].append("Test result")
        
        return self.generate_report(keyword, results)

def main():
    parser = argparse.ArgumentParser(description='Dark Web Monitor - OSINT Tool')
    parser.add_argument('keyword', help='Keyword to search for')
    parser.add_argument('--output', '-o', help='Output file for results')
    parser.add_argument('--config', '-c', default='config.yml', help='Path to configuration file')
    args = parser.parse_args()

    # Create output directory if it doesn't exist
    if args.output:
        os.makedirs(os.path.dirname(args.output) if os.path.dirname(args.output) else '.', exist_ok=True)

    # Initialize and run the monitor
    monitor = DarkWebMonitor(args.config)
    report = monitor.scan(args.keyword)
    
    if args.output:
        with open(args.output, 'w') as f:
            f.write(report)
        monitor.logger.info(f"[bold green]Report written to {args.output}[/bold green]")
    else:
        print(report)

if __name__ == "__main__":
    main()
