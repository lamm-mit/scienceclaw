#!/usr/bin/env python3
"""
DrugBank Helper Functions

Utility functions for common DrugBank operations including:
- Drug information extraction
- Interaction analysis
- Target identification
- Chemical property extraction

Usage:
    from drugbank_helper import DrugBankHelper

    db = DrugBankHelper()
    drug_info = db.get_drug_info('DB00001')
    interactions = db.get_interactions('DB00001')
"""

import os
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Any
import xml.etree.ElementTree as ET

# Default DrugBank version (bioversions no longer has "drugbank" getter; explicit version avoids lookup)
DEFAULT_DRUGBANK_VERSION = "5.1.14"


def _load_root_from_local(path: str):
    """Load DrugBank root from a local .zip or .xml file."""
    p = Path(path).expanduser().resolve()
    if not p.exists():
        raise FileNotFoundError(f"DRUGBANK_XML_PATH not found: {p}")
    if p.suffix.lower() == ".zip":
        with zipfile.ZipFile(p) as z:
            with z.open("full database.xml") as f:
                return ET.fromstring(f.read())
    # .xml or other
    return ET.parse(str(p)).getroot()


class DrugBankHelper:
    """Helper class for DrugBank data access and analysis"""

    NAMESPACE = {'db': 'http://www.drugbank.ca'}

    def __init__(self, root=None):
        """
        Initialize DrugBankHelper

        Args:
            root: Pre-loaded XML root element. If None, will load from drugbank-downloader
                   or from local file if DRUGBANK_XML_PATH is set.
        """
        self.root = root
        self._drug_cache = {}

    def _get_root(self):
        """Lazy load DrugBank root element"""
        if self.root is None:
            local_path = os.environ.get("DRUGBANK_XML_PATH") or os.environ.get("DRUGBANK_ZIP_PATH")
            if local_path:
                self.root = _load_root_from_local(local_path)
            else:
                from drugbank_downloader import get_drugbank_root
                version = os.environ.get("DRUGBANK_VERSION", DEFAULT_DRUGBANK_VERSION)
                self.root = get_drugbank_root(version=version)
        return self.root

    def _get_text_safe(self, element) -> Optional[str]:
        """Safely extract text from XML element"""
        return element.text if element is not None else None

    def find_drug(self, drugbank_id: str):
        """
        Find drug element by DrugBank ID

        Args:
            drugbank_id: DrugBank ID (e.g., 'DB00001')

        Returns:
            XML element for the drug or None if not found
        """
        if drugbank_id in self._drug_cache:
            return self._drug_cache[drugbank_id]

        root = self._get_root()
        for drug in root.findall('db:drug', self.NAMESPACE):
            primary_id = drug.find('db:drugbank-id[@primary="true"]', self.NAMESPACE)
            if primary_id is not None and primary_id.text == drugbank_id:
                self._drug_cache[drugbank_id] = drug
                return drug
        return None

    def get_drug_info(self, drugbank_id: str) -> Dict[str, Any]:
        """
        Get comprehensive drug information

        Args:
            drugbank_id: DrugBank ID

        Returns:
            Dictionary with drug information including name, type, description, etc.
        """
        drug = self.find_drug(drugbank_id)
        if drug is None:
            return {}

        info = {
            'drugbank_id': drugbank_id,
            'name': self._get_text_safe(drug.find('db:name', self.NAMESPACE)),
            'type': drug.get('type'),
            'description': self._get_text_safe(drug.find('db:description', self.NAMESPACE)),
            'cas_number': self._get_text_safe(drug.find('db:cas-number', self.NAMESPACE)),
            'indication': self._get_text_safe(drug.find('db:indication', self.NAMESPACE)),
            'pharmacodynamics': self._get_text_safe(drug.find('db:pharmacodynamics', self.NAMESPACE)),
            'mechanism_of_action': self._get_text_safe(drug.find('db:mechanism-of-action', self.NAMESPACE)),
        }

        return info

    def get_interactions(self, drugbank_id: str) -> List[Dict[str, str]]:
        """
        Get all drug-drug interactions

        Args:
            drugbank_id: DrugBank ID

        Returns:
            List of interaction dictionaries
        """
        drug = self.find_drug(drugbank_id)
        if drug is None:
            return []

        interactions = []
        ddi_elem = drug.find('db:drug-interactions', self.NAMESPACE)

        if ddi_elem is not None:
            for interaction in ddi_elem.findall('db:drug-interaction', self.NAMESPACE):
                interactions.append({
                    'partner_id': self._get_text_safe(interaction.find('db:drugbank-id', self.NAMESPACE)),
                    'partner_name': self._get_text_safe(interaction.find('db:name', self.NAMESPACE)),
                    'description': self._get_text_safe(interaction.find('db:description', self.NAMESPACE)),
                })

        return interactions

    def get_targets(self, drugbank_id: str) -> List[Dict[str, Any]]:
        """
        Get drug targets

        Args:
            drugbank_id: DrugBank ID

        Returns:
            List of target dictionaries
        """
        drug = self.find_drug(drugbank_id)
        if drug is None:
            return []

        targets = []
        targets_elem = drug.find('db:targets', self.NAMESPACE)

        if targets_elem is not None:
            for target in targets_elem.findall('db:target', self.NAMESPACE):
                target_data = {
                    'id': self._get_text_safe(target.find('db:id', self.NAMESPACE)),
                    'name': self._get_text_safe(target.find('db:name', self.NAMESPACE)),
                    'organism': self._get_text_safe(target.find('db:organism', self.NAMESPACE)),
                    'known_action': self._get_text_safe(target.find('db:known-action', self.NAMESPACE)),
                }

                # Extract actions
                actions_elem = target.find('db:actions', self.NAMESPACE)
                if actions_elem is not None:
                    target_data['actions'] = [
                        action.text for action in actions_elem.findall('db:action', self.NAMESPACE)
                    ]

                # Extract polypeptide info
                polypeptide = target.find('db:polypeptide', self.NAMESPACE)
                if polypeptide is not None:
                    target_data['uniprot_id'] = polypeptide.get('id')
                    target_data['gene_name'] = self._get_text_safe(
                        polypeptide.find('db:gene-name', self.NAMESPACE)
                    )

                targets.append(target_data)

        return targets

    def get_properties(self, drugbank_id: str) -> Dict[str, Dict[str, Any]]:
        """
        Get chemical properties

        Args:
            drugbank_id: DrugBank ID

        Returns:
            Dictionary with 'calculated' and 'experimental' property dictionaries
        """
        drug = self.find_drug(drugbank_id)
        if drug is None:
            return {'calculated': {}, 'experimental': {}}

        properties = {'calculated': {}, 'experimental': {}}

        # Calculated properties
        calc_props = drug.find('db:calculated-properties', self.NAMESPACE)
        if calc_props is not None:
            for prop in calc_props.findall('db:property', self.NAMESPACE):
                kind = self._get_text_safe(prop.find('db:kind', self.NAMESPACE))
                value = self._get_text_safe(prop.find('db:value', self.NAMESPACE))
                if kind and value:
                    properties['calculated'][kind] = value

        # Experimental properties
        exp_props = drug.find('db:experimental-properties', self.NAMESPACE)
        if exp_props is not None:
            for prop in exp_props.findall('db:property', self.NAMESPACE):
                kind = self._get_text_safe(prop.find('db:kind', self.NAMESPACE))
                value = self._get_text_safe(prop.find('db:value', self.NAMESPACE))
                if kind and value:
                    properties['experimental'][kind] = value

        return properties

    def check_interaction(self, drug1_id: str, drug2_id: str) -> Optional[Dict[str, str]]:
        """
        Check if two drugs interact

        Args:
            drug1_id: First drug DrugBank ID
            drug2_id: Second drug DrugBank ID

        Returns:
            Interaction dictionary if interaction exists, None otherwise
        """
        interactions1 = self.get_interactions(drug1_id)
        for interaction in interactions1:
            if interaction['partner_id'] == drug2_id:
                return interaction

        # Check reverse direction
        interactions2 = self.get_interactions(drug2_id)
        for interaction in interactions2:
            if interaction['partner_id'] == drug1_id:
                return interaction

        return None

    def check_polypharmacy(self, drug_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Check interactions in a drug regimen

        Args:
            drug_ids: List of DrugBank IDs

        Returns:
            List of all interactions found between the drugs
        """
        all_interactions = []

        for i, drug1 in enumerate(drug_ids):
            for drug2 in drug_ids[i + 1:]:
                interaction = self.check_interaction(drug1, drug2)
                if interaction:
                    interaction['drug1'] = drug1
                    interaction['drug2'] = drug2
                    all_interactions.append(interaction)

        return all_interactions

    def get_smiles(self, drugbank_id: str) -> Optional[str]:
        """
        Get SMILES structure for a drug

        Args:
            drugbank_id: DrugBank ID

        Returns:
            SMILES string or None
        """
        props = self.get_properties(drugbank_id)
        return props.get('calculated', {}).get('SMILES')

    def get_inchi(self, drugbank_id: str) -> Optional[str]:
        """
        Get InChI structure for a drug

        Args:
            drugbank_id: DrugBank ID

        Returns:
            InChI string or None
        """
        props = self.get_properties(drugbank_id)
        return props.get('calculated', {}).get('InChI')

    def search_by_name(self, name: str, exact: bool = False) -> List[Dict[str, str]]:
        """
        Search drugs by name

        Args:
            name: Drug name to search for
            exact: If True, require exact match (case-insensitive)

        Returns:
            List of matching drugs with id and name
        """
        root = self._get_root()
        results = []
        search_term = name.lower()

        for drug in root.findall('db:drug', self.NAMESPACE):
            drug_id = drug.find('db:drugbank-id[@primary="true"]', self.NAMESPACE).text
            drug_name = self._get_text_safe(drug.find('db:name', self.NAMESPACE))

            if drug_name:
                if exact:
                    if drug_name.lower() == search_term:
                        results.append({'id': drug_id, 'name': drug_name})
                else:
                    if search_term in drug_name.lower():
                        results.append({'id': drug_id, 'name': drug_name})

        return results


# CLI and example usage
if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 2 and sys.argv[1] in ("--help", "-h"):
        print("Usage: drugbank_helper.py [--help] | drugbank_helper.py <drugbank_id>")
        print("  --help, -h  Show this message")
        print("  <drugbank_id>  e.g. DB00001 - print drug info (requires DrugBank XML)")
        print("\nLibrary: from drugbank_helper import DrugBankHelper")
        sys.exit(0)

    if len(sys.argv) < 2:
        print("Pass a DrugBank ID (e.g. DB00001) to query, or --help. Requires DrugBank XML.")
        sys.exit(0)

    drug_id = sys.argv[1].strip()
    if not drug_id.upper().startswith("DB") and drug_id != drug_id.upper():
        drug_id = "DB" + drug_id.lstrip("0") if drug_id.isdigit() else drug_id

    try:
        db = DrugBankHelper()
        drug_info = db.get_drug_info(drug_id)
        if not drug_info:
            print(f"No drug found for {drug_id}")
            sys.exit(1)
        print(f"Drug: {drug_info.get('name')}")
        print(f"Type: {drug_info.get('type')}")
        print(f"Indication: {(drug_info.get('indication') or 'N/A')[:200]}...")
        interactions = db.get_interactions(drug_id)
        print(f"Interactions: {len(interactions)}")
        targets = db.get_targets(drug_id)
        print(f"Targets: {len(targets)}")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if "credentials were either invalid" in str(e) or "not been approved" in str(e):
            print("\n1. Check DRUGBANK_USERNAME and DRUGBANK_PASSWORD (echo them in this shell).", file=sys.stderr)
            print("2. Visit https://go.drugbank.com/releases/5.1.14#full – if it says 'Ineligible for download', request approval.", file=sys.stderr)
            print("3. Or download the zip manually from that page, then set DRUGBANK_XML_PATH=/path/to/full database.xml.zip", file=sys.stderr)
        else:
            print("Optional: set DRUGBANK_XML_PATH to a local full database.xml.zip or .xml to skip download.", file=sys.stderr)
        sys.exit(1)
