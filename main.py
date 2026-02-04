import argparse
import sys
from pathlib import Path
import logging
from logging_setup import setup_logging 
from config import load_config
from runner import run_health_checks, print_summary

def main():
    setup_logging()
    
    parser = argparse.ArgumentParser(description="DevOps Utility: system guard.")
    parser.add_argument("--config", default="config.json", help="Path to config file")
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("check", help="Health check")
    
    args = parser.parse_args()
    
    if args.command == "check":
        config = load_config(args.config)
        logging.info("--- Starting Health Check ---")
        
        full_report = run_health_checks(config)
        
        success = print_summary(full_report)
        
        if not success:
            sys.exit(1)
    else:
        parser.print_help()
        
    
if __name__ == "__main__":
    
    main()
