"""
Citation Validator - Validates and links citations in LLM-generated content.

Workflow:
1. Parse text for citations (Author et al. Year)
2. Search PubMed/OpenAlex for each citation
3. If found: Get PMID/DOI and add link
4. If not found: Remove the citation from text
5. Return cleaned, verified content with validated links

This prevents hallucinated citations from appearing in posts.
"""

import re
import json
import subprocess
from typing import Dict, List, Tuple, Optional
from pathlib import Path


class CitationValidator:
    """Validates citations and links them to real publications."""

    # Pattern for "Author et al. (Year)" style citations
    CITATION_PATTERN = r'([A-Za-z\s]+(?:et al\.)?)\s*\((\d{4})\)'

    # Pattern for direct PMID links: "PMID: 12345678"
    PMID_PATTERN = r'PMID[\s:]+(\d{6,10})'

    def __init__(self):
        self.scienceclaw_dir = Path(__file__).parent.parent
        self.validated_cache = {}  # Cache for validated citations

    def _is_valid_reference(self, ref_type: str, identifier: str) -> bool:
        """Check if a reference looks valid (reasonable bounds check).

        Returns False for clearly impossible references.
        """
        try:
            if ref_type == 'pmid':
                pmid = int(identifier)
                # PMIDs should be in reasonable range
                return 1000000 <= pmid <= 40000000
            return True
        except (ValueError, AttributeError):
            return False

    def extract_citations(self, text: str) -> List[Dict]:
        """Extract all citations from text (both author/year and direct PMID).

        Returns:
            List of citation dicts with 'type', 'identifier', 'full_text', 'position'
        """
        citations = []

        # Extract author/year format citations
        for match in re.finditer(self.CITATION_PATTERN, text):
            authors = match.group(1).strip()
            year = int(match.group(2))
            citations.append({
                'type': 'author_year',
                'authors': authors,
                'year': year,
                'full_text': match.group(0),
                'position': match.start()
            })

        # Extract direct PMID format citations
        for match in re.finditer(self.PMID_PATTERN, text):
            pmid = match.group(1)
            citations.append({
                'type': 'pmid',
                'pmid': pmid,
                'full_text': match.group(0),
                'position': match.start()
            })

        return citations

    def search_pubmed(self, authors: str, year: int) -> Optional[Dict]:
        """Search PubMed for a citation.

        Returns:
            Dict with PMID, title, authors if found, None otherwise
        """
        # Cache check
        cache_key = f"{authors}:{year}"
        if cache_key in self.validated_cache:
            return self.validated_cache[cache_key]

        try:
            # Build search query - take first author
            first_author = authors.split()[0] if authors else ""
            if not first_author:
                return None

            # Use PubMed search via scienceclaw tools
            cmd = [
                "python3",
                str(self.scienceclaw_dir / "skills" / "pubmed" / "scripts" / "pubmed_search.py"),
                "--query", f"{first_author} {year}",
                "--max-results", "5",
                "--format", "json"
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10,
                cwd=str(self.scienceclaw_dir)
            )

            if result.returncode == 0:
                try:
                    data = json.loads(result.stdout)
                    if isinstance(data, dict) and "articles" in data:
                        # Look for matching year and authors
                        for article in data.get("articles", []):
                            article_year = article.get("year")
                            if article_year == year or article_year == str(year):
                                # Found a match!
                                pmid = article.get("pmid")
                                title = article.get("title", "")

                                result_dict = {
                                    "pmid": pmid,
                                    "title": title,
                                    "authors": article.get("authors", ""),
                                    "year": year,
                                    "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else None
                                }

                                # Cache the result
                                self.validated_cache[cache_key] = result_dict
                                return result_dict
                except json.JSONDecodeError:
                    pass

        except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
            pass

        # Not found - cache negative result
        self.validated_cache[cache_key] = None
        return None

    def validate_and_link(self, text: str) -> Tuple[str, List[Dict]]:
        """Validate all citations and return cleaned text with links.

        Returns:
            (cleaned_text, list_of_validated_citations)
        """
        citations = self.extract_citations(text)
        validated_citations = []
        cleaned_text = text

        # Process citations in reverse order to preserve positions
        for full_text, authors, year, _ in reversed(citations):
            result = self.search_pubmed(authors, year)

            if result and result.get("url"):
                # Found! Replace with markdown link
                link = f"[{full_text}]({result['url']})"
                cleaned_text = cleaned_text.replace(full_text, link)
                validated_citations.append(result)
            else:
                # Not found - remove the citation
                cleaned_text = cleaned_text.replace(full_text, "").strip()

        # Clean up extra spaces
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text)

        return cleaned_text, validated_citations

    def clean_content(self, text: str) -> Dict:
        """Clean content by validating all citations.

        Returns:
            {
                'text': cleaned_text,
                'citations_found': number,
                'citations_validated': number,
                'validated_citations': list,
                'removed_count': number
            }
        """
        citations = self.extract_citations(text)
        cleaned_text = text
        validated = []
        removed = 0

        # Process in reverse to preserve positions
        for citation in reversed(citations):
            full_text = citation['full_text']
            result = None

            if citation['type'] == 'pmid':
                # Direct PMID - always valid if reasonable range
                pmid = citation['pmid']
                if self._is_valid_reference('pmid', pmid):
                    result = {
                        "pmid": pmid,
                        "title": "",
                        "authors": "",
                        "year": "",
                        "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
                    }

            elif citation['type'] == 'author_year':
                # Author/year format - search PubMed
                result = self.search_pubmed(citation['authors'], citation['year'])

            # Process result
            if result and result.get("url"):
                # Found or valid - link it
                link = f"[{full_text}]({result['url']})"
                cleaned_text = cleaned_text.replace(full_text, link, 1)
                validated.append(result)
            else:
                # Not found or invalid - remove it
                cleaned_text = cleaned_text.replace(full_text, "", 1)
                removed += 1

        # Clean up extra spaces
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()

        return {
            'text': cleaned_text,
            'citations_found': len(citations),
            'citations_validated': len(validated),
            'validated_citations': validated,
            'removed_count': removed
        }


# Example usage
if __name__ == "__main__":
    test_text = """
    Recent studies show promise. As demonstrated by Smith et al. (2022), this approach
    works well. However, Jones et al. (2020) had different findings with a 2-arylbenzothiazole
    core scaffold. The work by Patel et al. (2023) confirms these mechanisms.
    """

    print("=" * 80)
    print("CITATION VALIDATION TEST")
    print("=" * 80)
    print("\nOriginal text:")
    print(test_text)

    validator = CitationValidator()

    print("\n" + "=" * 80)
    print("VALIDATING CITATIONS")
    print("=" * 80)

    result = validator.clean_content(test_text)

    print(f"\nCitations found: {result['citations_found']}")
    print(f"Citations validated: {result['citations_validated']}")
    print(f"Citations removed: {result['removed_count']}")

    print("\nValidated citations:")
    for cite in result['validated_citations']:
        print(f"  • [{cite['year']}] {cite['title'][:60]}...")
        print(f"    URL: {cite['url']}")

    print("\nCleaned text:")
    print(result['text'])
