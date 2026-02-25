#!/usr/bin/env python3
"""
Export tickets and KB articles from Zoho Desk via API.

This automates the manual CSV export process. Run periodically to keep
the knowledge base fresh with the latest resolved tickets.

Usage:
    python export_zoho.py --tickets              # Export resolved tickets
    python export_zoho.py --kb                   # Export KB articles
    python export_zoho.py --all                  # Export everything
    python export_zoho.py --tickets --days 30    # Last 30 days only

Prerequisites:
    1. Create a Zoho API OAuth token with Desk.tickets.READ and Desk.articles.READ scopes
    2. Add your org ID and token to .env

Zoho Desk API docs: https://desk.zoho.com/DeskAPIDocument
"""

import argparse
import csv
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

ZOHO_ORG_ID = os.getenv("ZOHO_DESK_ORG_ID")
ZOHO_TOKEN = os.getenv("ZOHO_DESK_API_TOKEN")
ZOHO_BASE_URL = "https://desk.zoho.com/api/v1"

OUTPUT_DIR = Path("data/zoho")


def zoho_headers():
    return {
        "Authorization": f"Zoho-oauthtoken {ZOHO_TOKEN}",
        "orgId": ZOHO_ORG_ID,
        "Content-Type": "application/json",
    }


def export_tickets(days: int = None, limit: int = 500):
    """
    Export resolved/closed tickets from Zoho Desk.

    Outputs a CSV file ready for the ingestion pipeline.
    """
    if not ZOHO_ORG_ID or not ZOHO_TOKEN:
        print("ERROR: ZOHO_DESK_ORG_ID and ZOHO_DESK_API_TOKEN must be set in .env")
        print("See: https://desk.zoho.com/DeskAPIDocument#Authentication")
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_file = OUTPUT_DIR / f"tickets_export_{datetime.now().strftime('%Y%m%d')}.csv"

    print(f"Exporting resolved tickets from Zoho Desk...")

    all_tickets = []
    offset = 0
    page_limit = 100  # Zoho max per page

    # Build date filter
    params = {
        "status": "Closed",
        "limit": page_limit,
        "sortBy": "modifiedTime",
    }

    if days:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        params["modifiedTimeRange"] = f"{cutoff.strftime('%Y-%m-%dT%H:%M:%S')},{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S')}"

    while len(all_tickets) < limit:
        params["from"] = offset
        try:
            resp = requests.get(
                f"{ZOHO_BASE_URL}/tickets",
                headers=zoho_headers(),
                params=params,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.HTTPError as e:
            print(f"API Error: {e}")
            print(f"Response: {resp.text}")
            break
        except Exception as e:
            print(f"Error: {e}")
            break

        tickets = data.get("data", [])
        if not tickets:
            break

        # For each ticket, fetch the thread/comments for the resolution
        for ticket in tickets:
            ticket_id = ticket.get("id")
            subject = ticket.get("subject", "")
            description = ticket.get("description", "")
            status = ticket.get("status", "")
            category = ticket.get("category", "")

            # Get resolution from ticket threads
            resolution = _get_ticket_resolution(ticket_id)

            all_tickets.append({
                "Subject": subject,
                "Description": _strip_html(description),
                "Resolution": _strip_html(resolution),
                "Status": status,
                "Category": category,
            })

        offset += page_limit
        print(f"  Fetched {len(all_tickets)} tickets...")

        if len(tickets) < page_limit:
            break

    # Write CSV
    if all_tickets:
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=["Subject", "Description", "Resolution", "Status", "Category"])
            writer.writeheader()
            writer.writerows(all_tickets)
        print(f"\nExported {len(all_tickets)} tickets to {output_file}")
    else:
        print("No tickets found matching criteria.")

    return output_file


def _get_ticket_resolution(ticket_id: str) -> str:
    """Fetch the latest agent response from a ticket's thread."""
    try:
        resp = requests.get(
            f"{ZOHO_BASE_URL}/tickets/{ticket_id}/threads",
            headers=zoho_headers(),
            params={"limit": 5},
        )
        resp.raise_for_status()
        threads = resp.json().get("data", [])

        # Find the last response from an agent (not the customer)
        for thread in threads:
            if thread.get("direction") == "out":  # Agent response
                return thread.get("content", "")

    except Exception:
        pass  # Silently skip - some tickets may not have threads

    return ""


def export_kb_articles(limit: int = 500):
    """Export Knowledge Base articles from Zoho Desk."""
    if not ZOHO_ORG_ID or not ZOHO_TOKEN:
        print("ERROR: ZOHO_DESK_ORG_ID and ZOHO_DESK_API_TOKEN must be set in .env")
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_file = OUTPUT_DIR / f"kb_articles_export_{datetime.now().strftime('%Y%m%d')}.csv"

    print("Exporting KB articles from Zoho Desk...")

    all_articles = []
    offset = 0
    page_limit = 50

    while len(all_articles) < limit:
        try:
            resp = requests.get(
                f"{ZOHO_BASE_URL}/articles",
                headers=zoho_headers(),
                params={"from": offset, "limit": page_limit, "status": "Published"},
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"Error: {e}")
            break

        articles = data.get("data", [])
        if not articles:
            break

        for article in articles:
            all_articles.append({
                "Title": article.get("title", ""),
                "Content": _strip_html(article.get("answer", "")),
                "Category": article.get("category", {}).get("name", ""),
            })

        offset += page_limit
        print(f"  Fetched {len(all_articles)} articles...")

        if len(articles) < page_limit:
            break

    if all_articles:
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=["Title", "Content", "Category"])
            writer.writeheader()
            writer.writerows(all_articles)
        print(f"\nExported {len(all_articles)} articles to {output_file}")
    else:
        print("No KB articles found.")

    return output_file


def _strip_html(text: str) -> str:
    """Quick HTML stripping."""
    import re
    if not text:
        return ""
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<p[^>]*>', '\n\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'&nbsp;', ' ', text)
    return text.strip()


def main():
    parser = argparse.ArgumentParser(description="Export data from Zoho Desk for ingestion.")
    parser.add_argument("--tickets", action="store_true", help="Export resolved tickets")
    parser.add_argument("--kb", action="store_true", help="Export KB articles")
    parser.add_argument("--all", action="store_true", help="Export everything")
    parser.add_argument("--days", type=int, help="Only export tickets from last N days")
    parser.add_argument("--limit", type=int, default=500, help="Max items to export")

    args = parser.parse_args()

    if not any([args.tickets, args.kb, args.all]):
        parser.print_help()
        return

    if args.all or args.tickets:
        export_tickets(days=args.days, limit=args.limit)

    if args.all or args.kb:
        export_kb_articles(limit=args.limit)


if __name__ == "__main__":
    main()
