"""
OSINT Harvester — lightweight email, subdomain, and employee discovery.
Uses public data sources to find company digital footprint without
heavy dependencies (replaces theHarvester's core functionality).

Sources used:
- DNS enumeration (subdomain brute-forcing with common prefixes)
- CRT.sh (Certificate Transparency logs — real subdomain discovery)
- Email pattern detection from scraped pages
- Hunter.io-style email format guessing
"""

import asyncio
import httpx
import re
import json
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Common subdomains to check
_SUBDOMAIN_PREFIXES = [
    "www", "mail", "email", "webmail", "smtp", "pop", "imap",
    "blog", "dev", "staging", "beta", "alpha", "test", "demo",
    "api", "app", "dashboard", "admin", "portal", "cdn",
    "docs", "help", "support", "status", "careers", "jobs",
    "shop", "store", "payments", "billing", "investor", "ir",
    "press", "news", "media", "events", "community", "forum",
    "git", "gitlab", "github", "jira", "confluence", "slack",
    "vpn", "remote", "internal", "intranet", "sso", "auth",
    "m", "mobile", "analytics", "metrics", "grafana", "monitor",
    "ai", "ml", "data", "platform", "cloud", "infra",
]

# Email pattern heuristic
_EMAIL_PATTERN = re.compile(
    r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b'
)


