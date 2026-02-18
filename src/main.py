"""Main orchestrator for BCRA Weekly Monitor."""

import argparse
import sys
import webbrowser
import json
from datetime import datetime
from pathlib import Path

from .config import DATA_DIR
from .excel_reader import get_summary_table
from .charts import generate_all_charts
from .scraper import scrape_all, save_state, mark_as_processed
from .digest import build_digest, render_digest, save_digest_preview
from .emailer import send_digest_email, send_error_email
from .summarizer import generate_all_summaries


def run_digest(
    dry_run: bool = False,
    preview: bool = False,
    force: bool = False,
    days: int = 7,
) -> bool:
    """
    Run the complete digest workflow.

    Args:
        dry_run: Generate digest without sending email
        preview: Open digest in browser
        force: Ignore state file, process all content
        days: Number of days to look back for news

    Returns:
        True if successful, False otherwise
    """
    try:
        print("=" * 60)
        print("BCRA Weekly Monitor")
        print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)

        # Step 1: Read Excel data
        print("\n[1/6] Reading Excel data...")
        try:
            summary = get_summary_table()
            print("  Data loaded successfully")
        except Exception as e:
            print(f"  Error reading Excel: {e}")
            raise

        # Step 2: Generate charts
        print("\n[2/6] Generating charts...")
        try:
            charts = generate_all_charts()
            print(f"  Generated {len(charts)} charts")
        except Exception as e:
            print(f"  Error generating charts: {e}")
            raise

        # Step 3: Scrape web content
        print("\n[3/6] Scraping web content...")
        try:
            scrape_results = scrape_all(days=days, ignore_state=force)
            news = scrape_results["news"]
            reports = scrape_results["reports"]
            policy = scrape_results["policy"]
            state = scrape_results["state"]

            print(f"  News items: {len(news)}")
            print(f"  Reports: {len(reports)}")
            print(f"  Policy items: {len(policy)}")
        except Exception as e:
            print(f"  Error scraping: {e}")
            # Continue with empty content
            news, reports, policy, state = [], [], [], {}

        # Step 4: Generate AI summaries
        print("\n[4/6] Generating AI summaries...")
        try:
            summaries_dict = generate_all_summaries(reports, policy)
            reports_with_summary = len(summaries_dict.get("reports", {}))
            policy_with_summary = len(summaries_dict.get("policy", {}))
            print(f"  Reports with summaries: {reports_with_summary}/{len(reports)}")
            print(f"  Policy with summaries: {policy_with_summary}/{len(policy)}")
        except Exception as e:
            print(f"  Error generating summaries: {e}")
            summaries_dict = {"reports": {}, "policy": {}, "news": {}}

        # Step 5: Build and render digest
        print("\n[5/6] Building digest...")
        try:
            content = build_digest(
                news_items=news,
                report_items=reports,
                policy_items=policy,
                summaries=summaries_dict,
            )
            html = render_digest(content)
            print("  Digest compiled successfully")
        except Exception as e:
            print(f"  Error building digest: {e}")
            raise

        # Step 6: Send or preview
        if preview or dry_run:
            print("\n[6/6] Saving preview...")
            preview_path = save_digest_preview(html)
            print(f"  Preview saved to: {preview_path}")

            if preview:
                webbrowser.open(f"file:///{preview_path}")
                print("  Opened in browser")

            if dry_run:
                print("\n  DRY RUN - Email not sent")
        else:
            print("\n[6/6] Sending email...")
            success = send_digest_email(
                html_content=html,
                charts=content.charts,
                date_range=content.date_range,
            )

            if success:
                print("  Email sent successfully!")

                # Update state
                all_items = news + reports + policy
                state = mark_as_processed(all_items, state)
                save_state(state)
                print("  State updated")
            else:
                print("  Failed to send email")
                return False

        print("\n" + "=" * 60)
        print("Digest completed successfully!")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"\nFATAL ERROR: {e}")

        # Try to send error email
        if not dry_run:
            try:
                send_error_email(str(e))
            except:
                pass

        return False


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="BCRA Weekly Monitor - Generate and send weekly digest"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate digest without sending email"
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Open digest in browser"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Ignore state file, process all content"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Number of days to look back for news (default: 7)"
    )

    args = parser.parse_args()

    success = run_digest(
        dry_run=args.dry_run,
        preview=args.preview,
        force=args.force,
        days=args.days,
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
