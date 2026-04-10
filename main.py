import argparse
import json
import sys
from pathlib import Path
import logging
from logging_setup import setup_logging 
from config import load_config
from runner import run_health_checks, print_summary
from report_schema import build_report_document, get_exit_code_for_report

def emit_json_report(full_report, output_path=None, quiet=False):
    """Emit machine-readable report according to CLI output options."""
    report_document = build_report_document(full_report)
    payload = json.dumps(report_document, ensure_ascii=False)

    if output_path:
        output_file = Path(output_path)
        output_file.write_text(payload + "\n", encoding="utf-8")
        logging.info(f"JSON report saved to {output_file}")
        return

    if quiet:
        logging.info("JSON stdout output is disabled by --quiet")
        return

    sys.stdout.write(payload + "\n")

def main():
    setup_logging()
    
    parser = argparse.ArgumentParser(description="DevOps Utility: system guard.")
    parser.add_argument("--config", default="config.json", help="Path to config file")
    subparsers = parser.add_subparsers(dest="command")
    check_parser = subparsers.add_parser("check", help="Health check")
    check_parser.add_argument(
        "--output",
        help="Write JSON report to file (suppresses JSON in stdout)",
    )
    check_parser.add_argument(
        "--quiet",
        action="store_true",
        help="Do not print JSON report to stdout",
    )
    
    args = parser.parse_args()
    
    if args.command == "check":
        config = load_config(args.config)
        logging.info("--- Starting Health Check ---")
        
        full_report = run_health_checks(config)
        
        print_summary(full_report)
        
        emit_json_report(full_report, output_path=args.output, quiet=args.quiet)
        
        sys.exit(get_exit_code_for_report(full_report))
    else:
        parser.print_help()
        
    
if __name__ == "__main__":
    
    main()
