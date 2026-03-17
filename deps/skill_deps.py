"""Mapping of skill names to their required pip packages."""

SKILL_DEPS = {
    # No extra deps (use only stdlib + core)
    "pubmed": [],
    "blast": [],
    "uniprot": [],
    "sequence": [],
    "pdb": [],
    "websearch": [],
    "arxiv": [],
    "cas": [],
    "nistwebbook": [],
    "infinite": [],

    # Lightweight
    "pubchem": ["pubchempy"],
    "chembl": ["chembl-webresource-client", "url-normalize"],
    "rdkit": ["rdkit"],
    "datavis": ["matplotlib", "seaborn"],
    "plotly": ["plotly"],
    "polars": ["polars"],
    "py3dmol": ["py3Dmol"],
    "sympy": ["sympy", "mpmath"],
    "networkx": ["networkx"],
    "scipy": ["scipy"],
    "statsmodels": ["statsmodels"],
    "scikit-learn": ["scikit-learn", "joblib", "threadpoolctl"],
    "ase": ["ase"],
    "astropy": ["astropy"],
    "cobra": ["cobra"],
    "pydicom": ["pydicom"],
    "pubchempy": ["pubchempy"],

    # Medium
    "bioservices": ["bioservices", "easydev", "colorlog", "grequests", "rich-click", "suds-community", "xmltodict"],
    "gget": ["gget", "ipython", "traitlets", "stack-data", "ipywidgets", "mysql-connector-python", "pygments", "ipython-pygments-lexers", "jedi", "matplotlib-inline", "pexpect", "prompt_toolkit", "decorator"],
    "materials": ["pymatgen", "ase"],
    "umap": ["umap-learn"],
    "shap": ["shap"],
    "markitdown": ["markitdown", "python-dotenv", "magika"],
    "drugbank": ["drugbank-downloader", "pystow", "bioversions", "lxml"],
    "neuropixels": ["probeinterface", "neo"],
    "datamol": ["datamol"],
    "medchem": ["medchem", "datamol"],
    "pydeseq2": ["pydeseq2"],
    "etetoolkit": ["ete3"],
    "music21": ["music21"],
    "litellm": ["litellm"],
    "tooluniverse": ["tooluniverse"],
    "simpy": ["simpy"],

    # Heavy
    "torch": ["torch"],
    "torch_geometric": ["torch", "networkx"],
    "lightning": ["lightning", "lightning-utilities", "pytorch-lightning", "torchmetrics", "torch"],
    "stable_baselines3": ["stable-baselines3", "cloudpickle", "gymnasium"],
    "pymoo": ["pymoo", "moocore", "alive_progress", "autograd", "cma", "cffi"],
    "pymc": ["pymc", "arviz", "platformdirs", "xarray_einstats", "h5netcdf"],
    "arboreto": ["arboreto", "distributed", "dask", "zict", "pyarrow"],
    "scanpy": ["scanpy"],

    # Domain-specific heavy
    "qiskit": ["qiskit"],
    "cirq": ["cirq"],
    "pennylane": ["pennylane"],
    "qutip": ["qutip"],
    "opentrons": ["opentrons", "pyserial", "pydantic-settings", "opentrons-shared-data"],

    # tdc requires conda env - no pip install
    "tdc": [],
}
