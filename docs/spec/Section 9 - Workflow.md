# **SECTION 9 — WORKFLOW (GITHUB ACTIONS)**  
**Authoritative Specification — High‑Level Architecture**  
**Document ID:** Section 9 — Workflow  
**Version:** V0.00  

---

# **9.1 Purpose of This Section**  
This section defines the **high‑level workflow architecture** for automated tasks performed through GitHub Actions.  
These workflows ensure that:

- metadata stays up to date  
- assets remain synchronized  
- versioning remains consistent  
- validation runs regularly  
- the system remains deterministic and reproducible  

This section describes **what each workflow must accomplish**, not how it is implemented.

---

# **9.2 Workflow Categories**  
The system must support the following workflow categories:

- **Metadata Refresh Workflows**  
- **Asset Synchronization Workflows**  
- **Version Audit Workflows**  
- **Integrity Validation Workflows**  
- **Scheduled Maintenance Workflows**  

## **Live Workflow Files**

The current live repo implementation uses:

- `.github/workflows/build-data.yml` for production data rebuilds and committed runtime artifact refresh
- `.github/workflows/validate.yml` for validation-only checks against the tracked repo state
- `scripts/run_pipeline_tmdb_trakt.py` as the authoritative end-to-end local runner mirrored by the build-data workflow

---

# **9.3 Metadata Refresh Workflows**  
These workflows ensure that metadata remains current.

### **Responsibilities:**  
- Trigger metadata fetch scripts (TMDB, Trakt, TVMaze, OMDb)  
- Update local metadata files  
- Ensure deterministic ordering of updates  
- Produce a summary of changes  

### **Inputs (Conceptual):**  
- Local metadata  
- External metadata sources  

### **Outputs (Conceptual):**  
- Updated metadata  
- Refresh summary  

---

# **9.4 Asset Synchronization Workflows**  
These workflows ensure that all required assets exist locally.

### **Responsibilities:**  
- Trigger logo download workflow  
- Validate asset directories  
- Identify missing or outdated assets  
- Produce asset synchronization reports  

### **Inputs (Conceptual):**  
- Asset manifest  
- Local asset directories  

### **Outputs (Conceptual):**  
- Updated assets  
- Asset validation summary  

---

# **9.5 Version Audit Workflows**  
These workflows ensure that version metadata remains consistent.

### **Responsibilities:**  
- Trigger audit_versions  
- Validate schema versions  
- Validate metadata completeness  
- Produce version audit reports  

### **Inputs (Conceptual):**  
- Version manifest  
- Local metadata  

### **Outputs (Conceptual):**  
- Audit report  
- Version summary  

---

# **9.6 Integrity Validation Workflows**  
These workflows ensure that the system remains internally consistent.

### **Responsibilities:**  
- Validate metadata structure  
- Validate asset presence  
- Validate naming conventions  
- Validate directory structure  

### **Inputs (Conceptual):**  
- Local metadata  
- Local assets  

### **Outputs (Conceptual):**  
- Integrity report  

---

# **9.7 Scheduled Maintenance Workflows**  
These workflows run on a schedule to ensure long‑term stability.

### **Responsibilities:**  
- Perform periodic metadata refresh  
- Perform periodic asset validation  
- Perform periodic version audits  
- Produce maintenance summaries  

### **Inputs (Conceptual):**  
- Local dataset  

### **Outputs (Conceptual):**  
- Maintenance report  

---

# **9.8 Workflow Invariants**  
The following must never change:

- Workflows must be deterministic  
- Workflows must not modify authoritative fields incorrectly  
- Workflows must not delete assets without replacement  
- Workflows must not introduce schema drift  
- Workflows must always produce human‑readable reports  

---

# **9.9 End of Section 9 — Workflow (GitHub Actions)**
