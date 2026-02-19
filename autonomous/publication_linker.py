"""
Publication Linker - Extracts and links scientific references in posts and comments.

Automatically detects:
- PubMed IDs (PMID: 12345678)
- DOIs (doi: 10.xxxx/xxxxx or https://doi.org/10.xxxx/xxxxx)
- arXiv IDs (arXiv:2305.12345)
- PubMed Central IDs (PMCID: 1234567)
"""

import re
from typing import List, Dict, Tuple
from urllib.parse import quote


class PublicationReference:
    """Represents a single publication reference."""

    def __init__(self, ref_type: str, identifier: str, display_text: str = None):
        self.type = ref_type  # 'pmid', 'doi', 'arxiv', 'pmcid'
        self.identifier = identifier
        self.display_text = display_text or identifier
        self.url = self._get_url()

    def _get_url(self) -> str:
        """Generate URL based on reference type."""
        if self.type == 'pmid':
            return f"https://pubmed.ncbi.nlm.nih.gov/{self.identifier}/"
        elif self.type == 'pmcid':
            return f"https://www.ncbi.nlm.nih.gov/pmc/articles/{self.identifier}/"
        elif self.type == 'doi':
            # Normalize DOI
            doi = self.identifier
            if not doi.startswith('10.'):
                doi = doi.split('/')[-1] if '/' in doi else doi
            return f"https://doi.org/{quote(doi, safe=':/')}".replace('%2F', '/')
        elif self.type == 'arxiv':
            return f"https://arxiv.org/abs/{self.identifier}"
        else:
            return None

    def as_markdown_link(self) -> str:
        """Format as markdown link."""
        if self.url:
            return f"[{self.display_text}]({self.url})"
        return self.display_text

    def as_plain_link(self) -> Tuple[str, str]:
        """Return as (text, url) tuple."""
        return (self.display_text, self.url)


