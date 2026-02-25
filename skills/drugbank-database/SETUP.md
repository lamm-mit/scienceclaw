# DrugBank skill – what to do

## 1. Get a DrugBank account (required)

- Sign up (free for academic use): **https://go.drugbank.com**
- Accept the license and note your **email** and **password**.

## 2. Set credentials

Use your DrugBank login as environment variables so the downloader can fetch the XML:

```bash
export DRUGBANK_USERNAME="your_drugbank_email@example.com"
export DRUGBANK_PASSWORD="your_drugbank_password"
```

Or add to `~/.bashrc` / `~/.profile` (no spaces around `=`).

## 3. Install deps (if needed)

From the scienceclaw venv:

```bash
pip install drugbank-downloader lxml
```

(Already listed in scienceclaw `requirements.txt`.)

## 4. Run the skill

**CLI**

```bash
# Help
python3 scripts/drugbank_helper.py --help

# Query a drug (first run may download/cache DrugBank XML)
python3 scripts/drugbank_helper.py DB00001
```

**Python**

```python
from drugbank_helper import DrugBankHelper

db = DrugBankHelper()
info = db.get_drug_info("DB00001")
print(info["name"], info["type"])
interactions = db.get_interactions("DB00001")
```

First use of `DrugBankHelper()` may take a while while the XML is downloaded and parsed; later runs use the cache.

## Alternative: Download via curl (all-full-database)

If `drugbank-downloader` fails or you prefer manual control, use curl with HTTP basic auth:

```bash
export DRUGBANK_USERNAME="fw2@mit.edu"
export DRUGBANK_PASSWORD="your_password"

# Download latest
./scripts/download_drugbank.sh

# Or specific version (5.1.14 → 5-1-14 in URL)
./scripts/download_drugbank.sh 5-1-14

# Custom output dir
./scripts/download_drugbank.sh 5-1-14 /path/to/store/
```

Raw curl equivalent:

```bash
curl -Lfv -o drugbank_full.zip -u "$DRUGBANK_USERNAME:$DRUGBANK_PASSWORD" \
  https://go.drugbank.com/releases/5-1-14/downloads/all-full-database
```

Then set `DRUGBANK_XML_PATH` to the zip. Use `-L` so curl follows redirects.

## If download fails: use a local file

If your account is not yet approved for API download, you can download the database once in your browser from https://go.drugbank.com/releases/5.1.14#full (log in, click “Download” for “Full database”), then point the skill at the file:

```bash
export DRUGBANK_XML_PATH="/path/to/full database.xml.zip"
# or path to the extracted .xml:
# export DRUGBANK_XML_PATH="/path/to/full database.xml"
python3 scripts/drugbank_helper.py DB00001
```

The zip must contain a file named `full database.xml` (DrugBank’s default); the skill auto-detects the XML file inside.

## Optional: Pin DrugBank version

The skill uses version **5.1.14** by default (bioversions no longer provides DrugBank, so we avoid that lookup). To use another release:

```bash
export DRUGBANK_VERSION="5.1.12"
```

## Troubleshooting

- **“Invalid Getter name: drugbank”** → Fixed in the skill: we pass an explicit version so bioversions is not used. Ensure you’re on the latest `drugbank_helper.py`.
- **“Error: … open_drugbank”** or **“credentials were either invalid”** → Check `DRUGBANK_USERNAME` and `DRUGBANK_PASSWORD`. Reload shell after editing `.bashrc` (`source ~/.bashrc`) or set them in the same terminal before running.
- **No account** → Create one at https://go.drugbank.com (academic use is free). You may need to be approved for “academic download” before the full DB download works.
- **Commercial use** → DrugBank requires a separate license; see go.drugbank.com.
