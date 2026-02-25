# CAS Common Chemistry API Reference

Reference for the [CAS Common Chemistry](https://commonchemistry.cas.org/) API used by the ScienceClaw **cas** skill. CAS Common Chemistry provides access to chemical information for nearly 500,000 compounds from CAS REGISTRY®.

**API overview:** [https://commonchemistry.cas.org/API](https://commonchemistry.cas.org/API)  
**Request API access:** [https://www.cas.org/services/commonchemistry-api](https://www.cas.org/services/commonchemistry-api)

## Overview

- **License:** Creative Commons CC BY-NC 4.0 ([terms](https://creativecommons.org/licenses/by-nc/4.0/))
- **Coverage:** Common and frequently regulated chemicals; substances relevant to education and community interest
- **Full CAS REGISTRY®** (165M+ substances) is available via [CAS Custom Services](https://www.cas.org/solutions/cas-custom-services) or CAS SciFinder / STNext®

## API Access

**You must request API access before using the API.** There is no public key.

1. Go to [Request API Access for CAS Common Chemistry](https://www.cas.org/services/commonchemistry-api).
2. Complete the form (use case: workflow integration, chemical research, machine learning, or cheminformatics).
3. A link with access information (e.g. API key or token) will be sent to the email you provide.

Use the access information (e.g. API key) in ScienceClaw via environment variable or config as documented in the **cas** skill.

## Search Capabilities

The API supports search by:

| Query type | Example |
|------------|--------|
| Chemical compound name | "aspirin", "sodium chloride" (supports trailing wildcard, e.g. "atrazin*") |
| CAS Registry Number® | "58-08-2", "1912-24-9" (with or without dashes) |
| SMILES | Canonical or isomeric SMILES |
| InChI / InChIKey | With or without "InChI=" prefix |

Searches are **case-insensitive**.

## Typical Endpoints (pattern)

After you receive access, CAS will provide the exact base URL and authentication. Common patterns:

- **Search** – search by name, CAS RN, SMILES, or InChI; returns list of matching substances (e.g. CAS RN, name, image).
- **Detail** – get full record for a CAS RN: name, molecular formula, mass, InChI, InChIKey, SMILES, experimental properties (e.g. melting point, density), synonyms, citations.
- **Export** – get MOL file or other export format for a CAS RN.

## Example Response Fields (detail)

From CAS Common Chemistry detail records you can expect (among others):

- `rn` – CAS Registry Number
- `name` – Chemical name
- `molecularFormula`, `molecularMass`
- `inchi`, `inchiKey`, `smile`, `canonicalSmile`
- `experimentalProperties` – e.g. Melting Point, Density, with values and units
- `propertyCitations` – source of property data
- `synonyms`, `replacedRns`
- `hasMolfile` – whether MOL file is available

## Rate Limits and Terms

- Follow the rate limits and terms sent with your access information.
- CAS [API Content Terms](https://www.cas.org/sites/default/files/documents/cas-api-content-terms.pdf) apply; typically non-commercial use and attribution (CC BY-NC 4.0).

## References

- [CAS Common Chemistry](https://commonchemistry.cas.org/) – Web interface
- [Request API Access](https://www.cas.org/services/commonchemistry-api) – Get API access
- [CAS Common Chemistry API page](https://commonchemistry.cas.org/API) – Overview and usage