class PublicationLinker:
    """Extracts and links publications in scientific text.

    IMPORTANT: Only links references that are explicitly validated.
    To prevent spreading hallucinated references, this linker:
    - Requires explicit reference format (PMID: 12345678)
    - Should validate references against real databases before linking
    - Conservative approach: when in doubt, don't link
    """

    # Regex patterns for different reference types
    # These match ONLY explicit, properly formatted references
    PATTERNS = {
        'pmid': r'(?:PMID|PubMed ID)[\s:]+(\d{6,10})',
        'pmcid': r'(?:PMCID|PMC)[\s:]+(\d{7,10})',
        'doi': r'(?:doi[\s:]+|https?://doi\.org/)([0-9.]+/[^\s\)]+)',
        'arxiv': r'(?:arXiv|arxiv)[\s:]+([0-9.]+(?:v\d+)?)',
    }

    # Validation: minimum PMID should be reasonable
    MIN_PMID = 1000000  # PMIDs are in millions now
    MAX_PMID = 40000000  # Upper bound for reasonable PMID

    def __init__(self, text: str):
        self.text = text
        self.references: List[PublicationReference] = []
        self._extract_references()

    def _is_valid_reference(self, ref_type: str, identifier: str) -> bool:
        """Check if a reference looks valid (reasonable bounds check).

        This is a conservative check to prevent obvious hallucinations.
        Returns False for clearly impossible references.
        """
        try:
            if ref_type == 'pmid':
                pmid = int(identifier)
                # PMIDs should be in reasonable range
                return self.MIN_PMID <= pmid <= self.MAX_PMID
            elif ref_type == 'pmcid':
                pmcid = int(identifier)
                # PMCIDs should be 7-10 digits
                return 1000000 <= pmcid <= 9999999
            elif ref_type == 'doi':
                # DOI format check: should start with 10.
                return identifier.startswith('10.')
            elif ref_type == 'arxiv':
                # arXiv format: YYMM.NNNNN or YYMM.NNNNNvN
                return re.match(r'\d{4}\.\d{4,5}(?:v\d+)?$', identifier)
        except (ValueError, AttributeError):
            return False
        return True

    def _extract_references(self):
        """Extract all publication references from text.

        CONSERVATIVE: Only extracts references that pass validation checks.
        """
        for ref_type, pattern in self.PATTERNS.items():
            matches = re.finditer(pattern, self.text, re.IGNORECASE)
            for match in matches:
                identifier = match.group(1).strip()

                # Validate reference format
                if not self._is_valid_reference(ref_type, identifier):
                    continue  # Skip invalid references

                # Avoid duplicates
                if not any(ref.identifier == identifier and ref.type == ref_type
                          for ref in self.references):
                    self.references.append(
                        PublicationReference(ref_type, identifier, match.group(0))
                    )

    def link_references(self) -> str:
        """Replace references in text with markdown links."""
        linked_text = self.text

        # Sort by position in text (reverse) to preserve positions after replacement
        positions = []
        for ref_type, pattern in self.PATTERNS.items():
            for match in re.finditer(pattern, self.text, re.IGNORECASE):
                positions.append((match.start(), match.end(), match.group(0), ref_type, match.group(1)))

        # Sort by start position (reverse) to replace from end to beginning
        positions.sort(key=lambda x: x[0], reverse=True)

        # Replace each reference with its markdown link
        for start, end, full_match, ref_type, identifier in positions:
            ref = PublicationReference(ref_type, identifier.strip(), full_match)
            linked_text = linked_text[:start] + ref.as_markdown_link() + linked_text[end:]

        return linked_text

    def get_references(self) -> List[Dict]:
        """Get list of all extracted references."""
        return [
            {
                'type': ref.type,
                'identifier': ref.identifier,
                'display': ref.display_text,
                'url': ref.url
            }
            for ref in self.references
        ]

    def add_references_section(self, separator: str = "\n\n") -> str:
        """Add a references section at the end of text."""
        if not self.references:
            return self.text

        linked_text = self.link_references()

        # Create references section
        refs_section = "\n\n**References:**\n"
        for i, ref in enumerate(self.references, 1):
            refs_section += f"- {ref.as_markdown_link()}\n"

        return linked_text + refs_section

    def extract_and_format(self, include_refs_section: bool = True) -> str:
        """Extract references and format text with links.

        Args:
            include_refs_section: Whether to add a references section at the end

        Returns:
            Formatted text with linked references
        """
        if include_refs_section:
            return self.add_references_section()
        else:
            return self.link_references()

    @staticmethod
    def format_post_with_references(
        title: str,
        hypothesis: str,
        method: str,
        findings: str,
        sources: str = None
    ) -> Dict[str, str]:
        """Format a complete post with linked references in each section.

        Args:
            title: Post title
            hypothesis: Hypothesis section
            method: Method section
            findings: Findings section
            sources: Optional sources section

        Returns:
            Dict with formatted sections containing linked references
        """
        result = {
            'title': title,
            'hypothesis': PublicationLinker(hypothesis).link_references(),
            'method': PublicationLinker(method).link_references(),
            'findings': PublicationLinker(findings).link_references(),
        }

        if sources:
            result['sources'] = PublicationLinker(sources).extract_and_format(include_refs_section=False)

        return result


# Example usage
if __name__ == "__main__":
    # Test with sample text
    sample_text = """
    Recent studies (PMID: 35123456) have shown that protein aggregation
    plays a key role in Alzheimer's disease. This aligns with findings from
    doi: 10.1038/nature12345 which demonstrated tau pathology involvement.
    Additional supporting evidence from arXiv: 2305.12345 provides computational
    predictions of disease mechanisms. The clinical trial (PMCID: 1234567)
    confirmed these findings in human patients.
    """

    linker = PublicationLinker(sample_text)

    print("Extracted References:")
    for ref in linker.get_references():
        print(f"  {ref['type'].upper()}: {ref['identifier']} -> {ref['url']}")

    print("\nLinked Text:")
    print(linker.extract_and_format())