class OSINTHarvesterService:
    """Lightweight OSINT: discover emails, subdomains, and employee info."""

    async def harvest(self, company_name: str, domain: str = "") -> dict:
        """
        Run all OSINT modules in parallel.
        Returns {emails[], subdomains[], employees[], domain_info{}}
        """
        result = {
            "emails": [],
            "subdomains": [],
            "employees": [],
            "domain_info": {},
            "raw_content": "",
        }

        if not domain:
            domain = await self._guess_domain(company_name)
        if not domain:
            logger.info(f"[OSINT] Could not determine domain for '{company_name}'")
            return result

        result["domain_info"]["domain"] = domain
        logger.info(f"[OSINT] Scanning domain: {domain}")

        # Run all OSINT modules in parallel
        crt_task = self._crt_sh_subdomains(domain)
        dns_task = self._dns_subdomain_check(domain)
        email_task = self._find_emails(domain, company_name)

        crt_subs, dns_subs, email_data = await asyncio.gather(
            crt_task, dns_task, email_task,
            return_exceptions=True,
        )

        # Merge subdomains
        all_subs: set[str] = set()
        if isinstance(crt_subs, list):
            all_subs.update(crt_subs)
        if isinstance(dns_subs, list):
            all_subs.update(dns_subs)

        result["subdomains"] = sorted(all_subs)

        # Merge email data
        if isinstance(email_data, dict):
            result["emails"] = email_data.get("emails", [])
            result["employees"] = email_data.get("employees", [])

        # Analyze subdomains for intelligence
        intel_lines = self._analyze_subdomains(result["subdomains"], domain)

        # Build raw content for AI
        content_parts = [
            f"OSINT SCAN RESULTS FOR: {domain}",
            f"Company: {company_name}",
            f"Total subdomains discovered: {len(result['subdomains'])}",
        ]

        if result["subdomains"]:
            content_parts.append(
                "Subdomains found:\n" +
                "\n".join(f"  • {s}" for s in result["subdomains"][:50])
            )

        if intel_lines:
            content_parts.append(
                "Infrastructure intelligence:\n" +
                "\n".join(f"  • {i}" for i in intel_lines)
            )

        if result["emails"]:
            content_parts.append(
                f"Email addresses found ({len(result['emails'])}):\n" +
                "\n".join(f"  • {e}" for e in result["emails"][:20])
            )

        if result["employees"]:
            content_parts.append(
                f"Potential employees identified ({len(result['employees'])}):\n" +
                "\n".join(f"  • {e}" for e in result["employees"][:15])
            )

        result["raw_content"] = "\n\n".join(content_parts)
        logger.info(
            f"[OSINT] Harvest complete: {len(result['subdomains'])} subdomains, "
            f"{len(result['emails'])} emails, {len(result['employees'])} employees"
        )
        return result

    async def _guess_domain(self, company_name: str) -> str:
        """Guess the company's primary domain using SearXNG."""
        try:
            from core.config import settings
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(
                    f"{settings.SEARXNG_URL}/search",
                    params={"q": f"{company_name} official website", "format": "json"},
                )
                if resp.status_code == 200:
                    results = resp.json().get("results", [])
                    skip_domains = {
                        "wikipedia.org", "linkedin.com", "twitter.com", "x.com",
                        "facebook.com", "instagram.com", "youtube.com", "reddit.com",
                        "crunchbase.com", "bloomberg.com",
                    }
                    for r in results[:10]:
                        host = urlparse(r.get("url", "")).hostname or ""
                        if host and not any(host.endswith(d) for d in skip_domains):
                            # Strip 'www.' prefix
                            if host.startswith("www."):
                                host = host[4:]
                            return host
        except Exception as e:
            logger.warning(f"[OSINT] Domain guess error: {e}")
        return ""

    async def _crt_sh_subdomains(self, domain: str) -> list[str]:
        """Query Certificate Transparency logs via crt.sh for real subdomains."""
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    f"https://crt.sh/?q=%.{domain}&output=json",
                    headers={"User-Agent": "Mozilla/5.0"},
                )
                if resp.status_code != 200:
                    return []

                data = resp.json()
                subs: set[str] = set()
                for entry in data:
                    name = entry.get("name_value", "")
                    for line in name.split("\n"):
                        line = line.strip().lower()
                        if line.endswith(domain) and "*" not in line:
                            subs.add(line)

                logger.info(f"[OSINT] crt.sh: {len(subs)} subdomains for {domain}")
                return list(subs)
        except Exception as e:
            logger.warning(f"[OSINT] crt.sh error: {e}")
            return []

    async def _dns_subdomain_check(self, domain: str) -> list[str]:
        """Quick DNS check for common subdomains."""
        import socket
        found: list[str] = []

        async def _check(prefix: str):
            fqdn = f"{prefix}.{domain}"
            try:
                loop = asyncio.get_event_loop()
                await asyncio.wait_for(
                    loop.run_in_executor(None, socket.gethostbyname, fqdn),
                    timeout=2.0,
                )
                found.append(fqdn)
            except (socket.gaierror, asyncio.TimeoutError, OSError):
                pass

        # Check in batches to avoid overwhelming DNS
        batch_size = 20
        for i in range(0, len(_SUBDOMAIN_PREFIXES), batch_size):
            batch = _SUBDOMAIN_PREFIXES[i:i + batch_size]
            await asyncio.gather(*[_check(p) for p in batch])

        logger.info(f"[OSINT] DNS check: {len(found)} active subdomains for {domain}")
        return found

    async def _find_emails(self, domain: str, company_name: str) -> dict:
        """Search for email addresses associated with the domain."""
        emails: set[str] = set()
        employees: list[str] = []

        # Method 1: Search for emails via SearXNG
        try:
            from core.config import settings
            queries = [
                f'"@{domain}" email',
                f'"{company_name}" email contact',
                f'site:linkedin.com "{company_name}" email',
            ]
            async with httpx.AsyncClient(timeout=10.0) as client:
                for q in queries:
                    try:
                        resp = await client.get(
                            f"{settings.SEARXNG_URL}/search",
                            params={"q": q, "format": "json"},
                        )
                        if resp.status_code == 200:
                            results = resp.json().get("results", [])
                            for r in results:
                                text = f"{r.get('title', '')} {r.get('content', '')}"
                                found_emails = _EMAIL_PATTERN.findall(text)
                                for email in found_emails:
                                    if domain in email.lower():
                                        emails.add(email.lower())
                    except Exception:
                        continue
        except Exception as e:
            logger.warning(f"[OSINT] Email search error: {e}")

        # Extract employee names from email addresses
        for email in emails:
            local_part = email.split("@")[0]
            # Common patterns: john.doe, jdoe, john_doe
            if "." in local_part:
                parts = local_part.split(".")
                name = " ".join(p.capitalize() for p in parts if len(p) > 1)
                if len(name) > 3:
                    employees.append(name)

        return {"emails": sorted(emails), "employees": employees}

    def _analyze_subdomains(self, subdomains: list[str], domain: str) -> list[str]:
        """Derive competitive intelligence from subdomain patterns."""
        intel: list[str] = []

        # Categorize subdomains
        categories = {
            "dev_infra": ["dev", "staging", "test", "beta", "alpha", "qa", "uat", "sandbox"],
            "product": ["api", "app", "dashboard", "platform", "cloud", "mobile", "m."],
            "data_ai": ["ai", "ml", "data", "analytics", "metrics", "grafana", "kibana"],
            "security": ["vpn", "sso", "auth", "login", "secure", "sentry"],
            "comms": ["mail", "smtp", "imap", "slack", "teams", "chat"],
            "growth": ["blog", "docs", "help", "support", "community", "forum", "events"],
            "commerce": ["shop", "store", "payments", "billing", "checkout"],
            "careers": ["careers", "jobs", "hiring", "recruit"],
        }

        found_categories: dict[str, list[str]] = {}
        for sub in subdomains:
            prefix = sub.replace(f".{domain}", "").split(".")[0] if domain in sub else sub
            for cat, keywords in categories.items():
                if any(k in prefix.lower() for k in keywords):
                    found_categories.setdefault(cat, []).append(sub)
                    break

        labels = {
            "dev_infra": "Active development infrastructure (dev/staging/test environments detected)",
            "product": "Multiple product surfaces detected (API, dashboard, mobile)",
            "data_ai": "AI/ML and data infrastructure detected → investing in intelligence capabilities",
            "security": "Enterprise security infrastructure (SSO, VPN, auth)",
            "comms": "Internal communication infrastructure",
            "growth": "Growth & community investment (blog, docs, support, events)",
            "commerce": "E-commerce/payment infrastructure active",
            "careers": "Active hiring infrastructure detected",
        }

        for cat, subs in found_categories.items():
            intel.append(f"{labels.get(cat, cat)}: {', '.join(subs[:5])}")

        if len(subdomains) > 50:
            intel.append(f"Large digital footprint ({len(subdomains)} subdomains) — indicates mature, well-funded organization")
        elif len(subdomains) > 20:
            intel.append(f"Medium digital footprint ({len(subdomains)} subdomains) — growing organization")
        elif len(subdomains) > 5:
            intel.append(f"Small digital footprint ({len(subdomains)} subdomains) — focused/early-stage")

        return intel
